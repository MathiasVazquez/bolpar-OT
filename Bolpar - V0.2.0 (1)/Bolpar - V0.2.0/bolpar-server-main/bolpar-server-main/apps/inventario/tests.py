from datetime import datetime, timezone as dt_tz
from decimal import Decimal
from unittest.mock import patch

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
    MachineSnapshot,
    MachineStatusLog,
    OrderedItem,
    PlanningProduction,
    SalesOrder,
)


User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Modelos
# ──────────────────────────────────────────────────────────────────────────────

class OrderedItemModelTests(APITestCase):
    def test_net_total_is_calculated_on_save(self):
        order = SalesOrder.objects.create(so_number=1001, subject="OT-1")
        item = OrderedItem.objects.create(
            order=order,
            quantity=Decimal("3"),
            list_price=Decimal("100.00"),
            discount=Decimal("50.00"),
        )
        # 3 * 100 - 50 = 250
        self.assertEqual(item.net_total, Decimal("250.00"))

    def test_net_total_with_nulls(self):
        order = SalesOrder.objects.create(so_number=1002)
        item = OrderedItem.objects.create(order=order)  # todo None
        self.assertEqual(item.net_total, Decimal("0"))


class SalesOrderTotalsTests(APITestCase):
    def test_subtotal_and_grandtotal_recalculated(self):
        order = SalesOrder.objects.create(
            so_number=2001,
            subject="OT-2",
            tax=Decimal("10.00"),
            excise_duty=Decimal("5.00"),
        )
        OrderedItem.objects.create(
            order=order, quantity=Decimal("2"), list_price=Decimal("100"), discount=Decimal("0")
        )
        OrderedItem.objects.create(
            order=order, quantity=Decimal("1"), list_price=Decimal("50"), discount=Decimal("10")
        )
        # net_totals: 200 + 40 = 240
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.sub_total, Decimal("240.00"))
        # grand = 240 + 10 + 5 = 255
        self.assertEqual(order.grand_total, Decimal("255.00"))

    def test_grandtotal_handles_null_tax_fields(self):
        order = SalesOrder.objects.create(so_number=2002)
        OrderedItem.objects.create(
            order=order, quantity=Decimal("1"), list_price=Decimal("10"), discount=Decimal("0")
        )
        order.save()
        order.refresh_from_db()
        self.assertEqual(order.sub_total, Decimal("10.00"))
        self.assertEqual(order.grand_total, Decimal("10.00"))


class ConsumptionInputRoundingTests(APITestCase):
    def test_cantidad_rounded_half_up(self):
        order = SalesOrder.objects.create(so_number=3001)
        ci = ConsumptionInput.objects.create(
            order=order, insumo="Hilo", cantidad=Decimal("12.345"), unidad="kg"
        )
        # ROUND_HALF_UP: 12.345 -> 12.35
        self.assertEqual(ci.cantidad, Decimal("12.35"))

    def test_cantidad_none_passes_through(self):
        order = SalesOrder.objects.create(so_number=3002)
        ci = ConsumptionInput.objects.create(order=order, insumo="X")
        self.assertIsNone(ci.cantidad)


class MachineEmployeeUniquenessTests(APITestCase):
    def test_active_pair_must_be_unique(self):
        order = SalesOrder.objects.create(so_number=4001)
        machine = Machine.objects.create(sales_order=order, nombre="M1", numero=1)
        emp = Employee.objects.create(zoho_id="zh-1", name="Operario 1")

        MachineEmployee.objects.create(machine=machine, employee=emp, is_active=True)
        # Una segunda activa para el mismo par debe fallar (unique_together)
        from django.db import IntegrityError, transaction
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                MachineEmployee.objects.create(machine=machine, employee=emp, is_active=True)

        # Pero una inactiva sí puede coexistir con la activa
        MachineEmployee.objects.create(machine=machine, employee=emp, is_active=False)


# ──────────────────────────────────────────────────────────────────────────────
# Signal del webhook a Zoho
# ──────────────────────────────────────────────────────────────────────────────

class MachineStatusLogWebhookTests(APITestCase):
    @override_settings(ZOHO_WEBHOOK_URL="http://fake/zoho", ZOHO_WEBHOOK_TIMEOUT=1)
    @patch("apps.inventario.models.threading.Thread")
    def test_post_save_dispara_thread_con_payload(self, ThreadMock):
        order = SalesOrder.objects.create(so_number=5001)
        machine = Machine.objects.create(sales_order=order, nombre="M1", numero=1)

        log = MachineStatusLog.objects.create(
            machine=machine,
            estado="produciendo",
            fecha_hora=datetime(2026, 4, 26, 10, 0, tzinfo=dt_tz.utc),
            motivo="arranque",
        )

        self.assertTrue(ThreadMock.called)
        kwargs = ThreadMock.call_args.kwargs
        # Thread(target=_post_zoho_webhook, args=(url, payload, timeout), daemon=True)
        self.assertTrue(kwargs.get("daemon"))
        url, payload, timeout = kwargs["args"]
        self.assertEqual(url, "http://fake/zoho")
        self.assertEqual(timeout, 1)
        self.assertEqual(payload["machine_id"], machine.id)
        self.assertEqual(payload["estado"], "produciendo")
        self.assertEqual(payload["motivo"], "arranque")
        self.assertTrue(payload["nuevo"])
        self.assertIn("fecha_hora", payload)
        # Y se llamó a .start()
        ThreadMock.return_value.start.assert_called_once()

    @override_settings(ZOHO_WEBHOOK_URL="")
    @patch("apps.inventario.models.threading.Thread")
    def test_no_webhook_si_url_vacia(self, ThreadMock):
        order = SalesOrder.objects.create(so_number=5002)
        machine = Machine.objects.create(sales_order=order, nombre="M2", numero=2)
        MachineStatusLog.objects.create(
            machine=machine,
            estado="parada",
            fecha_hora=datetime(2026, 4, 26, 10, 0, tzinfo=dt_tz.utc),
        )
        ThreadMock.assert_not_called()

    @override_settings(ZOHO_WEBHOOK_URL="http://fake/zoho", ZOHO_WEBHOOK_TIMEOUT=1)
    @patch("apps.inventario.models.requests.post")
    def test_post_zoho_webhook_loguea_falla_sin_propagar(self, post_mock):
        import requests as _requests
        post_mock.side_effect = _requests.ConnectionError("nope")

        from apps.inventario.models import _post_zoho_webhook
        # No debe lanzar
        _post_zoho_webhook("http://fake/zoho", {"k": "v"}, 1)
        post_mock.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers para los tests de API
# ──────────────────────────────────────────────────────────────────────────────

class _AuthenticatedAPITestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="tester", password="p4ssword123", machineTurn="manana"
        )
        self.client.force_authenticate(self.user)


# ──────────────────────────────────────────────────────────────────────────────
# SalesOrder API
# ──────────────────────────────────────────────────────────────────────────────

class SalesOrderAPITests(_AuthenticatedAPITestCase):
    def test_create_order_with_nested(self):
        url = reverse("inventario:order-list")
        payload = {
            "so_number": 9001,
            "subject": "Nueva OT",
            "tax": "10.00",
            "excise_duty": "5.00",
            "items": [
                {"product_name": "Bolsa A", "quantity": "3", "list_price": "100.00", "discount": "0"},
                {"product_name": "Bolsa B", "quantity": "1", "list_price": "50.00", "discount": "10"},
            ],
            "planificacion_produccion": [
                {"producto": "Bolsa A", "cant": "3", "linea": "linea1"},
            ],
            "consumo_insumos": [
                {"insumo": "Hilo", "cantidad": "2.5", "unidad": "kg", "linea": "linea1"},
            ],
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        order = SalesOrder.objects.get(so_number=9001)
        self.assertEqual(order.items.count(), 2)
        self.assertEqual(order.planificacion_produccion.count(), 1)
        self.assertEqual(order.consumo_insumos.count(), 1)
        # net_totals: 300 + 40 = 340. grand: 340 + 10 + 5 = 355
        self.assertEqual(order.sub_total, Decimal("340.00"))
        self.assertEqual(order.grand_total, Decimal("355.00"))

    def test_update_replaces_nested_items(self):
        order = SalesOrder.objects.create(so_number=9002, subject="OT")
        OrderedItem.objects.create(
            order=order, product_name="viejo", quantity=Decimal("1"),
            list_price=Decimal("10"), discount=Decimal("0"),
        )
        url = reverse("inventario:order-detail", args=[order.pk])
        resp = self.client.put(
            url,
            {
                "so_number": 9002,
                "subject": "OT modificada",
                "items": [
                    {"product_name": "nuevo", "quantity": "2", "list_price": "5", "discount": "0"}
                ],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        order.refresh_from_db()
        self.assertEqual(order.subject, "OT modificada")
        names = list(order.items.values_list("product_name", flat=True))
        self.assertEqual(names, ["nuevo"])
        # Totales recalculados con el nuevo set de items: 2*5 - 0 = 10
        self.assertEqual(order.sub_total, Decimal("10.00"))
        self.assertEqual(order.grand_total, Decimal("10.00"))

    def test_consumos_real_bulk_replace(self):
        order = SalesOrder.objects.create(so_number=9003)
        ConsumptionInput.objects.create(order=order, insumo="viejo", cantidad=Decimal("1"), unidad="kg")
        url = reverse("inventario:order-save-consumos-real", args=[order.pk])
        resp = self.client.post(
            url,
            {
                "replace": True,
                "items": [
                    {"insumo": "Hilo 40", "cantidad": 12.5, "unidad": "kg", "linea": "linea1", "lote": "L-001"},
                    {"insumo": "Tela X",  "cantidad": 300,  "unidad": "m",  "linea": "linea2"},
                ],
                "created_by": "operario_xx",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data, {"saved": 2, "total_for_order": 2})
        insumos = list(ConsumptionInput.objects.filter(order=order).values_list("insumo", flat=True))
        self.assertNotIn("viejo", insumos)
        self.assertCountEqual(insumos, ["Hilo 40", "Tela X"])

    def test_consumos_real_bulk_append(self):
        order = SalesOrder.objects.create(so_number=9004)
        ConsumptionInput.objects.create(order=order, insumo="ya estaba", cantidad=Decimal("1"), unidad="kg")
        url = reverse("inventario:order-save-consumos-real", args=[order.pk])
        resp = self.client.post(
            url,
            {"items": [{"insumo": "nuevo", "cantidad": 1, "unidad": "kg"}]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total_for_order"], 2)

    def test_consumos_real_bulk_validacion_lista_vacia(self):
        order = SalesOrder.objects.create(so_number=9005)
        url = reverse("inventario:order-save-consumos-real", args=[order.pk])
        resp = self.client.post(url, {"items": []}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unauthenticated_blocked(self):
        self.client.force_authenticate(user=None)
        resp = self.client.get(reverse("inventario:order-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)


# ──────────────────────────────────────────────────────────────────────────────
# Machine API (acciones custom)
# ──────────────────────────────────────────────────────────────────────────────

class MachineAPITests(_AuthenticatedAPITestCase):
    def setUp(self):
        super().setUp()
        self.order = SalesOrder.objects.create(so_number=7001)
        self.other_order = SalesOrder.objects.create(so_number=7002)
        self.machine = Machine.objects.create(
            sales_order=self.order, nombre="M-A", numero=1, data_json={"foo": "bar"}
        )
        Machine.objects.create(sales_order=self.other_order, nombre="M-B", numero=1)

        self.emp1 = Employee.objects.create(zoho_id="z1", name="Op 1")
        self.emp2 = Employee.objects.create(zoho_id="z2", name="Op 2")
        self.emp3 = Employee.objects.create(zoho_id="z3", name="Op 3")

    def test_filter_by_ot(self):
        url = reverse("inventario:machine-list")
        resp = self.client.get(url, {"ot": self.order.pk})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # respuesta puede ser lista o dict paginado; aplanar
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        ids = [m["sales_order"] for m in data]
        self.assertEqual(set(ids), {self.order.pk})

    def test_set_employees_replace_mode(self):
        # asignación previa que debe quedar inactiva tras replace
        MachineEmployee.objects.create(machine=self.machine, employee=self.emp3, is_active=True)
        url = reverse("inventario:machine-set-employees", args=[self.machine.pk])
        resp = self.client.post(
            url,
            {
                "employee_ids": [self.emp1.id, self.emp2.id],
                "mode": "replace",
                "assigned_by": "supervisor",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["created"], 2)
        self.assertEqual(resp.data["deactivated"], 1)
        self.assertEqual(resp.data["current_count"], 2)
        active_ids = set(
            MachineEmployee.objects.filter(machine=self.machine, is_active=True)
            .values_list("employee_id", flat=True)
        )
        self.assertEqual(active_ids, {self.emp1.id, self.emp2.id})

    def test_set_employees_append_mode_no_desactiva(self):
        MachineEmployee.objects.create(machine=self.machine, employee=self.emp3, is_active=True)
        url = reverse("inventario:machine-set-employees", args=[self.machine.pk])
        resp = self.client.post(
            url,
            {"employee_ids": [self.emp1.id], "mode": "append"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["deactivated"], 0)
        self.assertEqual(resp.data["current_count"], 2)

    def test_set_employees_id_no_encontrado(self):
        url = reverse("inventario:machine-set-employees", args=[self.machine.pk])
        resp = self.client.post(
            url, {"employee_ids": [self.emp1.id, 999999]}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("not_found", resp.data)
        self.assertIn(999999, resp.data["not_found"])

    def test_set_employees_lista_vacia_replace_limpia_asignaciones(self):
        MachineEmployee.objects.create(machine=self.machine, employee=self.emp1, is_active=True)
        url = reverse("inventario:machine-set-employees", args=[self.machine.pk])
        resp = self.client.post(
            url,
            {"employee_ids": [], "mode": "replace", "assigned_by": "supervisor"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["current_count"], 0)
        self.assertEqual(
            MachineEmployee.objects.filter(machine=self.machine, is_active=True).count(),
            0,
        )

    def test_list_employees(self):
        MachineEmployee.objects.create(machine=self.machine, employee=self.emp1, is_active=True)
        MachineEmployee.objects.create(machine=self.machine, employee=self.emp2, is_active=False)
        url = reverse("inventario:machine-list-employees", args=[self.machine.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["zoho_id"], "z1")

    def test_finalize_creates_snapshot(self):
        url = reverse("inventario:machine-finalize", args=[self.machine.pk])
        resp = self.client.post(
            url,
            {"captured_by": "operario", "notes": "fin de turno"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        snap = MachineSnapshot.objects.get(machine=self.machine)
        self.assertEqual(snap.captured_by, "operario")
        self.assertEqual(snap.data_json, {"foo": "bar"})
        # No reset → la máquina conserva su data
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.data_json, {"foo": "bar"})

    def test_finalize_with_reset_machine(self):
        url = reverse("inventario:machine-finalize", args=[self.machine.pk])
        resp = self.client.post(
            url,
            {"reset_machine": True, "next_data_json": {"nuevo": 1}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.machine.refresh_from_db()
        self.assertEqual(self.machine.data_json, {"nuevo": 1})

    def test_finalize_reset_acepta_string_truthy(self):
        url = reverse("inventario:machine-finalize", args=[self.machine.pk])
        resp = self.client.post(
            url, {"reset_machine": "si"}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.machine.refresh_from_db()
        self.assertIsNone(self.machine.data_json)

    def test_finalize_sin_data_json_devuelve_400(self):
        machine_vacia = Machine.objects.create(
            sales_order=self.order, nombre="M-vacia", numero=99, data_json=None
        )
        url = reverse("inventario:machine-finalize", args=[machine_vacia.pk])
        resp = self.client.post(url, {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_snapshots(self):
        MachineSnapshot.objects.create(machine=self.machine, data_json={"v": 1})
        MachineSnapshot.objects.create(machine=self.machine, data_json={"v": 2})
        url = reverse("inventario:machine-list-snapshots", args=[self.machine.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 2)


# ──────────────────────────────────────────────────────────────────────────────
# Employee API (upsert-zoho)
# ──────────────────────────────────────────────────────────────────────────────

class EmployeeAPITests(_AuthenticatedAPITestCase):
    def test_upsert_zoho_single_object(self):
        url = reverse("inventario:employee-upsert-zoho")
        payload = {
            "id": "ZH-1",
            "Name": "Juan Pérez",
            "N_mero_de_Documento": 12345,
            "Email": "juan@e.com",
            "M_vil": "+595 9xx",
            "Sector": "Producción",
            "Rol": "Operario",
            "TURNO": "manana",
            "Owner": {"id": "OWN-1", "name": "Carlos", "email": "carlos@e.com"},
            "MAQUINA": {"id": "MZ-1", "name": "Maq Alpha"},
            "Created_Time": "2026-01-01T10:00:00+00:00",
            "Modified_Time": "2026-04-01T12:00:00+00:00",
            "Fecha_de_Nacimiento": "1990-05-12",
            "Actualizar": True,
        }
        resp = self.client.post(url, payload, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertEqual(resp.data["created"], 1)
        self.assertEqual(resp.data["updated"], 0)

        emp = Employee.objects.get(zoho_id="ZH-1")
        self.assertEqual(emp.name, "Juan Pérez")
        self.assertEqual(emp.numero_documento, "12345")
        self.assertEqual(emp.movil, "+595 9xx")
        self.assertEqual(emp.turno, "manana")
        self.assertEqual(emp.maquina_zoho_id, "MZ-1")
        self.assertEqual(emp.owner_email, "carlos@e.com")
        self.assertTrue(emp.actualizar)
        self.assertEqual(emp.fecha_nacimiento.isoformat(), "1990-05-12")

    def test_upsert_zoho_list_idempotente(self):
        url = reverse("inventario:employee-upsert-zoho")
        body = [
            {"id": "ZH-A", "Name": "A", "N_mero_de_Documento": "1"},
            {"id": "ZH-B", "Name": "B", "N_mero_de_Documento": "2"},
        ]
        r1 = self.client.post(url, body, format="json")
        self.assertEqual(r1.data["created"], 2)
        self.assertEqual(r1.data["updated"], 0)

        # mismo payload → sólo actualiza
        r2 = self.client.post(url, body, format="json")
        self.assertEqual(r2.data["created"], 0)
        self.assertEqual(r2.data["updated"], 2)

        self.assertEqual(Employee.objects.count(), 2)

    def test_upsert_zoho_payload_invalido(self):
        url = reverse("inventario:employee-upsert-zoho")
        resp = self.client.post(url, "no-soy-dict-ni-lista", format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_upsert_zoho_skip_si_no_id(self):
        url = reverse("inventario:employee-upsert-zoho")
        resp = self.client.post(url, [{"Name": "sin id"}], format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["created"], 0)
        self.assertEqual(resp.data["updated"], 0)
        self.assertEqual(Employee.objects.count(), 0)

    def test_employee_filtros(self):
        Employee.objects.create(zoho_id="z-100", name="Ana López", numero_documento="55555", sector="Producción", rol="Op")
        Employee.objects.create(zoho_id="z-101", name="Bruno Rodríguez", numero_documento="11111", sector="Logística", rol="Sup")
        url = reverse("inventario:employee-list")

        resp = self.client.get(url, {"name": "ana"})
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        zoho_ids = [e["zoho_id"] for e in data]
        self.assertEqual(zoho_ids, ["z-100"])

        resp = self.client.get(url, {"sector": "logística"})
        data = resp.data if isinstance(resp.data, list) else resp.data.get("results", resp.data)
        zoho_ids = [e["zoho_id"] for e in data]
        self.assertEqual(zoho_ids, ["z-101"])
