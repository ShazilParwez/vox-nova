import db
import uuid
from datetime import datetime

def test_db():
    print("Testing DB escalation creation...")
    db.init_db()
    
    ref_id = f"ESC-TEST-{uuid.uuid4().hex[:4].upper()}"
    success = db.create_escalation_record(
        reference_id=ref_id,
        user_id="test_user_1",
        who_needs_help="Shazil",
        issue="Suspected Fraud",
        what_happened="Unauthorized transaction of 5000 rs",
        what_agent_checked="Confirmed user has access to account, advised to block card",
        urgency="High",
        language="Hinglish",
        preferred_follow_up="Phone"
    )
    
    assert success, "Failed to create escalation record"
    print("Created successfully.")
    
    escalations = db.get_escalations()
    found = False
    for esc in escalations:
        if esc['reference_id'] == ref_id:
            found = True
            break
            
    assert found, "Record not found in DB"
    print("Record retrieved successfully!")

if __name__ == "__main__":
    test_db()
