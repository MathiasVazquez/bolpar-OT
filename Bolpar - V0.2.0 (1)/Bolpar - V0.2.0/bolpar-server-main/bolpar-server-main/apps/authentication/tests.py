from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken


User = get_user_model()


class CustomUserModelTests(APITestCase):
    def test_custom_user_extra_fields(self):
        u = User.objects.create_user(
            username="alice",
            email="alice@example.com",
            password="superSecret123",
            fav_color="azul",
            machineTurn="manana",
        )
        self.assertEqual(u.fav_color, "azul")
        self.assertEqual(u.machineTurn, "manana")
        self.assertTrue(u.check_password("superSecret123"))


class AuthEndpointsTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="bob",
            email="bob@example.com",
            password="strongPass789",
            fav_color="rojo",
            machineTurn="noche",
        )

    def test_create_user_endpoint(self):
        url = reverse("create_user")
        payload = {
            "username": "charlie",
            "email": "charlie@example.com",
            "password": "anotherStrong1",
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertTrue(User.objects.filter(username="charlie").exists())

    def test_create_user_short_password(self):
        url = reverse("create_user")
        payload = {"username": "dan", "email": "dan@e.com", "password": "123"}
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_token_obtain_includes_custom_claims(self):
        url = reverse("token_create")
        resp = self.client.post(
            url, {"username": "bob", "password": "strongPass789"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

        access = AccessToken(resp.data["access"])
        self.assertEqual(access["fav_color"], "rojo")
        self.assertEqual(access["machineTurn"], "noche")
        # simplejwt serializa user_id como string en algunas versiones
        self.assertEqual(int(access["user_id"]), self.user.id)

    def test_token_refresh(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse("token_refresh")
        resp = self.client.post(url, {"refresh": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)

    def test_hello_requires_auth(self):
        url = reverse("hello_world")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_hello_with_jwt(self):
        access = AccessToken.for_user(self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        resp = self.client.get(reverse("hello_world"))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data, {"hello": "world"})

    def test_blacklist_refresh_token(self):
        refresh = RefreshToken.for_user(self.user)
        url = reverse("blacklist")
        resp = self.client.post(url, {"refresh_token": str(refresh)}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_205_RESET_CONTENT)

        # un refresh blacklisted ya no debería emitir nuevos access
        resp2 = self.client.post(
            reverse("token_refresh"), {"refresh": str(refresh)}, format="json"
        )
        self.assertEqual(resp2.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_blacklist_invalid_token(self):
        resp = self.client.post(
            reverse("blacklist"), {"refresh_token": "no-es-un-jwt"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
