def test_health_does_not_leak_internal_error_details(client, monkeypatch):
    from app.routes import health as health_route

    def explode():
        raise RuntimeError("Can't connect to MySQL server on 'db-prod-01:3306'")

    monkeypatch.setattr(health_route.system_queries, "ping", explode)

    response = client.get("/health/mysql")
    body = response.get_json()

    assert response.status_code == 503
    assert body == {"status": "error"}
    assert "db-prod-01" not in response.get_data(as_text=True)
