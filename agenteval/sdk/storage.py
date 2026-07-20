import json
import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

class TraceStore:
    def __init__(self, db_path: str = "agenteval.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initializes database tables mapping to Appendix A of the PRD."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Check if attempt_number column exists in traces table
            cursor = conn.execute("PRAGMA table_info(traces)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "attempt_number" not in columns:
                # Old schema -> migrate smoothly by dropping traces table
                with conn:
                    conn.execute("DROP TABLE IF EXISTS traces")

            with conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id TEXT PRIMARY KEY,
                        api_key_hash TEXT NOT NULL UNIQUE,
                        created_at TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS traces (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        node_id TEXT NOT NULL,
                        node_type TEXT NOT NULL,          -- planner | retriever | generator | critic | tool | custom
                        timestamp_start TEXT NOT NULL,
                        timestamp_end TEXT NOT NULL,
                        inputs TEXT,                      -- JSON string
                        outputs TEXT,                     -- JSON string
                        tool_name TEXT,
                        tool_args TEXT,                   -- JSON string
                        tool_result TEXT,                 -- JSON string
                        retrieved_docs TEXT,              -- JSON list of {text, similarity_score}
                        tokens_in INTEGER DEFAULT 0,
                        tokens_out INTEGER DEFAULT 0,
                        cost_usd REAL DEFAULT 0.0,
                        parent_node_ids TEXT,             -- JSON list of string node IDs to support branching/loops
                        attempt_number INTEGER DEFAULT 1,
                        user_id TEXT,
                        UNIQUE(session_id, node_id, attempt_number)
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS eval_cache (
                        input_hash TEXT PRIMARY KEY,
                        metric_name TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                """)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS session_links (
                        child_session_id TEXT NOT NULL,
                        parent_session_id TEXT NOT NULL,
                        link_reason TEXT,
                        timestamp TEXT NOT NULL,
                        user_id TEXT,
                        PRIMARY KEY (child_session_id, parent_session_id)
                    )
                """)

            # Dynamic migrations to add user_id column if missing in existing databases
            cursor = conn.execute("PRAGMA table_info(traces)")
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "user_id" not in columns:
                with conn:
                    conn.execute("ALTER TABLE traces ADD COLUMN user_id TEXT")

            cursor = conn.execute("PRAGMA table_info(session_links)")
            link_columns = [row[1] for row in cursor.fetchall()]
            if link_columns and "user_id" not in link_columns:
                with conn:
                    conn.execute("ALTER TABLE session_links ADD COLUMN user_id TEXT")
        finally:
            conn.close()

    def resolve_user_id(self, api_key: str) -> Optional[str]:
        """Resolves user_id from plaintext API key hash lookup."""
        if not api_key:
            return None
        h = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT user_id FROM users WHERE api_key_hash = ?", (h,))
            row = cursor.fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def create_user(self, user_id: str, api_key: str):
        """Creates a user with plaintext API key by storing its SHA-256 hash."""
        h = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO users (user_id, api_key_hash, created_at) VALUES (?, ?, ?)",
                    (user_id, h, datetime.now().isoformat())
                )
        finally:
            conn.close()

    def get_cached_result(self, input_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached evaluation result if it exists."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute("SELECT result_json FROM eval_cache WHERE input_hash = ?", (input_hash,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None
        finally:
            conn.close()

    def set_cached_result(self, input_hash: str, metric_name: str, result: Dict[str, Any]):
        """Stores or overwrites an evaluation result in the cache database."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO eval_cache (input_hash, metric_name, result_json, timestamp) VALUES (?, ?, ?, ?)",
                    (input_hash, metric_name, json.dumps(result), datetime.now().isoformat())
                )
        finally:
            conn.close()

    def save_trace_node(self, trace_node: Dict[str, Any]):
        """Saves a single trace node data to the SQLite database."""
        # Convert dictionary values to JSON strings where appropriate
        inputs_json = json.dumps(trace_node.get("inputs"))
        outputs_json = json.dumps(trace_node.get("outputs"))
        tool_args_json = json.dumps(trace_node.get("tool_args")) if trace_node.get("tool_args") is not None else None
        tool_result_json = json.dumps(trace_node.get("tool_result")) if trace_node.get("tool_result") is not None else None
        retrieved_docs_json = json.dumps(trace_node.get("retrieved_docs")) if trace_node.get("retrieved_docs") is not None else None
        
        # parent_node_ids MUST be stored as a list/JSON array to support branching/parallel pipelines
        parent_node_ids = trace_node.get("parent_node_ids", [])
        parent_node_ids_json = json.dumps(parent_node_ids)

        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute("""
                    INSERT OR REPLACE INTO traces (
                        session_id, node_id, node_type, timestamp_start, timestamp_end,
                        inputs, outputs, tool_name, tool_args, tool_result,
                        retrieved_docs, tokens_in, tokens_out, cost_usd, parent_node_ids,
                        attempt_number, user_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trace_node["session_id"],
                    trace_node["node_id"],
                    trace_node["node_type"],
                    trace_node["timestamp_start"],
                    trace_node["timestamp_end"],
                    inputs_json,
                    outputs_json,
                    trace_node.get("tool_name"),
                    tool_args_json,
                    tool_result_json,
                    retrieved_docs_json,
                    trace_node.get("tokens_in", 0),
                    trace_node.get("tokens_out", 0),
                    trace_node.get("cost_usd", 0.0),
                    parent_node_ids_json,
                    trace_node.get("attempt_number", 1),
                    trace_node.get("user_id")
                ))
        finally:
            conn.close()

    def get_session_traces(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all trace nodes for a given session."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.row_factory = sqlite3.Row
            if user_id:
                cursor = conn.execute(
                    "SELECT * FROM traces WHERE session_id = ? AND (user_id = ? OR user_id IS NULL) ORDER BY timestamp_start ASC",
                    (session_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM traces WHERE session_id = ? ORDER BY timestamp_start ASC",
                    (session_id,)
                )
            rows = cursor.fetchall()
            
            traces = []
            for row in rows:
                trace = dict(row)
                # Deserialize JSON fields
                trace["inputs"] = json.loads(trace["inputs"]) if trace["inputs"] else None
                trace["outputs"] = json.loads(trace["outputs"]) if trace["outputs"] else None
                trace["tool_args"] = json.loads(trace["tool_args"]) if trace["tool_args"] else None
                trace["tool_result"] = json.loads(trace["tool_result"]) if trace["tool_result"] else None
                trace["retrieved_docs"] = json.loads(trace["retrieved_docs"]) if trace["retrieved_docs"] else None
                trace["parent_node_ids"] = json.loads(trace["parent_node_ids"]) if trace["parent_node_ids"] else []
                traces.append(trace)
            return traces
        finally:
            conn.close()

    def save_session_link(self, child_session_id: str, parent_session_id: str, link_reason: Optional[str] = None, user_id: Optional[str] = None):
        """Saves a link between a child session and its parent session."""
        conn = sqlite3.connect(self.db_path)
        try:
            with conn:
                conn.execute(
                    "INSERT OR REPLACE INTO session_links (child_session_id, parent_session_id, link_reason, timestamp, user_id) VALUES (?, ?, ?, ?, ?)",
                    (child_session_id, parent_session_id, link_reason, datetime.now().isoformat(), user_id)
                )
        finally:
            conn.close()

    def get_parent_session_ids(self, child_session_id: str, user_id: Optional[str] = None) -> List[str]:
        """Gets all direct parent session IDs for a given child session."""
        conn = sqlite3.connect(self.db_path)
        try:
            if user_id:
                cursor = conn.execute(
                    "SELECT parent_session_id FROM session_links WHERE child_session_id = ? AND (user_id = ? OR user_id IS NULL)",
                    (child_session_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT parent_session_id FROM session_links WHERE child_session_id = ?",
                    (child_session_id,)
                )
            return [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
