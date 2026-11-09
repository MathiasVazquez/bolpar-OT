from datetime import datetime, date

from django.utils.dateparse import parse_datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

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
from .serializers import (
    ConsumptionInputSerializer,
    EmployeeSerializer,
    MachineAssignedEmployeeSerializer,
    MachineSerializer,
    MachineSnapshotSerializer,
    MachineStatusLogSerializer,
    OrderedItemSerializer,
    PlanningProductionSerializer,
    SalesOrderSerializer,
)


class SalesOrderViewSet(viewsets.ModelViewSet):
    queryset = SalesOrder.objects.all()
    serializer_class = SalesOrderSerializer

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    @action(detail=True, methods=["post"], url_path="consumos/real/bulk")
    def save_consumos_real(self, request, pk=None):
        """
        POST /orders/{id}/consumos/real/bulk
        Body:
        {
          "replace": true|false,   // opcional (default false)
          "items": [
            {"insumo":"Hilo 40","cantidad":12.5,"unidad":"kg","linea":"linea1","lote":"L-001"},
            {"insumo":"Tela X","cantidad":300,"unidad":"m","linea":"linea2"}
          ],
          "created_by": "usuario opcional"
        }
        """
        order = self.get_object()
        payload = request.data or {}
        items = payload.get("items") or []
        replace = bool(payload.get("replace", False))
        created_by = payload.get("created_by")

        if not isinstance(items, list) or not items:
            return Response({"detail":"Debe enviar 'items' como lista no vacía."}, status=400)

        if replace:
            ConsumptionInput.objects.filter(order=order).delete()

        objs = []
        for it in items:
            objs.append(ConsumptionInput(
                order=order,
                insumo=it.get("insumo"),
                cantidad=it.get("cantidad"),
                unidad=it.get("unidad"),
                linea=it.get("linea"),
                lote=it.get("lote"),
                created_by=created_by,
            ))
        ConsumptionInput.objects.bulk_create(objs)

        total = ConsumptionInput.objects.filter(order=order).count()
        return Response({"saved": len(objs), "total_for_order": total}, status=200)



class OrderedItemViewSet(viewsets.ModelViewSet):
    queryset = OrderedItem.objects.all()
    serializer_class = OrderedItemSerializer


class PlanningProductionViewSet(viewsets.ModelViewSet):
    queryset = PlanningProduction.objects.all()
    serializer_class = PlanningProductionSerializer


class ConsumptionInputViewSet(viewsets.ModelViewSet):
    queryset = ConsumptionInput.objects.all()
    serializer_class = ConsumptionInputSerializer

class MachineViewSet(viewsets.ModelViewSet):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer

    def get_queryset(self):
        qs = Machine.objects.all()
        ot = self.request.query_params.get('ot')
        if ot is not None:
            qs = qs.filter(sales_order__pk=ot)
        return qs
    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)
    
    @action(detail=True, methods=["get"], url_path="employees")
    def list_employees(self, request, pk=None):
        """GET /machines/{id}/employees/ — lista los funcionarios activos asignados a la máquina."""
        machine = self.get_object()
        qs = Employee.objects.filter(machines_link__machine=machine, machines_link__is_active=True)
        data = MachineAssignedEmployeeSerializer(qs, many=True).data
        return Response({"count": len(data), "results": data})

    @action(detail=True, methods=["post"], url_path="set-employees")
    def set_employees(self, request, pk=None):
        """
        POST /machines/{id}/set-employees/
        Body:
        {
          "employee_ids": [1,2,3],      // IDs internos de Employee
          "mode": "replace" | "append", // por defecto: replace
          "assigned_by": "usuario opcional"
        }
        - replace: desactiva las asignaciones activas y crea las nuevas
        - append: agrega nuevas sin tocar las existentes
        """
        machine = self.get_object()
        ids = request.data.get("employee_ids", [])
        mode = (request.data.get("mode") or "replace").lower()
        assigned_by = request.data.get("assigned_by")

        if ids is None:
            ids = []

        if not isinstance(ids, list):
            return Response({"detail":"Debe enviar 'employee_ids' como lista."}, status=400)

        if mode not in {"replace", "append"}:
            return Response({"detail":"mode debe ser 'replace' o 'append'."}, status=400)

        # Una lista vacía es válida en modo replace: se usa para cerrar un turno
        # y dejar la máquina sin funcionarios activos hasta el siguiente turno.
        if not ids and mode == "append":
            return Response({"detail":"En modo append debe enviar al menos un employee_id."}, status=400)

        # Validar existencia de empleados
        employees = list(Employee.objects.filter(id__in=ids))
        found_ids = {e.id for e in employees}
        not_found = [i for i in ids if i not in found_ids]
        if not_found:
            return Response({"detail":"IDs no encontrados","not_found":not_found}, status=400)

        created, deactivated = 0, 0
        if mode == "replace":
            # desactivar actuales
            deactivated = MachineEmployee.objects.filter(machine=machine, is_active=True).update(is_active=False)
        # append o replace → crear faltantes activos
        existing_active = set(MachineEmployee.objects.filter(machine=machine, is_active=True).values_list("employee_id", flat=True))
        to_create = [MachineEmployee(machine=machine, employee=e, assigned_by=assigned_by)
                     for e in employees if e.id not in existing_active]
        if to_create:
            MachineEmployee.objects.bulk_create(to_create)
            created = len(to_create)

        # Respuesta
        current = Employee.objects.filter(machines_link__machine=machine, machines_link__is_active=True)
        return Response({
            "mode": mode,
            "created": created,
            "deactivated": deactivated,
            "current_count": current.count(),
            "current": MachineAssignedEmployeeSerializer(current, many=True).data
        }, status=200)

    @action(detail=True, methods=["get"], url_path="snapshots")
    def list_snapshots(self, request, pk=None):
        """GET /machines/{id}/snapshots/ -> historial de data_json."""
        machine = self.get_object()
        qs = machine.snapshots.all()
        serializer = MachineSnapshotSerializer(qs, many=True)
        return Response({"count": len(serializer.data), "results": serializer.data}, status=200)

    @action(detail=True, methods=["post"], url_path="finalize")
    def finalize(self, request, pk=None):
        """
        POST /machines/{id}/finalize/ crea un snapshot histórico del data_json actual.
        Body opcional:
        {
            "data_json": {...},            # si no se envía, usa machine.data_json
            "captured_by": "usuario",
            "notes": "texto",
            "reset_machine": true|false,   # si true, data_json de la máquina se limpia o se reemplaza
            "next_data_json": {...}        # sólo se usa si reset_machine es true
        }
        """
        machine = self.get_object()
        payload = request.data or {}
        data_json = payload.get("data_json", machine.data_json)

        if data_json is None:
            return Response({"detail": "La máquina no tiene data_json para guardar en el snapshot."}, status=400)

        snapshot = MachineSnapshot.objects.create(
            machine=machine,
            data_json=data_json,
            captured_by=payload.get("captured_by"),
            notes=payload.get("notes")
        )

        reset_current = payload.get("reset_machine")
        if isinstance(reset_current, str):
            reset_current = reset_current.lower() in ("true", "1", "yes", "si", "on")
        reset_current = bool(reset_current)

        if reset_current:
            machine.data_json = payload.get("next_data_json")
            machine.save(update_fields=["data_json"])

        return Response(MachineSnapshotSerializer(snapshot).data, status=201)

class MachineStatusLogViewSet(viewsets.ModelViewSet):
    queryset = MachineStatusLog.objects.all()
    serializer_class = MachineStatusLogSerializer

    def update(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)


def _get(d, *keys, default=None):
    # acceso seguro a claves con caracteres raros (N_mero_de_Documento, etc.)
    for k in keys:
        if k in d:
            return d.get(k)
    return default

def _parse_date(value):
    if not value:
        return None
    # admite 'YYYY-MM-DD' o datetime con tz
    try:
        if isinstance(value, (datetime, date)):
            return value if isinstance(value, date) else value.date()
        if "T" in value:
            dt = parse_datetime(value)
            return dt.date() if dt else None
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None

def _parse_dt(value):
    if not value:
        return None
    try:
        if isinstance(value, datetime):
            return value
        dt = parse_datetime(value)
        return dt
    except Exception:
        return None

def map_zoho_to_employee_fields(z):
    owner = z.get("Owner") or {}
    maquina = z.get("MAQUINA") or {}

    numero_doc = _get(z, "N_mero_de_Documento", "Numero_de_Documento", "Nro_de_Documento")

    data = {
        "zoho_id":           z.get("id"),
        "name":              z.get("Name") or z.get("LastName"),
        "numero_documento":  str(numero_doc) if numero_doc is not None else None,
        "email":             z.get("Email"),
        "secondary_email":   z.get("Secondary_Email"),
        "movil":             _get(z, "M_vil", "Movil", "Mobile"),
        "fecha_nacimiento":  _parse_date(_get(z, "Fecha_de_Nacimiento", "Nacimiento")),
        "ciudad_nacimiento": _get(z, "Ciudad_de_Nacimiento", "CiudadNacimiento"),
        "estado_civil":      _get(z, "ESTADO_CIVIL", "EstadoCivil"),
        "grupo_sanguineo":   _get(z, "GRUPO_SANGUINEO", "Sanguineo"),
        "alergico_a":        _get(z, "ALERGICO_A", "Alergico"),
        "direccion":         _get(z, "DIRECCION", "Direccion"),
        "ciudad":            _get(z, "CIUDAD", "Ciudad"),
        "barrio":            _get(z, "BARRIO", "Barrio"),
        "latitud":           z.get("Latitud"),
        "longitud":          z.get("Longitud"),
        "sector":            z.get("Sector"),
        "rol":               z.get("Rol"),
        "turno":             _get(z, "TURNO", "Turno"),
        "salario":           z.get("Salario"),
        "acceso_sistema":    _get(z, "Acceso_al_Sistema", "AccesoSistema"),
        "trasladar_a":       _get(z, "TRASLADAR_A", "Trasladar"),
        "maquina_name":      maquina.get("name") if isinstance(maquina, dict) else None,
        "maquina_zoho_id":   maquina.get("id") if isinstance(maquina, dict) else None,
        "owner_id":          owner.get("id") if isinstance(owner, dict) else None,
        "owner_name":        owner.get("name") if isinstance(owner, dict) else None,
        "owner_email":       owner.get("email") if isinstance(owner, dict) else None,
        "created_time_zoho": _parse_dt(z.get("Created_Time")),
        "modified_time_zoho":_parse_dt(z.get("Modified_Time")),
        "last_activity_time":_parse_dt(z.get("Last_Activity_Time")),
        "forms_url":         z.get("FORMS_URL"),
        "actualizar":        bool(z.get("Actualizar")) if z.get("Actualizar") is not None else False,
        "raw_zoho":          z,
    }
    return data

class EmployeeViewSet(viewsets.ModelViewSet):
    queryset = Employee.objects.all().order_by("-updated_at")
    serializer_class = EmployeeSerializer

    # filtros útiles sin meter librerías nuevas:
    def get_queryset(self):
        qs = super().get_queryset()
        q_doc = self.request.query_params.get("documento")
        q_name = self.request.query_params.get("name")
        q_sector = self.request.query_params.get("sector")
        q_rol = self.request.query_params.get("rol")
        if q_doc:
            qs = qs.filter(numero_documento__icontains=q_doc)
        if q_name:
            qs = qs.filter(name__icontains=q_name)
        if q_sector:
            qs = qs.filter(sector__iexact=q_sector)
        if q_rol:
            qs = qs.filter(rol__iexact=q_rol)
        return qs

    @action(detail=False, methods=["post"], url_path="upsert-zoho")
    def upsert_zoho(self, request):
        """
        Acepta:
        - Un solo objeto Zoho (dict)
        - Una lista de objetos Zoho ([dict, dict, ...])
        Hace UPSERT por 'id' (Zoho ID).
        """
        payload = request.data
        if isinstance(payload, dict):
            payloads = [payload]
        elif isinstance(payload, list):
            payloads = payload
        else:
            return Response({"detail": "Debe enviar un objeto o una lista de objetos Zoho."},
                            status=status.HTTP_400_BAD_REQUEST)

        created, updated = 0, 0
        ids = []

        for z in payloads:
            mapped = map_zoho_to_employee_fields(z)
            if not mapped.get("zoho_id"):
                continue
            obj, was_created = Employee.objects.update_or_create(
                zoho_id=mapped["zoho_id"],
                defaults=mapped
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1
            ids.append(obj.id)

        return Response({"created": created, "updated": updated, "ids": ids}, status=status.HTTP_200_OK)
