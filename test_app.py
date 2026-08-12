import os
import pytest
from dotenv import load_dotenv
from app import app, mongo
from bson.objectid import ObjectId

load_dotenv()

@pytest.fixture
def client():
    app.config["TESTING"] = True
    test_uri = os.getenv("TEST_MONGO_URI", "mongodb://localhost:27017/test_student_db")
    app.config["MONGO_URI"] = test_uri
    client = app.test_client()

    db_name = test_uri.rsplit('/', 1)[-1].split('?')[0] or "test_student_db"
    old_db = mongo.db
    mongo.db = mongo.cx[db_name]

    # Setup: clear and create test data
    with app.app_context():
        mongo.db.students.delete_many({})
        mongo.db.students.insert_one({
            "_id": ObjectId("66fddff25f4b5f6a0a123456"),
            "name": "Test Student",
            "email": "test@student.com",
            "course": "Flask"
        })
    yield client

    # Teardown: drop DB after test and restore original database binding
    with app.app_context():
        mongo.cx.drop_database(db_name)
        mongo.db = old_db



def test_home_page(client):
    """Test if home page loads correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b"Test Student" in response.data


def test_add_student(client):
    """Test adding a new student"""
    data = {"name": "New User", "email": "new@user.com", "course": "Python"}
    response = client.post('/add', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"New User" in response.data


def test_update_student(client):
    """Test updating a student"""
    student_id = "66fddff25f4b5f6a0a123456"
    data = {"name": "Updated Name", "email": "updated@student.com", "course": "Updated Course"}
    response = client.post(f'/update/{student_id}', data=data, follow_redirects=True)
    assert response.status_code == 200
    assert b"Updated Name" in response.data


def test_delete_student(client):
    """Test deleting a student"""
    # Add a temporary student
    with app.app_context():
        student_id = mongo.db.students.insert_one({
            "name": "Temp User",
            "email": "temp@user.com",
            "course": "Temp Course"
        }).inserted_id

    response = client.get(f'/delete/{student_id}', follow_redirects=True)
    assert response.status_code == 200
    assert b"Temp User" not in response.data


def test_health_endpoint(client):
    """Test /health endpoint returns JSON status response"""
    response = client.get('/health')
    assert response.status_code in [200, 500]
    data = response.get_json()
    assert "status" in data

