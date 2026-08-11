import os
import sys
import uuid
import json
import asyncio
from dotenv import load_dotenv
from livekit.api import LiveKitAPI

from livekit.protocol.room import CreateRoomRequest
from livekit.protocol.agent_dispatch import CreateAgentDispatchRequest
from livekit.protocol.sip import CreateSIPParticipantRequest

load_dotenv(".env.local")

async def make_outbound_call(phone_number: str, context: dict) -> dict:
    trunk_id = os.getenv("LIVEKIT_SIP_TRUNK_ID")
    if not trunk_id:
        return {"success": False, "message": "LIVEKIT_SIP_TRUNK_ID not found in environment."}
    if not phone_number:
        return {"success": False, "message": "Phone number is required."}

    # Hide full phone number in logs
    masked_number = phone_number[:-4] + "****" if len(phone_number) > 4 else "****"
    print(f"Initiating outbound call to {masked_number}...")

    room_name = f"outbound-reminder-{uuid.uuid4().hex[:8]}"
    
    api = LiveKitAPI()
    try:
        # Create room with metadata describing the call context
        await api.room.create_room(
            CreateRoomRequest(
                name=room_name, 
                metadata=json.dumps(context), 
                empty_timeout=5 * 60
            )
        )
        
        # Dispatch the agent to the room
        # We assume AGENT_NAME is defined (default to my-agent)
        agent_name = os.getenv("AGENT_NAME", "my-agent")
        await api.agent_dispatch.create_dispatch(
            CreateAgentDispatchRequest(
                agent_name=agent_name,
                room=room_name,
            )
        )
        print(f"Dispatched agent '{agent_name}' to room '{room_name}'.")

        # Extract just the username/number if it's a SIP URI
        # LiveKit expects "shazilparwez" not "sip:shazilparwez@domain.com"
        call_to_user = phone_number
        if call_to_user.startswith("sip:"):
            call_to_user = call_to_user[4:]
        if "@" in call_to_user:
            call_to_user = call_to_user.split("@")[0]

        # Create SIP participant to dial the user
        sip_identity = f"sip_{uuid.uuid4().hex[:8]}"
        await api.sip.create_sip_participant(
            CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=call_to_user,
                room_name=room_name,
                participant_identity=sip_identity,
                participant_name="User"
            )
        )
        print(f"SIP participant created for {masked_number}.")
        
        return {
            "success": True,
            "room_name": room_name,
            "call_status": "initiated",
            "message": "Outbound call initiated successfully"
        }
    except Exception as e:
        print(f"Exception during outbound call setup: {e}")
        return {
            "success": False,
            "call_status": "failed",
            "message": f"Unable to initiate outbound call: {str(e)}"
        }
    finally:
        await api.aclose()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python outbound_call.py <phone_number> [scheme]")
        sys.exit(1)

    target_phone = sys.argv[1]
    target_scheme = sys.argv[2] if len(sys.argv) > 2 else "PMSBY"

    context = {
        "call_type": "financial_scheme_reminder",
        "scheme": target_scheme,
        "reason": "previously eligible scheme reminder"
    }
    
    result = asyncio.run(make_outbound_call(target_phone, context))
    print(json.dumps(result, indent=2))