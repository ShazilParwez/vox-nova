import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "caller_data.db")

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    try:
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    name TEXT,
                    language_preference TEXT,
                    last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS facts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    fact_key TEXT,
                    fact_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS queries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    query_text TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS escalations (
                    reference_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    who_needs_help TEXT,
                    issue TEXT,
                    what_happened TEXT,
                    what_agent_checked TEXT,
                    urgency TEXT,
                    language TEXT,
                    preferred_follow_up TEXT,
                    status TEXT DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(user_id) REFERENCES users(user_id)
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS call_analytics (
                    call_id TEXT PRIMARY KEY,
                    user_id TEXT,
                    channel TEXT,
                    outcome TEXT,
                    success_reason TEXT,
                    failure_reason TEXT,
                    started_at TIMESTAMP,
                    ended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration_seconds INTEGER
                )
            """)
            conn.commit()
    except Exception as e:
        print(f"Failed to initialize database: {e}")

def lookup_caller(user_id: str):
    """Looks up a caller by user_id and returns their details and facts."""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            user = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            if not user:
                return {"found": False}
            
            facts = conn.execute("SELECT fact_key, fact_value FROM facts WHERE user_id = ?", (user_id,)).fetchall()
            
            return {
                "found": True,
                "user_id": user["user_id"],
                "name": user["name"],
                "language_preference": user["language_preference"],
                "facts": {f["fact_key"]: f["fact_value"] for f in facts},
                "last_interaction": user["last_interaction"]
            }
    except Exception as e:
        print(f"Error looking up caller: {e}")
        return {"found": False, "error": str(e)}

def save_caller_memory(user_id: str, name: str, facts: dict, language_preference: str = ""):
    """Creates or updates a caller record and saves approved facts."""
    try:
        with get_connection() as conn:
            # Upsert the user
            conn.execute("""
                INSERT INTO users (user_id, name, language_preference, last_interaction)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id) DO UPDATE SET
                    name = excluded.name,
                    language_preference = excluded.language_preference,
                    last_interaction = CURRENT_TIMESTAMP
            """, (user_id, name, language_preference))
            
            # Insert facts
            for k, v in facts.items():
                conn.execute("""
                    INSERT INTO facts (user_id, fact_key, fact_value)
                    VALUES (?, ?, ?)
                """, (user_id, k, v))
            
            conn.commit()
        return True
    except Exception as e:
        print(f"Error saving caller memory: {e}")
        return False

def save_query(user_id: str, query_text: str):
    """Saves a transcribed user query to the database."""
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO queries (user_id, query_text)
                VALUES (?, ?)
            """, (user_id, query_text))
            conn.commit()
    except Exception as e:
        print(f"Error saving query: {e}")

def create_escalation_record(reference_id: str, user_id: str, who_needs_help: str, issue: str, what_happened: str, what_agent_checked: str, urgency: str, language: str, preferred_follow_up: str):
    """Saves a new human escalation request."""
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT INTO escalations (reference_id, user_id, who_needs_help, issue, what_happened, what_agent_checked, urgency, language, preferred_follow_up)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (reference_id, user_id, who_needs_help, issue, what_happened, what_agent_checked, urgency, language, preferred_follow_up))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error saving escalation: {e}")
        return False

def get_escalations():
    """Retrieves all escalations."""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            return [dict(row) for row in conn.execute("SELECT * FROM escalations ORDER BY created_at DESC").fetchall()]
    except Exception as e:
        print(f"Error retrieving escalations: {e}")
        return []

def save_call_analytics(call_id: str, user_id: str, channel: str, outcome: str, success_reason: str, failure_reason: str, started_at: str, duration_seconds: int):
    """Saves the final outcome of a call session for analytics."""
    try:
        with get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO call_analytics (call_id, user_id, channel, outcome, success_reason, failure_reason, started_at, duration_seconds)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (call_id, user_id, channel, outcome, success_reason, failure_reason, started_at, duration_seconds))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error saving call analytics: {e}")
        return False

def get_analytics_summary():
    """Returns the total, successful, and failed call counts."""
    try:
        with get_connection() as conn:
            conn.row_factory = sqlite3.Row
            total_calls = conn.execute("SELECT COUNT(*) as count FROM call_analytics").fetchone()["count"]
            successful_calls = conn.execute("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'success'").fetchone()["count"]
            failed_calls = conn.execute("SELECT COUNT(*) as count FROM call_analytics WHERE outcome = 'failed'").fetchone()["count"]
            
            # Optional: Fetch last 5 calls for display
            recent = conn.execute("SELECT call_id, channel, outcome, ended_at FROM call_analytics ORDER BY ended_at DESC LIMIT 5").fetchall()
            recent_calls = [dict(r) for r in recent]
            
            return {
                "total_calls": total_calls,
                "successful_calls": successful_calls,
                "failed_calls": failed_calls,
                "recent_calls": recent_calls
            }
    except Exception as e:
        print(f"Error retrieving analytics: {e}")
        return {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "recent_calls": []
        }
