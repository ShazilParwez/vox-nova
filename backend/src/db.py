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
