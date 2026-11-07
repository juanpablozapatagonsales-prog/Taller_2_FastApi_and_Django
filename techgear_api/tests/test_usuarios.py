import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient
from passlib.context import CryptContext

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-long-enough-for-hs256")
API_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(API_SRC))

from model.auth import JWT_SECRET
from model.database import build_mongodb_url, db_manager
from routers import productos, usuarios


class FakeUsersCollection:
    def __init__(self):
        self.documents = {}

    async def find_one(self, query):
        if "_id" in query:
            return self.documents.get(query["_id"])
        key, value = next(iter(query.items()))
        return next(
            (
                user
                for user in self.documents.values()
                if user.get(key) == value
            ),
            None,
        )

    async def insert_one(self, document):
        inserted_id = ObjectId()
        self.documents[inserted_id] = {**document, "_id": inserted_id}

        class InsertResult:
            pass

        result = InsertResult()
        result.inserted_id = inserted_id
        return result


class FakeCollection:
    def __init__(self):
        self.documents = {}

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
        self.productos = FakeCollection()


class UserAuthEndpointTests(unittest.TestCase):
    def setUp(self):
        self.original_db = db_manager.db
        db_manager.db = FakeDatabase()
        self.app = FastAPI()
        self.app.include_router(usuarios.router)
        self.app.include_router(productos.router)
        self.client = TestClient(self.app)
        self.user_data = {
            "username": "camila",
            "correo": "camila@example.com",
            "password": "unaclave-larga-y-segura-2026",
        }

    def tearDown(self):
        self.client.close()
        db_manager.db = self.original_db

    def token_for(self, user_id, rol="cliente", expires=None):
        return jwt.encode(
            {
                "sub": str(user_id),
                "username": "camila",
                "rol": rol,
                "exp": expires or datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

    def test_registration_saves_bcrypt_hash_and_always_sets_client_role(self):
        response = self.client.post("/usuarios/registro", json=self.user_data)

        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertEqual(result["correo"], self.user_data["correo"])
        self.assertEqual(result["rol"], "cliente")
        self.assertNotIn("access_token", result)
        saved = db_manager.db.users.documents[ObjectId(result["id"])]
        self.assertTrue(
            CryptContext(schemes=["bcrypt"]).verify(
                self.user_data["password"],
                saved["hashed_password"],
            )
        )
        self.assertEqual(saved["rol"], "cliente")

    def test_registration_rejects_duplicate_email_with_409(self):
        self.client.post("/usuarios/registro", json=self.user_data)

        response = self.client.post("/usuarios/registro", json=self.user_data)

        self.assertEqual(response.status_code, 409)

    def test_registration_requires_eight_character_password(self):
        response = self.client.post(
            "/usuarios/registro",
            json={**self.user_data, "password": "short"},
        )

        self.assertEqual(response.status_code, 422)

    def test_login_returns_identity_and_signed_jwt(self):
        self.client.post("/usuarios/registro", json=self.user_data)

        response = self.client.post(
            "/usuarios/login",
            json={
                "correo": self.user_data["correo"],
                "password": self.user_data["password"],
            },
        )

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["token_type"], "bearer")
        self.assertEqual(result["rol"], "cliente")
        self.assertEqual(result["correo"], self.user_data["correo"])
        payload = jwt.decode(
            result["access_token"],
            JWT_SECRET,
            algorithms=["HS256"],
        )
        self.assertEqual(payload["sub"], result["id"])
        self.assertEqual(payload["username"], "camila")
        self.assertEqual(payload["rol"], "cliente")

    def test_login_with_wrong_password_returns_401_and_spanish_message(self):
        self.client.post("/usuarios/registro", json=self.user_data)

        response = self.client.post(
            "/usuarios/login",
            json={
                "correo": self.user_data["correo"],
                "password": "incorrecta",
            },
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(
            response.json()["detail"],
            "El correo o la contraseña no son correctos",
        )

    def test_me_returns_current_user_and_rejects_expired_token(self):
        user_id = ObjectId()
        db_manager.db.users.documents[user_id] = {
            "_id": user_id,
            "username": "camila",
            "correo": "camila@example.com",
            "rol": "cliente",
            "hashed_password": "not-used",
        }
        good_token = self.token_for(user_id)

        response = self.client.get(
            "/usuarios/me",
            headers={"Authorization": f"Bearer {good_token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], str(user_id))
        self.assertEqual(response.json()["rol"], "cliente")

        expired_token = self.token_for(
            user_id,
            expires=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
        expired = self.client.get(
            "/usuarios/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        self.assertEqual(expired.status_code, 401)

    def test_customer_cannot_create_product_but_admin_can(self):
        customer_id = ObjectId()
        admin_id = ObjectId()
        for user_id, rol in ((customer_id, "cliente"), (admin_id, "admin")):
            db_manager.db.users.documents[user_id] = {
                "_id": user_id,
                "username": rol,
                "correo": f"{rol}@example.com",
                "rol": rol,
            }
        payload = {
            "nombre": "Mouse",
            "descripcion": "Mouse inalámbrico",
            "precio": 25,
            "unidades": 3,
            "activo": True,
        }

        forbidden = self.client.post(
            "/productos/",
            json=payload,
            headers={"Authorization": f"Bearer {self.token_for(customer_id)}"},
        )
        created = self.client.post(
            "/productos/",
            json=payload,
            headers={
                "Authorization": f"Bearer {self.token_for(admin_id, 'admin')}"
            },
        )

        self.assertEqual(forbidden.status_code, 403)
        self.assertEqual(created.status_code, 201)

    def test_password_in_mongo_uri_takes_precedence_over_clave(self):
        uri = "mongodb+srv://test-user:uri-password@cluster.example.mongodb.net/"

        configured_uri = build_mongodb_url(uri, "different-clave")

        from urllib.parse import urlsplit

        self.assertEqual(urlsplit(configured_uri).password, "uri-password")

    def test_clave_is_used_when_mongo_uri_has_no_password(self):
        from urllib.parse import unquote, urlsplit

        uri = "mongodb+srv://test-user@cluster.example.mongodb.net/"

        configured_uri = build_mongodb_url(uri, "a password with spaces")

        self.assertEqual(
            unquote(urlsplit(configured_uri).password or ""),
            "a password with spaces",
        )
