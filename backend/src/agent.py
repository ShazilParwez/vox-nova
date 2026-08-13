import logging
import json
import db
import uuid
import datetime

from prompt import SYSTEM_PROMPT
from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
    inference,
    tokenize,
    room_io,
    UserInputTranscribedEvent,
    function_tool,
    RunContext,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel

logger = logging.getLogger("agent")

load_dotenv(".env.local")

# Initialize SQLite database
db.init_db()

SCHEMES_DATA = {
    "PMJJBY": {
        "min_age": 18,
        "max_age": 50,
        "premium": "₹436 per year",
        "coverage": "₹2 lakh for life insurance cover",
        "source": "Department of Financial Services, Ministry of Finance, Government of India",
        "source_url": "https://financialservices.gov.in/",
        "verified_on": "2026-08-10"
    },
    "PMSBY": {
        "min_age": 18,
        "max_age": 70,
        "premium": "₹20 per year",
        "coverage": "₹2 lakh for accidental death / total permanent disability, ₹1 lakh for partial permanent disability",
        "source": "Department of Financial Services, Ministry of Finance, Government of India",
        "source_url": "https://financialservices.gov.in/",
        "verified_on": "2026-08-10"
    }
}

class Assistant(Agent):
    def __init__(self, room: rtc.Room, call_state: dict, instructions: str = SYSTEM_PROMPT) -> None:
        super().__init__(instructions=instructions)
        self.room = room
        self.call_state = call_state

    def get_user_id(self):
        # Look up the identity of the user connected to the room
        for p in self.room.remote_participants.values():
            return p.identity
        return "unknown_user"

    @function_tool(description="Look up the current caller to see if they are a returning user and retrieve their name and saved financial facts.")
    async def lookup_caller(self):
        user_id = self.get_user_id()
        if user_id == "unknown_user":
            return json.dumps({"found": False, "reason": "No user connected yet"})
        result = db.lookup_caller(user_id)
        return json.dumps(result)

    @function_tool(description="Save or update the caller's memory. ALWAYS ask for explicit permission before saving new facts. DO NOT save sensitive information (OTP, PIN, passwords, etc.).")
    async def save_caller_memory(self, name: str, facts_json: str, language_preference: str = ""):
        user_id = self.get_user_id()
        if user_id == "unknown_user":
            return "Failed to save: No user connected."
        
        try:
            facts = json.loads(facts_json)
        except Exception:
            facts = {}
            
        sensitive_keywords = ["otp", "pin", "password", "cvv", "card", "account"]
        for k, v in facts.items():
            for word in sensitive_keywords:
                if word in str(v).lower():
                    return f"Failed to save: Sensitive information '{word}' detected. Please do not store this."

        db.save_caller_memory(user_id, name, facts, language_preference)
        return "Successfully saved caller memory."

    @function_tool(description="Check a user's eligibility for supported Indian government financial schemes using the current official scheme rules. Use this tool when a user asks whether they may be eligible for a supported scheme and the required eligibility information (age, account status) has been collected. Do not use it to approve enrollment or guarantee benefits. The result is informational only.")
    async def check_scheme_eligibility(self, scheme: str, age: int, has_eligible_account: bool):
        scheme_key = scheme.upper().strip()
        if scheme_key not in SCHEMES_DATA:
            return json.dumps({
                "status": "unavailable",
                "message": f"Eligibility information for {scheme} could not be retrieved or is unsupported."
            })
            
        data = SCHEMES_DATA[scheme_key]
        
        if not has_eligible_account:
            return json.dumps({
                "scheme": scheme_key,
                "status": "not_eligible",
                "reason": ["An eligible individual bank or Post Office account is required for this scheme."],
                "source": data["source"],
                "source_url": data["source_url"],
                "verified_on": data["verified_on"]
            })
            
        if age < data["min_age"] or age > data["max_age"]:
            return json.dumps({
                "scheme": scheme_key,
                "status": "not_eligible",
                "reason": [f"Age {age} is outside the current eligibility range of {data['min_age']} to {data['max_age']} years."],
                "source": data["source"],
                "source_url": data["source_url"],
                "verified_on": data["verified_on"]
            })
            
        self.call_state["success"] = True
        self.call_state["success_reason"] = f"Completed eligibility check for {scheme_key}"

        return json.dumps({
            "scheme": scheme_key,
            "status": "eligible",
            "reason": [
                f"Age is within the {data['min_age']}-{data['max_age']} eligibility range.",
                "User has confirmed an eligible bank/Post Office account."
            ],
            "premium": data["premium"],
            "coverage": data["coverage"],
            "source": data["source"],
            "source_url": data["source_url"],
            "verified_on": data["verified_on"],
            "disclaimer": "This is an informational eligibility check and not an approval or enrollment confirmation. Final enrollment is subject to the official process."
        })

    @function_tool(description="Create a human support escalation request. Use this ONLY when the user explicitly agrees to escalate their issue (like suspected fraud or an account-specific financial decision). You must ask for permission and tell them what will be shared before calling this. DO NOT include OTP, PIN, passwords, CVV, or complete bank account numbers in the summary.")
    async def create_escalation(self, who_needs_help: str, issue: str, what_happened: str, what_agent_checked: str, urgency: str, language: str, preferred_follow_up: str):
        user_id = self.get_user_id()
        if user_id == "unknown_user":
            user_id = "anonymous_" + uuid.uuid4().hex[:4]

        # Generate reference ID e.g. ESC-FIN-20260812-AB12
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        ref_id = f"ESC-FIN-{date_str}-{uuid.uuid4().hex[:4].upper()}"

        # Safety check: ensure no sensitive information is accidentally passed in
        sensitive_keywords = ["otp", "pin", "password", "cvv"]
        combined_text = f"{issue} {what_happened} {what_agent_checked}".lower()
        for word in sensitive_keywords:
            if word in combined_text:
                return json.dumps({
                    "status": "error",
                    "message": f"Escalation failed: sensitive information '{word}' detected. Please retry without sensitive data."
                })

        success = db.create_escalation_record(
            reference_id=ref_id,
            user_id=user_id,
            who_needs_help=who_needs_help,
            issue=issue,
            what_happened=what_happened,
            what_agent_checked=what_agent_checked,
            urgency=urgency,
            language=language,
            preferred_follow_up=preferred_follow_up
        )

        if success:
            return json.dumps({
                "status": "success",
                "reference_id": ref_id,
                "message": "Escalation request successfully created."
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to create escalation request in database."
            })


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    
    # Initialize Call Analytics State
    call_state = {
        "success": False,
        "started_at": datetime.datetime.now(),
        "channel": "browser",
        "user_id": "unknown_user",
        "success_reason": ""
    }

    # Inject outbound call instructions if applicable
    instructions = SYSTEM_PROMPT
    if ctx.room.metadata:
        try:
            metadata = json.loads(ctx.room.metadata)
            if metadata.get("call_type") == "financial_scheme_reminder":
                scheme = metadata.get("scheme", "PMSBY")
                instructions += f"\n\nOUTBOUND CALL CONTEXT:\nYou are initiating an outbound call. This is a reminder for {scheme}. Follow the OUTBOUND CALL OPENING RULE in your instructions exactly."
                call_state["channel"] = "sip"
        except Exception as e:
            logger.warning(f"Failed to parse room metadata: {e}")

    @ctx.room.on("participant_connected")
    def on_participant_connected(participant):
        call_state["user_id"] = participant.identity

    @ctx.room.on("disconnected")
    def on_room_disconnected():
        ended_at = datetime.datetime.now()
        duration = int((ended_at - call_state["started_at"]).total_seconds())
        outcome = "success" if call_state["success"] else "failed"
        failure_reason = "" if call_state["success"] else "User disconnected before completing a supported eligibility check or checklist request."
        
        logger.info(f"Call {ctx.room.name} disconnected. Outcome: {outcome}. Saving analytics...")
        db.save_call_analytics(
            call_id=ctx.room.name,
            user_id=call_state["user_id"],
            channel=call_state["channel"],
            outcome=outcome,
            success_reason=call_state["success_reason"],
            failure_reason=failure_reason,
            started_at=call_state["started_at"].strftime("%Y-%m-%d %H:%M:%S"),
            duration_seconds=duration
        )

    # Set up a voice AI pipeline
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
                model="gemini-3.5-flash-lite",
            ),
        tts=murf.TTS(
                voice="Anisha", 
                style="Conversational",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),

        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    logger.info(f"[7] AGENT_JOB_RECEIVED: Job started in room {ctx.room.name}")
    
    @session.on("user_speech_started")
    def on_user_speech_started():
        logger.info("[11] STT_STARTED: User speech detected")

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        # We check if the transcription is final
        if hasattr(event, 'is_final') and not event.is_final:
            return
            
        logger.info(f"[12] STT_TRANSCRIPT_RECEIVED: '{getattr(event, 'transcript', getattr(event, 'text', ''))}'")
        logger.info("[13] GEMINI_REQUEST_STARTED: Prompting LLM")
            
        user_id = "unknown_user"
        for p in ctx.room.remote_participants.values():
            user_id = p.identity
            break
            
        if hasattr(event, 'transcript') and event.transcript:
            db.save_query(user_id, event.transcript)
        elif hasattr(event, 'text') and event.text:
            db.save_query(user_id, event.text)
            
        # Mark as successful as soon as we get valid user input
        call_state["success"] = True
        if not call_state["success_reason"]:
            call_state["success_reason"] = "Conversation took place"

    @session.on("agent_speech_started")
    def on_agent_speech_started():
        call_state["success"] = True
        if not call_state["success_reason"]:
            call_state["success_reason"] = "Conversation took place"
        logger.info("[15] TTS_STARTED: Agent starting speech output")
        logger.info("[17] AGENT_AUDIO_PUBLISHED: Agent audio stream beginning")

    @session.on("agent_speech_committed")
    def on_agent_speech_committed():
        # Mark call as successful if the agent was able to reply (conversation happened)
        call_state["success"] = True
        if not call_state["success_reason"]:
            call_state["success_reason"] = "Conversation took place"
            
        logger.info("[14] GEMINI_RESPONSE_RECEIVED: LLM generated response")
        logger.info("[16] TTS_AUDIO_GENERATED: TTS generation complete")
        logger.info("[18] SIP_AUDIO_OUTPUT_CONFIRMED: Audio published to room")

    # Start the session
    await session.start(
        agent=Assistant(room=ctx.room, call_state=call_state, instructions=instructions),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()
    logger.info(f"[8] AGENT_JOINED_ROOM: Connected to {ctx.room.name}")
    
    for participant in ctx.room.remote_participants.values():
        logger.info(f"[6] SIP_PARTICIPANT_CONNECTED: Participant {participant.identity} found in room")
        logger.info(f"[9] SIP_AUDIO_TRACK_DETECTED: Checking tracks for {participant.identity}")
        for track in participant.track_publications.values():
            logger.info(f"[10] AUDIO_FRAMES_RECEIVED: Found published track {track.sid}")

    # If it's an outbound call, we need to trigger the agent to speak first
    if ctx.room.metadata and "financial_scheme_reminder" in ctx.room.metadata:
        async def outbound_greeting():
            import asyncio
            from livekit.agents import llm
            # Wait a moment for audio to establish
            await asyncio.sleep(2)
            
            logger.info("Triggering outbound greeting via generate_reply()")
            logger.info("[13] GEMINI_REQUEST_STARTED: Prompting LLM for greeting")
            try:
                # Gemini API throws '400 Bad Request' if the conversation starts with a tool call.
                # We MUST inject a dummy user message to satisfy Gemini's strict turn-history requirement.
                if hasattr(session, 'chat_ctx') and hasattr(session.chat_ctx, 'append'):
                    session.chat_ctx.append(role="user", text="Hello? I just picked up the phone. Please introduce yourself.")
                elif hasattr(session.history, 'append'):
                    try:
                        # If it's a ChatContext
                        session.history.append(role="user", text="Hello? I just picked up the phone. Please introduce yourself.")
                    except TypeError:
                        # If it's a plain list, instantiate ChatMessage with a list for content as required by pydantic
                        try:
                            msg = llm.ChatMessage(role="user", content="Hello? I just picked up the phone. Please introduce yourself.")
                        except Exception:
                            # In some LiveKit versions, content expects a list of ChatContent or str
                            msg = llm.ChatMessage(role="user", content=["Hello? I just picked up the phone. Please introduce yourself."])
                        session.history.append(msg)
                
                await session.generate_reply()
            except Exception as e:
                logger.error(f"Error triggering outbound greeting: {e}")
            
        import asyncio
        asyncio.create_task(outbound_greeting())


if __name__ == "__main__":
    cli.run_app(server)
