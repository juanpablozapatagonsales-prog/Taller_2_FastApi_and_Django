import sys
import unittest
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

API_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(API_SRC))

from model.database import build_mongodb_url, db_manager
from routers import usuarios


class FakeUsersCollection:
    def __init__(self):
        self.documents = {}

    async def find_one(self, query):
        if "email" in query:
            return next(
                (
                    document
                    for document in self.documents.values()
                    if document["email"] == query["email"]
                ),
                None,
            )
        return self.documents.get(query["_id"])

    async def insert_one(self, document):
        inserted_id = ObjectId()
        self.documents[inserted_id] = {**document, "_id": inserted_id}

        class InsertResult:
            pass

        result = InsertResult()
        result.inserted_id = inserted_id
        return result


class FakeDatabase:
    def __init__(self):
        self.users = FakeUsersCollection()


class UserAuthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.original_db = db_manager.db
        db_manager.db = FakeDatabase()
        self.app = FastAPI()
        self.app.include_router(usuarios.router)
        self.client = TestClient(self.app)
        self.user_data = {
            "username": "camila",
            "email": "camila@example.com",
            "password": "unaclave-larga-y-segura-2026",
        }

    def tearDown(self):
        self.client.close()
        db_manager.db = self.original_db

    def test_registration_saves_bcrypt_hash_and_returns_jwt(self):
        response = self.client.post("/usuarios/", json=self.user_data)

        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["email"], self.user_data["email"])
        self.assertEqual(result["token_type"], "bearer")
        self.assertNotEqual(
            db_manager.db.users.documents[ObjectId(result["id"])]["hashed_password"],
            self.user_data["password"],
        )

    def test_duplicate_email_is_rejected(self):
        self.client.post("/usuarios/", json=self.user_data)

        response = self.client.post("/usuarios/", json=self.user_data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["detail"], "El correo ya está registrado")

    def test_login_verifies_password_saved_in_mongodb(self):
        self.client.post("/usuarios/", json=self.user_data)

        response = self.client.post(
            "/usuarios/login",
            json={
                "email": self.user_data["email"],
                "password": self.user_data["password"],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["email"], self.user_data["email"])
        self.assertTrue(response.json()["access_token"])

    def test_login_rejects_wrong_password(self):
        self.client.post("/usuarios/", json=self.user_data)

        response = self.client.post(
            "/usuarios/login",
            json={"email": self.user_data["email"], "password": "wrong-password"},
        )

        self.assertEqual(response.status_code, 401)

    def test_me_checks_jwt_and_reads_user_from_mongodb(self):
        created = self.client.post("/usuarios/", json=self.user_data).json()

        response = self.client.get(
            "/usuarios/me",
            headers={"Authorization": f"Bearer {created['access_token']}"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], created["id"])
        self.assertEqual(response.json()["email"], self.user_data["email"])

    def test_me_rejects_invalid_token(self):
        response = self.client.get(
            "/usuarios/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        self.assertEqual(response.status_code, 401)

    def test_password_in_mongo_uri_takes_precedence_over_clave(self):
        uri = "mongodb+srv://test-user:uri-password@cluster.example.mongodb.net/"

        configured_uri = build_mongodb_url(uri, "different-clave")

        self.assertEqual(urlsplit(configured_uri).password, "uri-password")

    def test_clave_is_used_when_mongo_uri_has_no_password(self):
        uri = "mongodb+srv://test-user@cluster.example.mongodb.net/"

        configured_uri = build_mongodb_url(uri, "a password with spaces")

        self.assertEqual(
            unquote(urlsplit(configured_uri).password or ""),
            "a password with spaces",
        )


if __name__ == "__main__":
    unittest.main()
