from __future__ import annotations

from sqlalchemy import (
    Column,
    Float,
    Integer,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)

metadata = MetaData()

users = Table(
    "users",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("api_key_hash", String, nullable=False, unique=True),
    Column("created_at", String, nullable=False),
)

traces = Table(
    "traces",
    metadata,
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
    Column("profile_id", String, nullable=True),
    Column("profile_version", String, nullable=True),
    UniqueConstraint("session_id", "node_id", "attempt_number", name="uq_session_node_attempt"),
)

node_profiles = Table(
    "node_profiles",
    metadata,
    Column("profile_id", String, primary_key=True),
    Column("session_id", String, nullable=True),
    Column("node_id", String, nullable=False),
    Column("profile_signature", String, nullable=False),
    Column("profile_version", String, nullable=False),
    Column("inferred_role", String, nullable=False),
    Column("purpose", Text, nullable=True),
    Column("responsibilities", Text, nullable=True),
    Column("inputs_summary", Text, nullable=True),
    Column("outputs_summary", Text, nullable=True),
    Column("tools_used", Text, nullable=True),
    Column("evaluation_dimensions", Text, nullable=True),
    Column("executable_metrics", Text, nullable=True),
    Column("metric_weights", Text, nullable=True),
    Column("confidence", Float, default=1.0),
    Column("created_at", String, nullable=False),
    Column("updated_at", String, nullable=False),
    Column("user_id", String, nullable=True),
)

eval_cache = Table(
    "eval_cache",
    metadata,
    Column("input_hash", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("metric_name", String, nullable=False),
    Column("result_json", Text, nullable=False),
    Column("timestamp", String, nullable=False),
)

session_links = Table(
    "session_links",
    metadata,
    Column("child_session_id", String, nullable=False),
    Column("parent_session_id", String, nullable=False),
    Column("link_reason", String, nullable=True),
    Column("timestamp", String, nullable=False),
    Column("user_id", String, nullable=True),
    PrimaryKeyConstraint("child_session_id", "parent_session_id"),
)

