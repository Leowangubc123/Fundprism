from uuid import uuid4


def test_compare_requires_login(client):
    response = client.get("/api/funds/compare")
    assert response.status_code == 401


def test_compare_empty_ids(client, auth_headers):
    response = client.get("/api/funds/compare", headers=auth_headers)
    assert response.status_code == 400


def test_compare_too_many_ids(client, auth_headers):
    ids = ",".join([str(uuid4()) for _ in range(6)])
    response = client.get(f"/api/funds/compare?ids={ids}", headers=auth_headers)
    assert response.status_code == 400


def test_compare_returns_funds(client, auth_headers, sample_funds):
    ids = f"{sample_funds['fund_a'].id},{sample_funds['fund_b'].id}"
    response = client.get(f"/api/funds/compare?ids={ids}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data["funds"]) == 2
    names = {f["name"] for f in data["funds"]}
    assert names == {"基金 A", "基金 B"}
    fund_a = next(f for f in data["funds"] if f["name"] == "基金 A")
    assert fund_a["nav"] == 1.11
    assert len(fund_a["nav_history"]) == 2
