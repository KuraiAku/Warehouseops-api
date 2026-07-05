from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_get_products_returns_list():
    response = client.get("/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)
    