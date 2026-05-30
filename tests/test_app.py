def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "healthy"


def test_alerts_requires_auth(client):
    response = client.get("/api/alerts")
    assert response.status_code == 401

