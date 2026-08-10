import logging
import json
import db

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
    def __init__(self, room: rtc.Room) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self.room = room

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

    # Set up a voice AI pipeline
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language="multi"),
        llm=google.LLM(
                model="gemini-3.5-flash",
            ),
        tts=murf.TTS(
                voice="Anisha", 
                style="Conversational",
                tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
                text_pacing=True
            ),
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        preemptive_generation=True,
    )

    @session.on("user_input_transcribed")
    def on_user_input_transcribed(event: UserInputTranscribedEvent):
        # We check if the transcription is final
        if hasattr(event, 'is_final') and not event.is_final:
            return
            
        user_id = "unknown_user"
        for p in ctx.room.remote_participants.values():
            user_id = p.identity
            break
            
        if hasattr(event, 'transcript') and event.transcript:
            db.save_query(user_id, event.transcript)
        elif hasattr(event, 'text') and event.text:
            db.save_query(user_id, event.text)

    # Start the session
    await session.start(
        agent=Assistant(room=ctx.room),
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


if __name__ == "__main__":
    cli.run_app(server)
