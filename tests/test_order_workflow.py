def test_allocate_order_success(client):
    product_data = {
        "sku": "ALLOCATE-1001",
        "name": "Allocate Test Product",
        "category": "Testing",
        "quantity": 100,
        "location": "Test Bin",
        "reorder_level": 10
    }

    product_response = client.post("/products", json=product_data)
    assert product_response.status_code == 201
    product_id = product_response.json()["product_id"]

    order_data = {
        "items" : 
        [
            {
            "product_id" : product_id,
             "quantity"  : 5
            }
        ]
    }   

    order_response = client.post("/orders", json=order_data)
    assert order_response.status_code == 201
    order_id = order_response.json()["order_id"]

    allocate_response = client.post(f"/orders/{order_id}/allocate")

    assert allocate_response.status_code == 200
    assert allocate_response.json()["message"] == "Order allocated successfully"
    assert allocate_response.json()["order_id"] == order_id
    assert allocate_response.json()["status"] == "allocated"

def test_allocate_order_not_enough_inventory_fails(client):
    product_data = {
        "sku": "ALLOCATE-FAIL-1001",
        "name": "Allocate Test Product",
        "category": "Testing",
        "quantity": 10,
        "location": "Test Bin",
        "reorder_level": 10
    }

    product_response = client.post("/products", json=product_data)
    assert product_response.status_code == 201
    product_id = product_response.json()["product_id"]

    order_data = {
        "items" : 
        [
            {
            "product_id" : product_id,
             "quantity"  : 50
            }
        ]
    }   

    order_response = client.post("/orders", json=order_data)
    assert order_response.status_code == 201
    order_id = order_response.json()["order_id"]

    allocate_response = client.post(f"/orders/{order_id}/allocate")

    assert allocate_response.status_code == 400
    assert allocate_response.json()["detail"] == "Not enough inventory to allocate order"

def test_pick_order_success(client):
    product_data = {
        "sku": "PICK-1001",
        "name": "Pick Test Product",
        "category": "Testing",
        "quantity": 100,
        "location": "Test Bin",
        "reorder_level": 10
    }

    product_response = client.post("/products", json=product_data)
    assert product_response.status_code == 201
    product_id = product_response.json()["product_id"]

    order_data = {
        "items" : 
        [
            {
            "product_id" : product_id,
             "quantity"  : 5
            }
        ]
    }   

    order_response = client.post("/orders", json=order_data)
    assert order_response.status_code == 201

    order_id = order_response.json()["order_id"]

    allocate_response = client.post(f"/orders/{order_id}/allocate")
    assert allocate_response.status_code == 200

    pick_response = client.post(f"/orders/{order_id}/pick")

    assert pick_response.status_code == 200
    assert pick_response.json()["message"] == "Order picked successfully"
    assert pick_response.json()["order_id"] == order_id


def test_pick_order_not_allocated(client):
    product_data = {
        "sku": "PICK-NOT-ALLOCATED-1001",
        "name": "Pick Not Allocated Test Product",
        "category": "Testing",
        "quantity": 100,
        "location": "Test Bin",
        "reorder_level": 10
    }

    product_response = client.post("/products", json=product_data)
    assert product_response.status_code == 201
    product_id = product_response.json()["product_id"]

    order_data = {
        "items" : 
        [
            {
            "product_id" : product_id,
             "quantity"  : 5
            }
        ]
    }   

    order_response = client.post("/orders", json=order_data)
    assert order_response.status_code == 201

    order_id = order_response.json()["order_id"]

    pick_response = client.post(f"/orders/{order_id}/pick")

    assert pick_response.status_code == 400
    assert pick_response.json()["detail"] == "Only orders with allocated status can be picked"
