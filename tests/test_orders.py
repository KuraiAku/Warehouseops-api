def test_create_order_success(client):
    product_data = {
        "sku": "ORDER-1001",
        "name": "Order Test Product",
        "category": "Testing",
        "quantity": 100,
        "location": "Test Bin",
        "reorder_level": 10
    }

    product_response = client.post("/products", json=product_data)

    assert product_response.status_code == 201

    product_id = product_response.json()["product_id"]

    order_data = {
        "items": [
            {
                "product_id": product_id,
                "quantity": 5
            }
        ]
    }

    order_response = client.post("/orders", json=order_data)

    assert order_response.status_code == 201
    assert "order_id" in order_response.json()

def test_create_order_invalid_product_id(client):
    order_data = {
        "items": [
            {
                "product_id": 999999,
                "quantity": 5
            }
        ]
    }

    order_response = client.post("/orders", json=order_data)

    assert order_response.status_code == 404

    