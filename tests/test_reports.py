def test_get_orders_summary_with_pending_order(client):
    product_response = client.post("/products", json={
        "sku": "REPORT-TEST-001",
        "name": "Report Test Product",
        "category": "Testing",
        "quantity": 100,
        "location": "A1",
        "reorder_level": 10
    })

    assert product_response.status_code == 201
    product_id = product_response.json()["product_id"]

    order_response = client.post("/orders", json={
        "items": [
            {
                "product_id": product_id,
                "quantity": 5
            }
        ]
    })

    assert order_response.status_code == 201

    response = client.get("/reports/orders-summary")

    assert response.status_code == 200

    data = response.json()

    assert data["total_orders"] == 1
    assert data["pending_orders"] == 1
    assert data["allocated_orders"] == 0
    assert data["picked_orders"] == 0
    assert data["cancelled_orders"] == 0