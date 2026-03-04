from rest_framework import status
from rest_framework.test import APITestCase

from .models import Category, Order, Product


class EcommerceApiSmokeTests(APITestCase):
    def test_register_login_create_and_cancel_order(self):
        register_response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "smokeuser",
                "email": "smoke@example.com",
                "password": "safe-password-123",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        token_response = self.client.post(
            "/api/token/",
            {"username": "smokeuser", "password": "safe-password-123"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", token_response.data)

        category = Category.objects.create(name="Books", description="Book category")
        product = Product.objects.create(
            name="Django Guide",
            description="A practical Django book",
            price="10.00",
            stock_quantity=5,
            category=category,
        )

        list_response = self.client.get("/api/products/")
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )
        create_order_response = self.client.post(
            "/api/orders/",
            {"items": [{"product": product.id, "quantity": 2}]},
            format="json",
        )
        self.assertEqual(create_order_response.status_code, status.HTTP_201_CREATED)

        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 3)

        order_id = create_order_response.data["id"]
        cancel_response = self.client.post(f"/api/orders/{order_id}/cancel/", format="json")
        self.assertEqual(cancel_response.status_code, status.HTTP_200_OK)

        product.refresh_from_db()
        self.assertEqual(product.stock_quantity, 5)
        self.assertFalse(Order.objects.filter(id=order_id).exists())


class OrderBusinessRulesTests(APITestCase):
    def setUp(self):
        register_response = self.client.post(
            "/api/accounts/register/",
            {
                "username": "orders-user",
                "email": "orders@example.com",
                "password": "safe-password-123",
            },
            format="json",
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)

        token_response = self.client.post(
            "/api/token/",
            {"username": "orders-user", "password": "safe-password-123"},
            format="json",
        )
        self.assertEqual(token_response.status_code, status.HTTP_200_OK)

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {token_response.data['access']}"
        )

        category = Category.objects.create(name="Devices", description="Device category")
        self.product = Product.objects.create(
            name="Phone",
            description="A smartphone",
            price="100.00",
            stock_quantity=5,
            category=category,
        )

    def test_zero_quantity_order_is_rejected(self):
        response = self.client.post(
            "/api/orders/",
            {"items": [{"product": self.product.id, "quantity": 0}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Order.objects.count(), 0)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)

    def test_order_cannot_be_created_as_completed(self):
        response = self.client.post(
            "/api/orders/",
            {"is_completed": True, "items": [{"product": self.product.id, "quantity": 1}]},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["is_completed"])

    def test_delete_order_restores_stock(self):
        create_response = self.client.post(
            "/api/orders/",
            {"items": [{"product": self.product.id, "quantity": 2}]},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 3)

        order_id = create_response.data["id"]
        delete_response = self.client.delete(f"/api/orders/{order_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_200_OK)

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 5)
        self.assertFalse(Order.objects.filter(id=order_id).exists())

    def test_delete_completed_order_is_blocked(self):
        create_response = self.client.post(
            "/api/orders/",
            {"items": [{"product": self.product.id, "quantity": 1}]},
            format="json",
        )
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        order_id = create_response.data["id"]

        complete_response = self.client.post(f"/api/orders/{order_id}/complete/", format="json")
        self.assertEqual(complete_response.status_code, status.HTTP_200_OK)

        delete_response = self.client.delete(f"/api/orders/{order_id}/")
        self.assertEqual(delete_response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertTrue(Order.objects.filter(id=order_id).exists())
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock_quantity, 4)
