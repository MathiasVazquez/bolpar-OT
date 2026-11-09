"""
Validación de la colección Postman `Bolpar.postman_collection.json`.

Cada test reproduce un request real de la colección (mismo método y mismo
body JSON) contra el test client de DRF, con la DB en memoria poblada con
los datos mínimos para que la operación tenga sentido. El objetivo es
confirmar que los endpoints expuestos por el backend aceptan los payloads
que el front actualmente envía.
"""
import json
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import (
    ConsumptionInput,
    Employee,
    Machine,
    MachineEmployee,
    MachineStatusLog,
    SalesOrder,
)


User = get_user_model()


@override_settings(ZOHO_WEBHOOK_URL="")  # evita disparar el webhook a Zoho
class PostmanCollectionTests(APITestCase):
    """
    Reproduce los requests de Bolpar.postman_collection.json y valida que
    el backend responda con códigos de éxito.
    """

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1", password="12345-strong", machineTurn="manana"
        )
        self.client.force_authenticate(self.user)

        # Seed básico — los IDs concretos del Postman (6, 41, 44, 111, 66)
        # no importan; validamos la forma del request, no el ID literal.
        self.so_main = SalesOrder.objects.create(
            so_number=600001, subject="OT seed principal"
        )
        self.so_for_ot_filter = SalesOrder.objects.create(
            so_number=600002, subject="OT para filtro ?ot="
        )
        Machine.objects.create(
            sales_order=self.so_for_ot_filter, nombre="M-de-OT2", numero=1
        )

        self.so_for_consumos = SalesOrder.objects.create(
            so_number=600041, subject="OT consumos"
        )
        self.so_for_get = SalesOrder.objects.create(
            so_number=600044, subject="OT get/update"
        )

        self.machine_target = Machine.objects.create(
            sales_order=self.so_main, nombre="IMP-target", numero=111
        )

        self.employee_target = Employee.objects.create(
            zoho_id="zh-66", name="Operario 66"
        )

    # ── 1. Machine & StatusLog API ──────────────────────────────────────────
    def test_postman_01_crear_maquina_con_estados(self):
        body = {
            "sales_order": self.so_main.id,
            "nombre": "IMP",
            "numero": 1,
            "data_json": {},
            "status_logs": [
                {"estado": "Iniciar Producción", "fecha_hora": "2025-06-30T21:13:00", "motivo": ""},
                {"estado": "E2", "fecha_hora": "2025-07-01T21:13:00", "motivo": ""},
                {"estado": "E3", "fecha_hora": "2025-07-02T21:13:00", "motivo": ""},
            ],
        }
        resp = self.client.post(
            "/api/inventario/machines/", body, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        machine = Machine.objects.get(id=resp.data["id"])
        self.assertEqual(machine.nombre, "IMP")
        # Los 3 status logs anidados se persistieron
        self.assertEqual(machine.status_logs.count(), 3)

    def test_postman_02_obtener_todas_las_maquinas_filtro_ot(self):
        resp = self.client.get(f"/api/inventario/machines/?ot={self.so_for_ot_filter.id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["sales_order"], self.so_for_ot_filter.id)

    def test_postman_03_obtener_todas_las_maquinas_sin_filtro(self):
        resp = self.client.get("/api/inventario/machines/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_postman_04_crear_estado_de_maquina(self):
        # ⚠ La URL en Postman es `localhost:8000/machine-status-logs` (sin
        # prefijo /api/inventario/ y sin trailing slash). La URL correcta
        # del backend es /api/inventario/machine-status-logs/. Validamos
        # contra la URL correcta.
        body = {
            "machine": self.machine_target.id,
            "estado": "E4",
            "fecha_hora": "2025-07-03T21:13:00",
            "motivo": "Falla menor",
        }
        resp = self.client.post(
            "/api/inventario/machine-status-logs/", body, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(MachineStatusLog.objects.filter(estado="E4").exists())

    def test_postman_04b_url_postman_original_devuelve_404(self):
        # Confirma que la URL como está en Postman (sin prefijo) no resuelve.
        resp = self.client.post(
            "/machine-status-logs", {"machine": 1, "estado": "x"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_postman_05_actualizar_maquina_patch(self):
        body = {"nombre": "IMP Actualizada", "numero": 2}
        resp = self.client.patch(
            f"/api/inventario/machines/{self.machine_target.id}/", body, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.machine_target.refresh_from_db()
        self.assertEqual(self.machine_target.nombre, "IMP Actualizada")
        self.assertEqual(self.machine_target.numero, 2)

    def test_postman_06_eliminar_status_log(self):
        log = MachineStatusLog.objects.create(
            machine=self.machine_target,
            estado="x",
            fecha_hora="2025-07-03T21:13:00Z",
        )
        # URL correcta (la de Postman tiene mismas inconsistencias que el #4)
        resp = self.client.delete(f"/api/inventario/machine-status-logs/{log.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

    # ── 2. crear ot ─────────────────────────────────────────────────────────
    def test_postman_07_crear_ot_payload_completo(self):
        body = {
            "so_number": 3001,
            "subject": "Orden desde Postman",
            "ajuste": "12.50",
            "ancho_util": "5.00",
            "cantidad_kilogramos": "100.00",
            "cantidad_metros": "50.00",
            "cilindro": "0.00",
            "shipping_city": "Asunción",
            "billing_city": "Asunción",
            "sales_commission": "2.00",
            "created_by": "tester",
            "shipping_code": "SC-3001",
            "billing_code": "BC-3001",
            "description": "Creada vía Postman",
            "discount": "0.00",
            "distancia_tacas": "10.00",
            "shipping_street": "Calle 1",
            "billing_street": "Calle 2",
            "status": "pendiente",
            "shipping_state": "Central",
            "billing_state": "Central",
            "tag": "Test",
            "due_date": "2025-07-01",
            "fondo_util": "0.00",
            "fuerte_util": "0.00",
            "tax": "0.00",
            "excise_duty": "0.00",
            "largo_util": "0.00",
            "modified_by": "tester",
            "currency": "PYG",
            "customer_no": "CUST-3001",
            "account_name": "Empresa Test",
            "deal_name": "Deal Test",
            "contact_name": "Contacto Test",
            "quote_name": "Quote Test",
            "purchase_order": "PO-3001",
            "shipping_country": "Paraguay",
            "billing_country": "Paraguay",
            "pending": "",
            "owner": "tester",
            "exchange_rate": "1.0000",
            "terms_and_conditions": "T&C Test",
            "items": [
                {
                    "quantity": "10.00",
                    "created_by": "tester",
                    "description": "Item 1",
                    "discount": "0.00",
                    "estado_op": "activo",
                    "tax": "0.00",
                    "product_name": "Producto 1",
                    "list_price": "100.00",
                }
            ],
            "planificacion_produccion": [
                {
                    "cant": "5.00",
                    "created_by": "tester",
                    "fecha": "2025-06-21T17:00:00Z",
                    "linea": "linea1",
                    "linea_new": "Línea A",
                    "observacion": "Plan 1",
                    "producto": "Producto 1",
                }
            ],
            "consumo_insumos": [
                {
                    "cantidad": "2.00",
                    "created_by": "tester",
                    "insumo": "Insumo 1",
                    "linea": "Linea A",
                    "lote": "L001",
                    "unidad": "kg",
                }
            ],
        }
        resp = self.client.post("/api/inventario/orders/", body, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        order = SalesOrder.objects.get(so_number=3001)
        self.assertEqual(order.items.count(), 1)
        self.assertEqual(order.planificacion_produccion.count(), 1)
        self.assertEqual(order.consumo_insumos.count(), 1)
        # Totales recalculados: 10 * 100 - 0 = 1000
        self.assertEqual(order.sub_total, Decimal("1000.00"))
        self.assertEqual(order.grand_total, Decimal("1000.00"))

    # ── 3. get ot ───────────────────────────────────────────────────────────
    def test_postman_08_get_ot_sin_trailing_slash_redirige(self):
        # En Postman el URL es `/api/inventario/orders/44` (sin slash).
        # Django con APPEND_SLASH=True redirige (301) a `/44/`.
        url_no_slash = f"/api/inventario/orders/{self.so_for_get.id}"
        resp = self.client.get(url_no_slash)
        self.assertIn(resp.status_code, (301, 302))

        resp = self.client.get(url_no_slash, follow=True)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["id"], self.so_for_get.id)

    def test_postman_08b_get_ot_con_trailing_slash(self):
        resp = self.client.get(f"/api/inventario/orders/{self.so_for_get.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["so_number"], 600044)

    # ── 4. update ot ────────────────────────────────────────────────────────
    def test_postman_09_update_ot_parcial(self):
        body = {"subject": "Orden actualizada Postman", "ajuste": "20.00"}
        resp = self.client.put(
            f"/api/inventario/orders/{self.so_for_get.id}/", body, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.so_for_get.refresh_from_db()
        self.assertEqual(self.so_for_get.subject, "Orden actualizada Postman")
        self.assertEqual(self.so_for_get.ajuste, Decimal("20.00"))

    # ── 5. obtain token JWT ─────────────────────────────────────────────────
    def test_postman_10_obtain_token_jwt(self):
        # Sin auth previa
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            "/api/token/obtain/",
            {"username": "user1", "password": "12345-strong"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)

    def test_postman_10b_obtain_token_credenciales_postman_originales(self):
        # En Postman el body es {"username":"user1","password":"12345"}.
        # Con la password de seed de este test sería 401 (la real es
        # "12345-strong"), pero confirmamos que el endpoint responde 401
        # ante credenciales inválidas.
        self.client.force_authenticate(user=None)
        resp = self.client.post(
            "/api/token/obtain/",
            {"username": "user1", "password": "12345"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ── 6. set-employees ───────────────────────────────────────────────────
    def test_postman_11_set_employees_replace(self):
        body = {
            "employee_ids": [self.employee_target.id],
            "mode": "replace",
            "assigned_by": "lmeza",
        }
        resp = self.client.post(
            f"/api/inventario/machines/{self.machine_target.id}/set-employees/",
            body,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data["created"], 1)
        self.assertEqual(resp.data["current_count"], 1)
        self.assertTrue(
            MachineEmployee.objects.filter(
                machine=self.machine_target,
                employee=self.employee_target,
                is_active=True,
            ).exists()
        )

    # ── 7. consumos/real/bulk ──────────────────────────────────────────────
    def test_postman_12_consumption_inputs_bulk(self):
        body = {
            "replace": True,
            "created_by": "lmeza",
            "items": [
                {
                    "insumo": "Hilo 40",
                    "cantidad": 12.5,
                    "unidad": "kg",
                    "linea": "linea1",
                    "lote": "L-001",
                },
                {
                    "insumo": "Tela X",
                    "cantidad": 300,
                    "unidad": "m",
                    "linea": "linea2",
                },
            ],
        }
        resp = self.client.post(
            f"/api/inventario/orders/{self.so_for_consumos.id}/consumos/real/bulk/",
            body,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.content)
        self.assertEqual(resp.data, {"saved": 2, "total_for_order": 2})
        self.assertEqual(
            ConsumptionInput.objects.filter(order=self.so_for_consumos).count(), 2
        )

    # ── 8. user (registro) ─────────────────────────────────────────────────
    def test_postman_13_user_create(self):
        self.client.force_authenticate(user=None)
        body = {
            "email": "test1@test.com",
            "username": "admin1",
            "password": "8n*5F$3q#C",
        }
        resp = self.client.post("/api/user/create/", body, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.content)
        self.assertTrue(User.objects.filter(username="admin1").exists())
