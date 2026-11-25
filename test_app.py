"""The node answers the VillageOS pipeline envelope (docs/SERVICES.md §16.2)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app import app, host

SITE = {
    "population": 320,
    "builtFootprintHectares": 8.88,
    "productiveFootprintHectares": 8.16,
    "arrayHostHectares": 5.28,
    "rainfallMillimetresPerYear": 84.0,
    "solarResourceKwhPerM2PerYear": 2072.7,
    "coolingDegreeDaysPerYear": 3778.17,
}


@pytest.fixture
def client():
    with patch.object(host.mycelium, "register", new=AsyncMock(return_value=True)):
        with TestClient(app) as c:
            yield c


def envelope(inputs, params=None):
    return {"runId": str(uuid.uuid4()), "nodeId": str(uuid.uuid4()), "params": params or {}, "inputs": inputs}


def test_manifest_declares_ports_and_settings(client):
    body = client.get("/manifest").json()
    assert body["service"] == "ClimatePack"
    assert body["rehearses"] is True
    names = {p["portName"]: p for p in body["ports"]}
    assert names["coolingDegreeDaysPerYear"]["required"] is True
    assert names["desalinationCapacityM3PerDay"]["direction"] == "out"
    assert {s["name"] for s in body["settings"]} == {"profile", "seawaterAccess"}


def test_a_dubai_node_run_succeeds(client):
    res = client.post("/handle", json=envelope(SITE, {"profile": "uae", "seawaterAccess": True}))
    body = res.json()
    assert body["result"] == "success", body
    out = body["outputs"]
    assert out["shortfallM3PerYear"] == pytest.approx(0)
    assert out["desalinationCapacityM3PerDay"] > 0
    assert out["coolingMwhPerYear"] > 0
    assert "coolingCop" in out["unsourcedAssumptions"]


def test_a_missing_input_fails_naming_the_port(client):
    inputs = {k: v for k, v in SITE.items() if k != "rainfallMillimetresPerYear"}
    body = client.post("/handle", json=envelope(inputs)).json()
    assert body["result"] == "fail"
    assert "rainfallMillimetresPerYear" in body["error"]


def test_a_null_input_fails_rather_than_counting_as_zero(client):
    body = client.post("/handle", json=envelope({**SITE, "coolingDegreeDaysPerYear": None})).json()
    assert body["result"] == "fail"
    assert "coolingDegreeDaysPerYear" in body["error"]


def test_a_body_that_is_no_node_request_is_refused(client):
    assert client.post("/handle", json={"relationshipId": "r1"}).status_code == 400
