import sqlite3
import json
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

# Use the data directory for the sqlite DB
DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "chat_history.db"

def _get_connection():
    # Ensure data directory exists
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the SQLite database for chat history."""
    try:
        with _get_connection() as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL, -- 'user' or 'assistant'
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id)')
            conn.commit()
            logger.info("Initialized chat history SQLite database.")
    except Exception as e:
        logger.error(f"Failed to initialize chat history DB: {e}")

def get_session_history(session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve the recent chat history for a given session."""
    try:
        with _get_connection() as conn:
            # Fetch the last N messages, ordered by time
            cursor = conn.execute('''
                SELECT role, content 
                FROM messages 
                WHERE session_id = ? 
                ORDER BY created_at ASC
            ''', (session_id,))
            rows = cursor.fetchall()
            
            # If we limit, we want the most recent N messages, but kept in chronological order
            # Since we fetched ASC, if there are more than `limit`, we just take the last `limit`
            history = [{"role": row["role"], "content": row["content"]} for row in rows]
            return history[-limit:]
    except Exception as e:
        logger.error(f"Failed to fetch session history: {e}")
        return []

def add_message(session_id: str, role: str, content: str):
    """Add a single message to a session's history."""
    try:
        with _get_connection() as conn:
            conn.execute('''
                INSERT INTO messages (session_id, role, content)
                VALUES (?, ?, ?)
            ''', (session_id, role, content))
            conn.commit()
    except Exception as e:
        logger.error(f"Failed to insert message into history: {e}")

# Initialize on module import
init_db()
