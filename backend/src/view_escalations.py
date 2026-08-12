import db

def view_escalations():
    print("\n" + "="*80)
    print("FINSAATHI HUMAN ESCALATION DASHBOARD")
    print("="*80 + "\n")
    
    escalations = db.get_escalations()
    if not escalations:
        print("No open escalation requests found.")
        print("="*80 + "\n")
        return

    for esc in escalations:
        print(f"Reference ID : {esc.get('reference_id', 'N/A')}")
        print(f"Status       : {esc.get('status', 'open').upper()}")
        print(f"Created At   : {esc.get('created_at', 'N/A')}")
        print(f"User ID      : {esc.get('user_id', 'N/A')}")
        print(f"Who Needs    : {esc.get('who_needs_help', 'N/A')}")
        print(f"Urgency      : {esc.get('urgency', 'N/A')}")
        print(f"Language     : {esc.get('language', 'N/A')}")
        print(f"Follow Up    : {esc.get('preferred_follow_up', 'N/A')}")
        print("-" * 40)
        print("Issue:")
        print(f"  {esc.get('issue', 'N/A')}")
        print("What Happened:")
        print(f"  {esc.get('what_happened', 'N/A')}")
        print("What FinSaathi Checked:")
        print(f"  {esc.get('what_agent_checked', 'N/A')}")
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    # Ensure tables exist
    db.init_db()
    view_escalations()
