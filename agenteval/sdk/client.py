from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

try:
    import httpx
except ImportError as exc:  # pragma: no cover - dependency guard
    httpx = None
    _HTTPX_IMPORT_ERROR = exc
else:
    _HTTPX_IMPORT_ERROR = None


class AgentEvalClient:
    """Thin HTTP transport for hosted AgentEval deployments."""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        retries: int = 2,
        batch_size: int = 100,
    ) -> None:
        if not api_url:
            raise ValueError("api_url is required for hosted AgentEval transport")
        if not api_key:
            raise ValueError("api_key is required for hosted AgentEval transport")
        if httpx is None:
            raise RuntimeError(f"httpx is required for hosted AgentEval transport: {_HTTPX_IMPORT_ERROR}")

        self.api_url = api_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.batch_size = max(1, int(batch_size))
        self._client = httpx.Client(
            timeout=timeout,
            headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        )

    def close(self) -> None:
        self._client.close()

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.api_url}{path}"
        last_error: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                response = self._client.post(url, content=json.dumps(payload))
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt >= self.retries:
                    break
        raise RuntimeError(f"AgentEval hosted ingestion failed for {path}: {last_error}")

    def submit_trace(self, trace_node: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/api/v1/traces", trace_node)

    def submit_traces(self, trace_nodes: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
        payload = {"traces": list(trace_nodes)}
        return self._post("/api/v1/traces/batch", payload)

