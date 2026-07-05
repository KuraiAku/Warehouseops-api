def test_get_products_returns_list(client):
    response = client.get("/products")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_product_success(client):
    product_data = {
        "sku": "TEST-1001",
        "name": "Test Product",
        "category": "Testing",
        "quantity": 50,
        "location": "Test Bin",
        "reorder_level": 10
    }

    response = client.post("/products", json=product_data)

    assert response.status_code == 201
    assert response.json()["message"] == "Product added successfully"
    assert "product_id" in response.json()

def test_duplicate_sku_fails(client):
    product_data = {
        "sku": "DUP-1001",
        "name": "Duplicate Test Product",
        "category": "Testing",
        "quantity": 50,
        "location": "Test Bin",
        "reorder_level": 10
    }

    first_response = client.post("/products", json=product_data)
    second_response = client.post("/products", json=product_data)

    assert first_response.status_code == 201
    assert second_response.status_code == 409