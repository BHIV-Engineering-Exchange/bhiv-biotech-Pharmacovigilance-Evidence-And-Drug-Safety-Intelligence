"""
BHIV BiotechSystem — Live Socket HTTP Server Test
Hariom Upadhyay | Backend Architecture & Integration

Boots an actual live Uvicorn ASGI server on an ephemeral localhost port.
Executes real HTTP socket requests over TCP to prove the backend works
as an actual network daemon, beyond in-process ASGI simulation.
"""

from __future__ import annotations

import socket
import threading
import time
import requests
import pytest
import uvicorn
from integration.api_service import app


def get_free_port() -> int:
    """Bind to port 0 to get an available ephemeral port from the OS."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class UvicornServerThread(threading.Thread):
    def __init__(self, port: int):
        super().__init__(daemon=True)
        self.port = port
        self.server = None
        self.started = threading.Event()

    def run(self):
        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=self.port,
            log_level="warning",
            access_log=False,
        )
        self.server = uvicorn.Server(config)
        self.started.set()
        self.server.run()

    def stop(self):
        if self.server:
            self.server.should_exit = True


def test_live_socket_http_server():
    """Verify live HTTP server starts, serves real TCP sockets, and handles endpoints."""
    port = get_free_port()
    server_thread = UvicornServerThread(port)
    server_thread.start()
    server_thread.started.wait(timeout=5)

    base_url = f"http://127.0.0.1:{port}"
    max_retries = 10
    connected = False

    for _ in range(max_retries):
        try:
            resp = requests.get(f"{base_url}/health", timeout=1.0)
            if resp.status_code == 200:
                connected = True
                break
        except requests.ConnectionError:
            time.sleep(0.3)

    assert connected, f"Could not connect to live Uvicorn server on port {port}"

    try:
        # 1. Test live GET /health over TCP socket
        health_resp = requests.get(f"{base_url}/health", timeout=2.0)
        assert health_resp.status_code == 200
        health_data = health_resp.json()
        assert health_data["status"] == "OK"
        assert health_data["service"] == "BHIV Pharmacovigilance Backend API"
        assert health_data["integrations"]["qc_engine_shyamal"] == "VERIFIED"

        # 2. Test live POST /api/v1/qc/validate over TCP socket
        valid_payload = {
            "record": {
                "schema_version": "1.0.0",
                "evidence_id": "LIVE-SOCKET-EV-001",
                "study_id": "STUDY-SOCKET-001",
                "source": "OpenFDA/FAERS",
                "protocol_reference": "NOT_REPORTED",
                "sample_identification": "NOT_REPORTED",
                "control_identification": "NOT_REPORTED",
                "experimental_conditions": "NOT_REPORTED",
                "measurement_method": "NOT_REPORTED",
                "method_validation_status": "NOT_REPORTED",
                "raw_data_availability": "NOT_REPORTED",
                "missing_data": [],
                "deviations": [],
                "statistical_reporting": "NOT_REPORTED",
                "reproducibility": "NOT_REPORTED",
                "limitations": "NOT_REPORTED",
                "evidence_category": "Clinical",
                "synthetic_data_declaration": "SAMPLE / SYNTHETIC / FOR SOFTWARE TESTING",
                "reviewer_status": "NOT REVIEWED",
                "evidence_quality": "VERIFIED",
                "final_review_status": "READY FOR HUMAN REVIEW",
            }
        }
        qc_resp = requests.post(f"{base_url}/api/v1/qc/validate", json=valid_payload, timeout=2.0)
        assert qc_resp.status_code == 200
        qc_data = qc_resp.json()
        assert qc_data["qc_status"] == "PASS"
        assert qc_data["engine_available"] is True

        # 3. Test live POST /api/v1/patient/intake over TCP socket
        pt_payload = {
            "report_id": "LIVE-SOCKET-PT-001",
            "drug_name": "Atorvastatin",
            "patient_id": "PT-CONFIDENTIAL-888",
            "adverse_event": "Myalgia",
            "data_origin": "REAL_WORLD",
            "store_evidence": False,
        }
        pt_resp = requests.post(f"{base_url}/api/v1/patient/intake", json=pt_payload, timeout=2.0)
        assert pt_resp.status_code == 200
        pt_data = pt_resp.json()
        assert pt_data["status"] == "ACCEPTED"
        assert pt_data["pseudonymized_patient_id"].startswith("PT-")
        assert "PT-CONFIDENTIAL-888" not in pt_data["pseudonymized_patient_id"]

    finally:
        server_thread.stop()
