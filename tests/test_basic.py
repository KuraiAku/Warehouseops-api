def test_home_route(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Warehouseops API is running!"}