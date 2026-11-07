import asyncio
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from bson import ObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("JWT_SECRET", "test-jwt-secret-long-enough-for-hs256")
API_SRC = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(API_SRC))

from model.auth import JWT_SECRET
from model.database import db_manager
from routers import pedidos, productos


class FakeCollection:
    def __init__(self, documents=None):
        self.documents = {
            document["_id"]: document for document in (documents or [])
        }

    @staticmethod
    def _matches_value(value, expected):
        if not isinstance(expected, dict):
            return value == expected
        if "$exists" in expected:
            return (value is not None) == expected["$exists"]
        if "$gte" in expected:
            return value is not None and value >= expected["$gte"]
        return False

    def _matches(self, document, query):
        for key, expected in query.items():
            if key == "$or":
                if not any(self._matches(document, option) for option in expected):
                    return False
            elif not self._matches_value(document.get(key), expected):
                return False
        return True

    async def find_one(self, query):
        return next(
            (
                document
                for document in self.documents.values()
                if self._matches(document, query)
            ),
            None,
        )

    def find(self, query):
        results = [
            document
            for document in self.documents.values()
            if self._matches(document, query)
        ]

        class FakeCursor:
            async def to_list(self, length=None):
                return results[:length] if length else results

        return FakeCursor()

    async def find_one_and_update(self, query, update, return_document):
        document = await self.find_one(query)
        if document is None:
            return None
        before = document.copy()
        for key, amount in update.get("$inc", {}).items():
            document[key] = document.get(key, 0) + amount
        return document if return_document else before

    async def update_one(self, query, update):
        document = await self.find_one(query)
        if document:
            for key, amount in update.get("$inc", {}).items():
                document[key] = document.get(key, 0) + amount

    async def insert_one(self, document):
        inserted_id = ObjectId()
        self.documents[inserted_id] = {**document, "_id": inserted_id}

        class InsertResult:
            pass

        result = InsertResult()
        result.inserted_id = inserted_id
        return result


class FakeDatabase:
    def __init__(self, product):
        self.users = FakeCollection()
        self.productos = FakeCollection([product])
        self.pedidos = FakeCollection()


class CatalogAndOrderEndpointTests(unittest.TestCase):
    def setUp(self):
        self.original_db = db_manager.db
        self.product_id = ObjectId()
        self.product = {
            "_id": self.product_id,
            "nombre": "Teclado",
            "descripcion": "Teclado mecánico",
            "precio": 100,
            "unidades": 5,
            "activo": True,
            "imagen": "https://example.com/teclado.jpg",
        }
        db_manager.db = FakeDatabase(self.product.copy())
        self.customer_id = ObjectId()
        self.admin_id = ObjectId()
        db_manager.db.users.documents[self.customer_id] = {
            "_id": self.customer_id,
            "username": "cliente",
            "correo": "cliente@example.com",
            "rol": "cliente",
        }
        db_manager.db.users.documents[self.admin_id] = {
            "_id": self.admin_id,
            "username": "admin",
            "correo": "admin@example.com",
            "rol": "admin",
        }
        self.app = FastAPI()
        self.app.include_router(productos.router)
        self.app.include_router(pedidos.router)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        db_manager.db = self.original_db

    def token(self, user_id, rol="cliente"):
        return jwt.encode(
            {
                "sub": str(user_id),
                "username": rol,
                "rol": rol,
                "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
            },
            JWT_SECRET,
            algorithm="HS256",
        )

    def auth(self, user_id=None, rol="cliente"):
        return {
            "Authorization": f"Bearer {self.token(user_id or self.customer_id, rol)}"
        }

    def test_product_reads_are_public(self):
        response = self.client.get(f"/productos/{self.product_id}")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["imagen"], self.product["imagen"])

    def test_customer_order_uses_token_user_and_decreases_stock(self):
        response = self.client.post(
            "/pedidos/",
            json={
                "usuario_id": str(self.admin_id),
                "productos": [{"producto_id": str(self.product_id), "cantidad": 2}],
            },
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["usuario_id"], str(self.customer_id))
        self.assertEqual(response.json()["total"], 200)
        self.assertEqual(
            db_manager.db.productos.documents[self.product_id]["unidades"],
            3,
        )

    def test_customer_sees_only_own_orders_and_admin_sees_all(self):
        other_id = ObjectId()
        order_template = {
            "productos": [
                {
                    "producto_id": str(self.product_id),
                    "cantidad": 1,
                    "nombre": "Teclado",
                    "precio_unitario": 100,
                }
            ],
            "total": 100,
            "estado": "pendiente",
        }
        for owner_id in (self.customer_id, other_id):
            asyncio.run(
                db_manager.db.pedidos.insert_one(
                    {**order_template, "usuario_id": str(owner_id)}
                )
            )

        customer_orders = self.client.get("/pedidos/", headers=self.auth())
        admin_orders = self.client.get(
            "/pedidos/",
            headers=self.auth(self.admin_id, "admin"),
        )

        self.assertEqual(len(customer_orders.json()), 1)
        self.assertEqual(customer_orders.json()[0]["usuario_id"], str(self.customer_id))
        self.assertEqual(len(admin_orders.json()), 2)

    def test_order_requires_a_valid_login(self):
        response = self.client.post(
            "/pedidos/",
            json={
                "productos": [{"producto_id": str(self.product_id), "cantidad": 1}]
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_order_does_not_change_stock_when_quantity_exceeds_inventory(self):
        response = self.client.post(
            "/pedidos/",
            json={
                "productos": [{"producto_id": str(self.product_id), "cantidad": 6}]
            },
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            db_manager.db.productos.documents[self.product_id]["unidades"],
            5,
        )

    def test_order_updates_legacy_stock_field(self):
        db_manager.db.productos.documents[self.product_id].pop("unidades")
        db_manager.db.productos.documents[self.product_id]["stock"] = 4

        response = self.client.post(
            "/pedidos/",
            json={
                "productos": [{"producto_id": str(self.product_id), "cantidad": 1}]
            },
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            db_manager.db.productos.documents[self.product_id]["stock"],
            3,
        )


if __name__ == "__main__":
    unittest.main()
