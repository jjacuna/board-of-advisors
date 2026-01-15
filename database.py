import sqlite3
import os

DATABASE = "board.db"


def get_db_connection():
    """Create a database connection."""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize the database with schema."""
    conn = get_db_connection()

    with open("schema.sql", "r") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()


def save_conversation(question: str, advisor_responses: list, ceo_decision: str) -> int:
    """Save a complete conversation to the database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Insert the conversation
    cursor.execute(
        "INSERT INTO conversations (user_question) VALUES (?)",
        (question,)
    )
    conversation_id = cursor.lastrowid

    # Insert advisor responses
    for advisor in advisor_responses:
        cursor.execute(
            """INSERT INTO advisor_responses
               (conversation_id, advisor_name, advisor_role, response, model_used)
               VALUES (?, ?, ?, ?, ?)""",
            (conversation_id, advisor["name"], advisor["role"],
             advisor["response"], advisor["model"])
        )

    # Insert CEO decision
    cursor.execute(
        """INSERT INTO executive_decisions
           (conversation_id, decision, model_used)
           VALUES (?, ?, ?)""",
        (conversation_id, ceo_decision, "openai/gpt-4o-mini")
    )

    conn.commit()
    conn.close()

    return conversation_id


def get_history(limit: int = 10) -> list:
    """Get conversation history with all responses."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Get conversations
    cursor.execute(
        """SELECT id, user_question, created_at
           FROM conversations
           ORDER BY created_at DESC
           LIMIT ?""",
        (limit,)
    )
    conversations = cursor.fetchall()

    result = []
    for conv in conversations:
        # Get advisor responses for this conversation
        cursor.execute(
            """SELECT advisor_name, advisor_role, response, model_used
               FROM advisor_responses
               WHERE conversation_id = ?""",
            (conv["id"],)
        )
        advisors = [dict(row) for row in cursor.fetchall()]

        # Get CEO decision
        cursor.execute(
            """SELECT decision, model_used
               FROM executive_decisions
               WHERE conversation_id = ?""",
            (conv["id"],)
        )
        ceo_row = cursor.fetchone()
        ceo_decision = dict(ceo_row) if ceo_row else None

        result.append({
            "id": conv["id"],
            "question": conv["user_question"],
            "created_at": conv["created_at"],
            "advisors": advisors,
            "ceo_decision": ceo_decision
        })

    conn.close()
    return result


def get_advisor_settings() -> dict:
    """Get all advisor settings from database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT advisor_key, name, role, model, system_prompt FROM advisor_settings")
    rows = cursor.fetchall()

    conn.close()

    return {row["advisor_key"]: dict(row) for row in rows}


def save_advisor_setting(advisor_key: str, name: str, role: str, model: str, system_prompt: str):
    """Save or update an advisor setting."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO advisor_settings (advisor_key, name, role, model, system_prompt, updated_at)
           VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
           ON CONFLICT(advisor_key) DO UPDATE SET
           name = excluded.name,
           role = excluded.role,
           model = excluded.model,
           system_prompt = excluded.system_prompt,
           updated_at = CURRENT_TIMESTAMP""",
        (advisor_key, name, role, model, system_prompt)
    )

    conn.commit()
    conn.close()


def save_document(filename: str, file_type: str, file_size: int) -> int:
    """Save document metadata and return document ID."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO documents (filename, file_type, file_size, status)
           VALUES (?, ?, ?, 'processing')""",
        (filename, file_type, file_size)
    )
    doc_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return doc_id


def update_document_status(doc_id: int, status: str, chunk_count: int = None):
    """Update document processing status."""
    conn = get_db_connection()
    cursor = conn.cursor()

    if chunk_count is not None:
        cursor.execute(
            "UPDATE documents SET status = ?, chunk_count = ? WHERE id = ?",
            (status, chunk_count, doc_id)
        )
    else:
        cursor.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            (status, doc_id)
        )

    conn.commit()
    conn.close()


def get_documents() -> list:
    """Get all documents with metadata."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, filename, file_type, file_size, chunk_count, status, created_at
           FROM documents
           ORDER BY created_at DESC"""
    )
    documents = [dict(row) for row in cursor.fetchall()]

    conn.close()
    return documents


def delete_document(doc_id: int) -> bool:
    """Delete document metadata from database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    deleted = cursor.rowcount > 0

    conn.commit()
    conn.close()

    return deleted
