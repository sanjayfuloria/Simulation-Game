import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from fastapi.testclient import TestClient

from api.main import app


client = TestClient(app)


def test_health():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json().get("status") == "ok"


def test_signup_and_session():
    res = client.post("/api/auth/signup", json={"email": "student@example.com", "password": "x", "role": "student"})
    assert res.status_code == 200
    data = res.json()
    token = data["token"]
    headers = {"Authorization": f"Bearer {token}"}
    session = client.get("/api/session", headers=headers)
    assert session.status_code == 200
    assert session.json()["email"] == "student@example.com"


def test_round_fetch_multi():
    res = client.post("/api/auth/signup", json={"email": "student2@example.com", "password": "x", "role": "student"})
    token = res.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}
    team = client.post("/api/teams", headers=headers, json={"name": "T1"}).json()
    r1 = client.get(f"/api/rounds/current?team_id={team['id']}&round_number=1", headers=headers)
    r2 = client.get(f"/api/rounds/current?team_id={team['id']}&round_number=2", headers=headers)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["scenario_id"] != r2.json()["scenario_id"]
