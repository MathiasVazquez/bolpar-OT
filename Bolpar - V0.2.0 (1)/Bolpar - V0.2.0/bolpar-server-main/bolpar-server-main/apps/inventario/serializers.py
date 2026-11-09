from rest_framework import serializers
from .models import (
    SalesOrder, OrderedItem,
    PlanningProduction, ConsumptionInput, Machine, MachineStatusLog, Employee, MachineEmployee, MachineSnapshot
)

class MachineEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineEmployee
        fields = "__all__"

class MachineAssignedEmployeeSerializer(serializers.ModelSerializer):
    """Para listar los funcionarios asignados a una máquina."""
    class Meta:
        model = Employee
        fields = ("id","zoho_id","name","numero_documento","sector","rol","movil","email")

class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = "__all__"
        read_only_fields = ["created_at", "updated_at"]
        
class ConsumptionInputSerializer(serializers.ModelSerializer):
    lote = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    class Meta:
        model = ConsumptionInput
        fields = ["cantidad", "created_by", "insumo", "linea", "lote", "unidad"]

class OrderedItemSerializer(serializers.ModelSerializer):
    description = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    class Meta:
        model = OrderedItem
        fields = ["quantity", "created_by", "description", "discount", "estado_op", "tax", "product_name", "list_price"]

class PlanningProductionSerializer(serializers.ModelSerializer):
    observacion = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    linea_new = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )
    producto = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )

    class Meta:
        model = PlanningProduction
        fields = [
            "cant", "created_by", "fecha",
            "linea", "linea_new", "observacion", "producto", "producto_medio"
        ]


class SalesOrderSerializer(serializers.ModelSerializer):
    items = OrderedItemSerializer(many=True, required=False)
    planificacion_produccion = PlanningProductionSerializer(many=True, required=False)
    consumo_insumos = ConsumptionInputSerializer(many=True, required=False)
    tag = serializers.CharField(
        allow_blank=True, allow_null=True, required=False
    )

    class Meta:
        model = SalesOrder
        fields = "__all__"

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        planif_data = validated_data.pop("planificacion_produccion", [])
        consu_data = validated_data.pop("consumo_insumos", [])

        order = SalesOrder.objects.create(**validated_data)

        for it in items_data:
            OrderedItem.objects.create(order=order, **it)
        for pp in planif_data:
            PlanningProduction.objects.create(order=order, **pp)
        for ci in consu_data:
            ConsumptionInput.objects.create(order=order, **ci)

        # Re-save para que SalesOrder.save() recalcule sub_total/grand_total
        # con los items recién creados.
        if items_data:
            order.save()

        return order

    def update(self, instance, validated_data):
        # si quieres soportar PUT parcial
        items_data = validated_data.pop("items", None)
        planif_data = validated_data.pop("planificacion_produccion", None)
        consu_data = validated_data.pop("consumo_insumos", None)

        # Actualiza campos simples
        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        # (Opcional) limpiar y re-crear anidados si vienen en el payload
        if items_data is not None:
            instance.items.all().delete()
            for it in items_data:
                OrderedItem.objects.create(order=instance, **it)

        if planif_data is not None:
            instance.planificacion_produccion.all().delete()
            for pp in planif_data:
                PlanningProduction.objects.create(order=instance, **pp)

        if consu_data is not None:
            instance.consumo_insumos.all().delete()
            for ci in consu_data:
                ConsumptionInput.objects.create(order=instance, **ci)

        # Si se reemplazaron items, re-disparar save() para recalcular totales
        # con el set de items actualizado.
        if items_data is not None:
            instance.save()

        return instance

class MachineStatusLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineStatusLog
        fields = ["machine", "estado", "fecha_hora", "motivo"]
        extra_kwargs = {
            # `machine` se requiere sólo cuando el serializer se usa de forma
            # standalone (POST /machine-status-logs/). Cuando viene anidado
            # dentro de MachineSerializer.status_logs, el padre lo asigna.
            "machine": {"required": False, "allow_null": True},
        }

    def validate(self, attrs):
        if self.parent is None and not attrs.get("machine"):
            raise serializers.ValidationError(
                {"machine": "This field is required."}
            )
        return attrs


class MachineSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MachineSnapshot
        fields = ["id", "machine", "data_json", "captured_at", "captured_by", "notes"]
        read_only_fields = ["captured_at"]


class MachineSerializer(serializers.ModelSerializer):
    status_logs = MachineStatusLogSerializer(many=True, required=False)
    snapshots = MachineSnapshotSerializer(many=True, read_only=True)

    class Meta:
        model = Machine
        fields = ["id", "sales_order", "nombre", "numero", "data_json", "status_logs", "snapshots"]

    def create(self, validated_data):
        status_logs_data = validated_data.pop("status_logs", [])
        machine = Machine.objects.create(**validated_data)
        for log_data in status_logs_data:
            MachineStatusLog.objects.create(machine=machine, **log_data)
        return machine

    def update(self, instance, validated_data):
        status_logs_data = validated_data.pop("status_logs", None)

        for attr, val in validated_data.items():
            setattr(instance, attr, val)
        instance.save()

        if status_logs_data is not None:
            instance.status_logs.all().delete()
            for log_data in status_logs_data:
                MachineStatusLog.objects.create(machine=instance, **log_data)

        return instance
