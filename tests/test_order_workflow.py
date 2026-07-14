def create_test_product(client, sku="TEST-PRODUCT-1001", quantity=100):
    product_data = {
        "sku": sku,
        "name": "Test Product",
        "category": "Testing",
        "quantity": quantity,
        "location": "Test Bin",
        "reorder_level": 10
    }

    response = client.post("/products", json=product_data)

    assert response.status_code == 201

    return response.json()["product_id"]


def create_test_order(client, product_id, quantity=5):
    order_data = {
        "items": [
            {
                "product_id": product_id,
                "quantity": quantity
            }
        ]
    }

    response = client.post("/orders", json=order_data)

    assert response.status_code == 201

    return response.json()["order_id"]


def test_allocate_order_success(client):
    product_id = create_test_product(
        client,
        sku="ALLOCATE-1001",
        quantity=100
    )

    order_id = create_test_order(
        client,
        product_id=product_id,
        quantity=5
    )

    allocate_response = client.post(f"/orders/{order_id}/allocate")

    assert allocate_response.status_code == 200
    assert allocate_response.json()["message"] == "Order allocated successfully"
    assert allocate_response.json()["order_id"] == order_id
    assert allocate_response.json()["status"] == "allocated"

def test_allocate_order_not_enough_inventory_fails(client):
    product_id = create_test_product(
        client,
        sku="ALLOCATE-FAIL-1001",
        quantity=10
    )

    order_id = create_test_order(
        client,
        product_id=product_id,
        quantity=50
    )

    allocate_response = client.post(f"/orders/{order_id}/allocate")

    assert allocate_response.status_code == 400
    assert allocate_response.json()["detail"] == "Not enough inventory to allocate order"

def test_pick_order_success(client):
    product_id = create_test_product(
        client,
        sku="PICK-1001",
        quantity=100
    )

    order_id = create_test_order(
        client,
        product_id=product_id,
        quantity=5
    )

    allocate_response = client.post(f"/orders/{order_id}/allocate")
    assert allocate_response.status_code == 200

    pick_response = client.post(f"/orders/{order_id}/pick")

    assert pick_response.status_code == 200
    assert pick_response.json()["message"] == "Order picked successfully"
    assert pick_response.json()["order_id"] == order_id


def test_pick_order_not_allocated(client):
    product_id = create_test_product(
        client,
        sku="PICK-NOT-ALLOCATED-1001",
        quantity=100
    )

    order_id = create_test_order(
        client,
        product_id=product_id,
        quantity=5
    )

    pick_response = client.post(f"/orders/{order_id}/pick")

    assert pick_response.status_code == 400
    assert pick_response.json()["detail"] == "Only orders with allocated status can be picked"


def test_picked_order_cancellation_fails(client):
    product_id = create_test_product(
        client,
        sku="PICK-CANCELLED-1001",
        quantity=100
    )

    order_id = create_test_order(
        client,
        product_id=product_id,
        quantity=5
    )

    allocate_response = client.post(f"/orders/{order_id}/allocate")
    assert allocate_response.status_code == 200

    pick_response = client.post(f"/orders/{order_id}/pick")
    assert pick_response.status_code == 200

    cancellation_response = client.post(f"/orders/{order_id}/cancel")

    assert cancellation_response.status_code == 400
    assert cancellation_response.json()["detail"] == "Picked orders can not be cancelled"

