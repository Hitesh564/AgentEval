import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime

from sqlalchemy import (
    create_engine, select, insert, update, delete, or_, and_, func
)
from sqlalchemy import inspect
from agenteval.sdk.database import build_engine_options, database_backend_name, resolve_database_url
from agenteval.sdk.schema import metadata, users, traces, eval_cache, session_links

_PUBLIC_CACHE_USER_ID = "__public__"

class TraceStore:
    def __init__(
        self,
        db_path: Optional[str] = None,
        *,
        database_url: Optional[str] = None,
        allow_sqlite_fallback: bool = True,
        init_schema: Optional[bool] = None,
    ):
        self.db_path = db_path or database_url or "agenteval.db"
        self.db_url = resolve_database_url(
            database_url or db_path,
            allow_sqlite_fallback=allow_sqlite_fallback,
        )
        self.backend_name = database_backend_name(self.db_url)
        self.engine = create_engine(self.db_url, **build_engine_options(self.db_url))
        self.metadata = metadata
        self.users = users
        self.traces = traces
        self.eval_cache = eval_cache
        self.session_links = session_links
        from agenteval.sdk.schema import node_profiles
        self.node_profiles = node_profiles

        if init_schema is None:
            init_schema = self.backend_name == "sqlite"

        if init_schema:
            self.init_db()
        self.eval_cache_has_user_id = self._table_has_column("eval_cache", "user_id")

    def init_db(self):
        """Initializes database tables using SQLAlchemy metadata."""
        self.metadata.create_all(self.engine)

    def _normalize_cache_user_id(self, user_id: Optional[str]) -> str:
        normalized = (user_id or "").strip()
        return normalized or _PUBLIC_CACHE_USER_ID

    def _table_has_column(self, table_name: str, column_name: str) -> bool:
        if self.backend_name != "sqlite":
            return True
        try:
            inspector = inspect(self.engine)
            return any(column.get("name") == column_name for column in inspector.get_columns(table_name))
        except Exception:
            return False

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

    def get_cached_result(
        self,
        input_hash: str,
        user_id: Optional[str] = None,
        legacy_input_hashes: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Retrieves a cached evaluation result if it exists.

        The primary lookup uses the canonical SHA-256 cache key. Optional legacy
        hashes let us read pre-hardened MD5-backed cache rows without rewriting
        stored data.
        """
        cache_user_id = self._normalize_cache_user_id(user_id)
        candidate_hashes = [input_hash]
        if legacy_input_hashes and cache_user_id == _PUBLIC_CACHE_USER_ID:
            for legacy_hash in legacy_input_hashes:
                if legacy_hash and legacy_hash not in candidate_hashes:
                    candidate_hashes.append(legacy_hash)

        with self.engine.connect() as conn:
            for candidate_hash in candidate_hashes:
                query = select(self.eval_cache.c.result_json).where(self.eval_cache.c.input_hash == candidate_hash)
                if self.eval_cache_has_user_id:
                    query = query.where(self.eval_cache.c.user_id == cache_user_id)
                row = conn.execute(query).fetchone()
                if row:
                    return json.loads(row[0])
            return None

    def set_cached_result(
        self,
        input_hash: str,
        metric_name: str,
        result: Dict[str, Any],
        user_id: Optional[str] = None,
    ):
        """Stores or overwrites an evaluation result in the cache database."""
        now_str = datetime.now().isoformat()
        result_json = json.dumps(result)
        cache_user_id = self._normalize_cache_user_id(user_id)
        
        with self.engine.begin() as conn:
            stmt_select = select(self.eval_cache.c.input_hash).where(self.eval_cache.c.input_hash == input_hash)
            if self.eval_cache_has_user_id:
                stmt_select = stmt_select.where(self.eval_cache.c.user_id == cache_user_id)
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                stmt_update = (
                    update(self.eval_cache)
                    .where(self.eval_cache.c.input_hash == input_hash)
                    .values(metric_name=metric_name, result_json=result_json, timestamp=now_str)
                )
                if self.eval_cache_has_user_id:
                    stmt_update = stmt_update.where(self.eval_cache.c.user_id == cache_user_id)
                conn.execute(stmt_update)
            else:
                insert_values = {
                    "input_hash": input_hash,
                    "metric_name": metric_name,
                    "result_json": result_json,
                    "timestamp": now_str,
                }
                if self.eval_cache_has_user_id:
                    insert_values["user_id"] = cache_user_id
                stmt_insert = insert(self.eval_cache).values(**insert_values)
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
        parent_session_id = trace_node.get("parent_session_id")
        trace_user_id = trace_node.get("user_id")

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
        if parent_session_id:
            self.save_session_link(
                session_id,
                parent_session_id,
                link_reason="Handoff",
                user_id=trace_user_id,
            )

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
        cache_user_id = self._normalize_cache_user_id(user_id)
        with self.engine.begin() as conn:
            conn.execute(delete(self.traces).where(self.traces.c.user_id == user_id))
            conn.execute(delete(self.session_links).where(self.session_links.c.user_id == user_id))
            if self.eval_cache_has_user_id:
                conn.execute(delete(self.eval_cache).where(self.eval_cache.c.user_id == cache_user_id))

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

    def save_node_profile(self, profile_data: Dict[str, Any]):
        """Saves or updates a node profile in the node_profiles table."""
        profile_id = profile_data.get("profile_id")
        if not profile_id:
            return

        def _json_dumps_safe(obj: Any) -> Optional[str]:
            if obj is None:
                return None
            if isinstance(obj, str):
                return obj
            try:
                return json.dumps(obj, default=str)
            except Exception:
                return str(obj)

        now_str = datetime.now().isoformat()
        values = {
            "profile_id": profile_id,
            "session_id": profile_data.get("session_id"),
            "node_id": str(profile_data.get("node_id", "")),
            "profile_signature": str(profile_data.get("profile_signature", "")),
            "profile_version": str(profile_data.get("profile_version", "1.0")),
            "inferred_role": str(profile_data.get("inferred_role", "custom")),
            "purpose": str(profile_data.get("purpose", "")),
            "responsibilities": _json_dumps_safe(profile_data.get("responsibilities")),
            "inputs_summary": _json_dumps_safe(profile_data.get("inputs_summary")),
            "outputs_summary": _json_dumps_safe(profile_data.get("outputs_summary")),
            "tools_used": _json_dumps_safe(profile_data.get("tools_used")),
            "evaluation_dimensions": _json_dumps_safe(profile_data.get("evaluation_dimensions")),
            "executable_metrics": _json_dumps_safe(profile_data.get("executable_metrics")),
            "metric_weights": _json_dumps_safe(profile_data.get("metric_weights")),
            "confidence": float(profile_data.get("confidence", 1.0)),
            "created_at": str(profile_data.get("created_at") or now_str),
            "updated_at": now_str,
            "user_id": profile_data.get("user_id"),
        }

        with self.engine.begin() as conn:
            stmt_select = select(self.node_profiles.c.profile_id).where(self.node_profiles.c.profile_id == profile_id)
            existing = conn.execute(stmt_select).fetchone()
            if existing:
                conn.execute(
                    update(self.node_profiles)
                    .where(self.node_profiles.c.profile_id == profile_id)
                    .values(**values)
                )
            else:
                conn.execute(insert(self.node_profiles).values(**values))

    def get_node_profile(self, session_id: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a saved node profile by session_id and node_id."""
        stmt = (
            select(self.node_profiles)
            .where(and_(self.node_profiles.c.session_id == session_id, self.node_profiles.c.node_id == node_id))
            .order_by(self.node_profiles.c.updated_at.desc())
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if not row:
                return None
            return self._row_to_profile_dict(row)

    def get_profile_by_signature(self, signature: str) -> Optional[Dict[str, Any]]:
        """Retrieves a saved node profile by deterministic profile signature."""
        stmt = (
            select(self.node_profiles)
            .where(self.node_profiles.c.profile_signature == signature)
            .order_by(self.node_profiles.c.updated_at.desc())
        )
        with self.engine.connect() as conn:
            row = conn.execute(stmt).fetchone()
            if not row:
                return None
            return self._row_to_profile_dict(row)

    def list_session_profiles(self, session_id: str) -> List[Dict[str, Any]]:
        """Lists all node profiles for a session."""
        stmt = select(self.node_profiles).where(self.node_profiles.c.session_id == session_id)
        with self.engine.connect() as conn:
            rows = conn.execute(stmt).fetchall()
            return [self._row_to_profile_dict(r) for r in rows]

    def _row_to_profile_dict(self, row: Any) -> Dict[str, Any]:
        """Converts a database row into a structured profile dictionary."""
        def _parse_json(val: Optional[str]) -> Any:
            if not val:
                return []
            try:
                return json.loads(val)
            except Exception:
                return val

        # Handle row mapping safely
        data = dict(row._mapping) if hasattr(row, "_mapping") else dict(row)
        data["responsibilities"] = _parse_json(data.get("responsibilities"))
        data["inputs_summary"] = _parse_json(data.get("inputs_summary"))
        data["outputs_summary"] = _parse_json(data.get("outputs_summary"))
        data["tools_used"] = _parse_json(data.get("tools_used"))
        data["evaluation_dimensions"] = _parse_json(data.get("evaluation_dimensions"))
        data["executable_metrics"] = _parse_json(data.get("executable_metrics"))
        data["metric_weights"] = _parse_json(data.get("metric_weights"))
        return data

    def close(self):
        """Disposes engine connections."""
        if hasattr(self, "engine"):
            self.engine.dispose()

