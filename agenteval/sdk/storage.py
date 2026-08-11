import os
import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import (
    create_engine, MetaData, Table, Column, Integer, String, Text, Float,
    PrimaryKeyConstraint, UniqueConstraint, select, insert, update, delete, or_, and_, func
)
from sqlalchemy.pool import NullPool

class TraceStore:
    def __init__(self, db_path: str = "agenteval.db"):
        self.db_path = db_path
        
        # Resolve database URL
        env_url = os.environ.get("AGENTEVAL_DATABASE_URL")
        if db_path.startswith("postgresql://") or db_path.startswith("postgres://") or db_path.startswith("sqlite://"):
            db_url = db_path
        elif db_path != "agenteval.db":
            normalized = db_path.replace("\\", "/")
            db_url = f"sqlite:///{normalized}"
        elif env_url:
            db_url = env_url
        else:
            db_url = f"sqlite:///{db_path}"
            
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
            
        self.db_url = db_url
        
        connect_args = {}
        engine_kwargs = {"pool_pre_ping": True}
        if db_url.startswith("sqlite"):
            connect_args["check_same_thread"] = False
            engine_kwargs["poolclass"] = NullPool
            
        self.engine = create_engine(self.db_url, connect_args=connect_args, **engine_kwargs)
        self.metadata = MetaData()

        # Define schema tables
        self.users = Table(
            "users",
            self.metadata,
            Column("user_id", String, primary_key=True),
            Column("api_key_hash", String, nullable=False, unique=True),
            Column("created_at", String, nullable=False),
        )

        self.traces = Table(
            "traces",
            self.metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("session_id", String, nullable=False),
            Column("node_id", String, nullable=False),
            Column("node_type", String, nullable=False),
            Column("timestamp_start", String, nullable=False),
            Column("timestamp_end", String, nullable=False),
            Column("inputs", Text, nullable=True),
            Column("outputs", Text, nullable=True),
            Column("tool_name", String, nullable=True),
            Column("tool_args", Text, nullable=True),
            Column("tool_result", Text, nullable=True),
            Column("retrieved_docs", Text, nullable=True),
            Column("tokens_in", Integer, default=0),
            Column("tokens_out", Integer, default=0),
            Column("cost_usd", Float, default=0.0),
            Column("parent_node_ids", Text, nullable=True),
            Column("attempt_number", Integer, default=1),
            Column("user_id", String, nullable=True),
            UniqueConstraint("session_id", "node_id", "attempt_number", name="uq_session_node_attempt"),
        )

        self.eval_cache = Table(
            "eval_cache",
            self.metadata,
            Column("input_hash", String, primary_key=True),
            Column("metric_name", String, nullable=False),
            Column("result_json", Text, nullable=False),
            Column("timestamp", String, nullable=False),
        )

        self.session_links = Table(
            "session_links",
            self.metadata,
            Column("child_session_id", String, nullable=False),
            Column("parent_session_id", String, nullable=False),
            Column("link_reason", String, nullable=True),
            Column("timestamp", String, nullable=False),
            Column("user_id", String, nullable=True),
            PrimaryKeyConstraint("child_session_id", "parent_session_id"),
        )

        self.init_db()

    def init_db(self):
        """Initializes database tables using SQLAlchemy metadata."""
        self.metadata.create_all(self.engine)

    def resolve_user_id(self, api_key: str) -> Optional[str]:
        """Resolves user_id from plaintext API key hash lookup."""
        if not api_key:
            return None
        h = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        stmt = select(self.users.c.user_id).where(self.users.c.api_key_hash == h)
        with self.engine.connect() as conn:
            result = conn.execute(stmt).fetchone()
            return result[0] if result else None

    def create_user(self, user_id: str, api_key: str):
        """Creates or updates a user entry by storing its SHA-256 API key hash."""
        h = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
        now_str = datetime.now().isoformat()
        
        with self.engine.begin() as conn:
            stmt_select = select(self.users.c.user_id).where(self.users.c.user_id == user_id)
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                stmt_update = (
                    update(self.users)
                    .where(self.users.c.user_id == user_id)
                    .values(api_key_hash=h, created_at=now_str)
                )
                conn.execute(stmt_update)
            else:
                stmt_insert = insert(self.users).values(
                    user_id=user_id, api_key_hash=h, created_at=now_str
                )
                conn.execute(stmt_insert)

    def get_cached_result(self, input_hash: str) -> Optional[Dict[str, Any]]:
        """Retrieves a cached evaluation result if it exists."""
        stmt = select(self.eval_cache.c.result_json).where(self.eval_cache.c.input_hash == input_hash)
        with self.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if row:
                return json.loads(row[0])
            return None

    def set_cached_result(self, input_hash: str, metric_name: str, result: Dict[str, Any]):
        """Stores or overwrites an evaluation result in the cache database."""
        now_str = datetime.now().isoformat()
        result_json = json.dumps(result)
        
        with self.engine.begin() as conn:
            stmt_select = select(self.eval_cache.c.input_hash).where(self.eval_cache.c.input_hash == input_hash)
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                stmt_update = (
                    update(self.eval_cache)
                    .where(self.eval_cache.c.input_hash == input_hash)
                    .values(metric_name=metric_name, result_json=result_json, timestamp=now_str)
                )
                conn.execute(stmt_update)
            else:
                stmt_insert = insert(self.eval_cache).values(
                    input_hash=input_hash, metric_name=metric_name, result_json=result_json, timestamp=now_str
                )
                conn.execute(stmt_insert)

    def save_trace_node(self, trace_node: Dict[str, Any]):
        """Saves a single trace node data to the database."""
        inputs_json = json.dumps(trace_node.get("inputs"))
        outputs_json = json.dumps(trace_node.get("outputs"))
        tool_args_json = json.dumps(trace_node.get("tool_args")) if trace_node.get("tool_args") is not None else None
        tool_result_json = json.dumps(trace_node.get("tool_result")) if trace_node.get("tool_result") is not None else None
        retrieved_docs_json = json.dumps(trace_node.get("retrieved_docs")) if trace_node.get("retrieved_docs") is not None else None
        
        parent_node_ids = trace_node.get("parent_node_ids", [])
        parent_node_ids_json = json.dumps(parent_node_ids)
        
        session_id = trace_node["session_id"]
        node_id = trace_node["node_id"]
        attempt_number = trace_node.get("attempt_number", 1)
        
        values_dict = {
            "session_id": session_id,
            "node_id": node_id,
            "node_type": trace_node["node_type"],
            "timestamp_start": trace_node["timestamp_start"],
            "timestamp_end": trace_node["timestamp_end"],
            "inputs": inputs_json,
            "outputs": outputs_json,
            "tool_name": trace_node.get("tool_name"),
            "tool_args": tool_args_json,
            "tool_result": tool_result_json,
            "retrieved_docs": retrieved_docs_json,
            "tokens_in": trace_node.get("tokens_in", 0),
            "tokens_out": trace_node.get("tokens_out", 0),
            "cost_usd": trace_node.get("cost_usd", 0.0),
            "parent_node_ids": parent_node_ids_json,
            "attempt_number": attempt_number,
            "user_id": trace_node.get("user_id"),
        }

        with self.engine.begin() as conn:
            stmt_select = select(self.traces.c.id).where(
                and_(
                    self.traces.c.session_id == session_id,
                    self.traces.c.node_id == node_id,
                    self.traces.c.attempt_number == attempt_number,
                )
            )
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                stmt_update = (
                    update(self.traces)
                    .where(self.traces.c.id == existing[0])
                    .values(**values_dict)
                )
                conn.execute(stmt_update)
            else:
                stmt_insert = insert(self.traces).values(**values_dict)
                conn.execute(stmt_insert)

    def get_session_traces(self, session_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieves all trace nodes for a given session."""
        stmt = select(self.traces).where(self.traces.c.session_id == session_id)
        if user_id:
            stmt = stmt.where(or_(self.traces.c.user_id == user_id, self.traces.c.user_id.is_(None)))
        stmt = stmt.order_by(self.traces.c.timestamp_start.asc())

        with self.engine.connect() as conn:
            result = conn.execute(stmt)
            rows = result.mappings().all()
            
            traces = []
            for row in rows:
                trace = dict(row)
                trace["inputs"] = json.loads(trace["inputs"]) if trace["inputs"] else None
                trace["outputs"] = json.loads(trace["outputs"]) if trace["outputs"] else None
                trace["tool_args"] = json.loads(trace["tool_args"]) if trace["tool_args"] else None
                trace["tool_result"] = json.loads(trace["tool_result"]) if trace["tool_result"] else None
                trace["retrieved_docs"] = json.loads(trace["retrieved_docs"]) if trace["retrieved_docs"] else None
                trace["parent_node_ids"] = json.loads(trace["parent_node_ids"]) if trace["parent_node_ids"] else []
                traces.append(trace)
            return traces

    def save_session_link(self, child_session_id: str, parent_session_id: str, link_reason: Optional[str] = None, user_id: Optional[str] = None):
        """Saves a link between a child session and its parent session."""
        now_str = datetime.now().isoformat()
        values_dict = {
            "child_session_id": child_session_id,
            "parent_session_id": parent_session_id,
            "link_reason": link_reason,
            "timestamp": now_str,
            "user_id": user_id,
        }

        with self.engine.begin() as conn:
            stmt_select = select(self.session_links.c.child_session_id).where(
                and_(
                    self.session_links.c.child_session_id == child_session_id,
                    self.session_links.c.parent_session_id == parent_session_id,
                )
            )
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                stmt_update = (
                    update(self.session_links)
                    .where(
                        and_(
                            self.session_links.c.child_session_id == child_session_id,
                            self.session_links.c.parent_session_id == parent_session_id,
                        )
                    )
                    .values(**values_dict)
                )
                conn.execute(stmt_update)
            else:
                stmt_insert = insert(self.session_links).values(**values_dict)
                conn.execute(stmt_insert)

    def get_parent_session_ids(self, child_session_id: str, user_id: Optional[str] = None) -> List[str]:
        """Gets all direct parent session IDs for a given child session."""
        stmt = select(self.session_links.c.parent_session_id).where(
            self.session_links.c.child_session_id == child_session_id
        )
        if user_id:
            stmt = stmt.where(
                or_(self.session_links.c.user_id == user_id, self.session_links.c.user_id.is_(None))
            )

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return [row[0] for row in rows]

    def list_session_summaries(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists distinct sessions with their earliest start time."""
        min_start = func.min(self.traces.c.timestamp_start).label("start_time")
        stmt = (
            select(self.traces.c.session_id, min_start)
            .group_by(self.traces.c.session_id)
            .order_by(min_start.desc())
        )
        if user_id:
            stmt = stmt.where(or_(self.traces.c.user_id == user_id, self.traces.c.user_id.is_(None)))

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return [{"session_id": row[0], "start_time": row[1]} for row in rows]

    def get_distinct_session_ids(self, user_id: Optional[str] = None) -> List[str]:
        """Gets list of all distinct session_ids."""
        stmt = select(self.traces.c.session_id).distinct()
        if user_id:
            stmt = stmt.where(or_(self.traces.c.user_id == user_id, self.traces.c.user_id.is_(None)))

        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return [row[0] for row in rows]

    def delete_case_traces(self, user_id: str, case_prefix: str):
        """Deletes traces and session_links for a specific case prefix."""
        pattern = f"session_{case_prefix}_%"
        with self.engine.begin() as conn:
            conn.execute(
                delete(self.traces).where(
                    and_(
                        self.traces.c.user_id == user_id,
                        self.traces.c.session_id.like(pattern),
                    )
                )
            )
            conn.execute(
                delete(self.session_links).where(
                    and_(
                        self.session_links.c.user_id == user_id,
                        or_(
                            self.session_links.c.child_session_id.like(pattern),
                            self.session_links.c.parent_session_id.like(pattern),
                        ),
                    )
                )
            )

    def clear_user_data(self, user_id: str):
        """Clears all traces and links for a user."""
        with self.engine.begin() as conn:
            conn.execute(delete(self.traces).where(self.traces.c.user_id == user_id))
            conn.execute(delete(self.session_links).where(self.session_links.c.user_id == user_id))

    def update_branching_topology(self, session_id: str):
        """Updates parent_node_ids and merges retrieved docs for parallel branching research agent nodes."""
        with self.engine.begin() as conn:
            conn.execute(
                update(self.traces)
                .where(and_(self.traces.c.session_id == session_id, self.traces.c.node_id.in_(["policy_retriever", "product_retriever"])))
                .values(parent_node_ids=json.dumps(["planner"]))
            )
            conn.execute(
                update(self.traces)
                .where(and_(self.traces.c.session_id == session_id, self.traces.c.node_id == "synthesizer"))
                .values(parent_node_ids=json.dumps(["policy_retriever", "product_retriever"]))
            )
            conn.execute(
                update(self.traces)
                .where(and_(self.traces.c.session_id == session_id, self.traces.c.node_id == "critic"))
                .values(parent_node_ids=json.dumps(["synthesizer"]))
            )
            
            stmt_docs = select(self.traces.c.retrieved_docs).where(
                and_(self.traces.c.session_id == session_id, self.traces.c.node_id.in_(["policy_retriever", "product_retriever"]))
            )
            rows = conn.execute(stmt_docs).fetchall()
            merged_docs = []
            for row in rows:
                if row[0]:
                    try:
                        docs_list = json.loads(row[0])
                        if isinstance(docs_list, list):
                            merged_docs.extend(docs_list)
                    except Exception:
                        pass
                        
            conn.execute(
                update(self.traces)
                .where(and_(self.traces.c.session_id == session_id, self.traces.c.node_id == "synthesizer"))
                .values(retrieved_docs=json.dumps(merged_docs))
            )

    def close(self):
        """Disposes engine connections."""
        if hasattr(self, "engine"):
            self.engine.dispose()
