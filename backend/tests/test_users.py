from app.models.user import User


def test_list_users_requires_admin(client, auth_headers):
    response = client.get("/api/admin/users", headers=auth_headers)
    assert response.status_code == 403


def test_create_user(client, admin_headers, db):
    payload = {
        "username": "sales01",
        "password": "secret123",
        "full_name": "销售一号",
        "role": "sales",
    }
    response = client.post("/api/admin/users", json=payload, headers=admin_headers)
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "sales01"
    assert data["role"] == "sales"
    assert data["is_active"] is True

    user = db.query(User).filter(User.username == "sales01").first()
    assert user is not None
    assert user.full_name == "销售一号"


def test_create_user_duplicate_username(client, admin_headers, db):
    db.add(User(username="dup", hashed_password="x", role="sales"))
    db.commit()

    response = client.post(
        "/api/admin/users",
        json={"username": "dup", "password": "secret123", "role": "sales"},
        headers=admin_headers,
    )
    assert response.status_code == 409


def test_update_user(client, admin_headers, db, admin_user):
    user = User(username="toedit", hashed_password="x", role="sales", is_active=True)
    db.add(user)
    db.commit()

    response = client.put(
        f"/api/admin/users/{user.id}",
        json={"role": "admin", "is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["is_active"] is False


def test_cannot_self_deactivate(client, admin_headers, admin_user):
    response = client.put(
        f"/api/admin/users/{admin_user.id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 400


def test_reset_password(client, admin_headers, db):
    user = User(username="resetme", hashed_password="old", role="sales")
    db.add(user)
    db.commit()

    response = client.post(
        f"/api/admin/users/{user.id}/reset-password",
        json={"password": "newpass123"},
        headers=admin_headers,
    )
    assert response.status_code == 200


def test_delete_user(client, admin_headers, db):
    user = User(username="todelete", hashed_password="x", role="sales")
    db.add(user)
    db.commit()

    response = client.delete(f"/api/admin/users/{user.id}", headers=admin_headers)
    assert response.status_code == 204
    assert db.query(User).filter(User.id == user.id).first() is None


def test_cannot_delete_self(client, admin_headers, admin_user):
    response = client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
    assert response.status_code == 400
