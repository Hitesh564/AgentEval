import os
from locust import HttpUser, task, between

class AgentEvalDashboardUser(HttpUser):
    # Simulates realistic user think-time between dashboard interactions (0.5 to 1.5 seconds)
    wait_time = between(0.5, 1.5)
    
    def on_start(self):
        """Initializes API key header for each simulated load test user."""
        self.api_key = os.environ.get("AGENTEVAL_LOADTEST_KEY", "loadtest_secret_key_123")
        self.headers = {"X-API-Key": self.api_key}
        self.session_id = "session_calib_loadtest_001"

    @task(4)
    def view_session_list(self):
        """Screen 1: Conversation List (/api/sessions)"""
        self.client.get("/api/sessions", headers=self.headers, name="/api/sessions")

    @task(4)
    def view_trace_detail(self):
        """Screen 2: Single Session Trace Detail (/api/sessions/{id}/trace)"""
        self.client.get(f"/api/sessions/{self.session_id}/trace", headers=self.headers, name="/api/sessions/[id]/trace")

    @task(2)
    def view_session_chain(self):
        """Screen 2: Cross-Session Diagnostic Chain (/api/sessions/{id}/chain)"""
        self.client.get(f"/api/sessions/{self.session_id}/chain", headers=self.headers, name="/api/sessions/[id]/chain")

    @task(1)
    def view_benchmark_compare(self):
        """Screen 3: Benchmark/Regression Report (/api/benchmark/compare)"""
        self.client.get("/api/benchmark/compare", headers=self.headers, name="/api/benchmark/compare")
