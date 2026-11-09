from django.contrib import admin
from .models import (
    SalesOrder,
    OrderedItem,
    PlanningProduction,
    ConsumptionInput,
    Machine,
    MachineStatusLog,Employee,
    MachineEmployee
)

# ─── SalesOrder y sus inlines ───────────────────────────────────────────────

class OrderedItemInline(admin.TabularInline):
    model = OrderedItem
    extra = 1

class PlanningProductionInline(admin.TabularInline):
    model = PlanningProduction
    extra = 1

class ConsumptionInputInline(admin.TabularInline):
    model = ConsumptionInput
    extra = 1

@admin.register(SalesOrder)
class SalesOrderAdmin(admin.ModelAdmin):
    list_display = ('so_number', 'subject', 'status', 'due_date')
    list_filter  = ('status', 'due_date')
    search_fields = ('so_number', 'subject', 'account_name', 'owner')
    inlines = [
        OrderedItemInline,
        PlanningProductionInline,
        ConsumptionInputInline,
    ]


# ─── OrderedItem ────────────────────────────────────────────────────────────

@admin.register(OrderedItem)
class OrderedItemAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'quantity', 'order', 'estado_op')
    list_filter  = ('estado_op',)
    search_fields = ('product_name', 'order__so_number')


# ─── PlanningProduction ─────────────────────────────────────────────────────

@admin.register(PlanningProduction)
class PlanningProductionAdmin(admin.ModelAdmin):
    list_display = ('producto', 'producto_medio', 'cant', 'order', 'fecha', 'linea')
    list_filter  = ('linea',)
    date_hierarchy = 'fecha'
    search_fields = ('producto', 'order__so_number')


# ─── ConsumptionInput ───────────────────────────────────────────────────────

@admin.register(ConsumptionInput)
class ConsumptionInputAdmin(admin.ModelAdmin):
    list_display = ('insumo', 'cantidad', 'order', 'linea', 'lote')
    list_filter  = ('linea',)
    search_fields = ('insumo', 'order__so_number')


# ─── Machine y su inline de logs ────────────────────────────────────────────

class MachineStatusLogInline(admin.TabularInline):
    model = MachineStatusLog
    extra = 1

@admin.register(Machine)
class MachineAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'numero', 'sales_order')
    list_filter  = ('sales_order',)
    search_fields = ('nombre', 'numero')
    inlines = [MachineStatusLogInline]


# ─── MachineStatusLog ───────────────────────────────────────────────────────

@admin.register(MachineStatusLog)
class MachineStatusLogAdmin(admin.ModelAdmin):
    list_display = ('machine', 'estado', 'fecha_hora')
    list_filter  = ('estado',)
    date_hierarchy = 'fecha_hora'
    search_fields = ('machine__nombre',)


from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from .models import (
    SalesOrder, OrderedItem, PlanningProduction, ConsumptionInput,
    Machine, MachineStatusLog, Employee  # <-- IMPORTANTE
)

# ... (todo tu admin actual arriba sin cambios) ...


# ─── Employee (Funcionarios) ────────────────────────────────────────────────

@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "numero_documento", "sector", "rol",
        "ciudad", "salario", "actualizar", "modified_time_zoho",
    )
    list_filter = (
        "sector", "rol", "ciudad", "actualizar",
        ("modified_time_zoho", admin.DateFieldListFilter),
        ("created_time_zoho", admin.DateFieldListFilter),
    )
    search_fields = (
        "name", "numero_documento", "email", "movil",
        "owner_name", "owner_email", "maquina_name",
    )
    ordering = ("-updated_at",)
    readonly_fields = (
        "zoho_id", "owner_id", "owner_name", "owner_email",
        "created_time_zoho", "modified_time_zoho", "last_activity_time",
        "forms_url_link", "raw_zoho_pretty", "created_at", "updated_at",
    )

    fieldsets = (
        ("Identificación", {
            "fields": ("zoho_id", "name", "numero_documento", "actualizar")
        }),
        ("Contacto", {
            "fields": ("email", "secondary_email", "movil")
        }),
        ("Datos personales", {
            "fields": ("fecha_nacimiento", "ciudad_nacimiento", "estado_civil", "grupo_sanguineo", "alergico_a")
        }),
        ("Dirección", {
            "fields": ("direccion", "ciudad", "barrio", "latitud", "longitud")
        }),
        ("Laboral", {
            "fields": ("sector", "rol", "turno", "salario", "acceso_sistema", "trasladar_a",
                       "maquina_name", "maquina_zoho_id")
        }),
        ("Owner Zoho", {
            "fields": ("owner_id", "owner_name", "owner_email")
        }),
        ("Metadatos Zoho", {
            "fields": ("created_time_zoho", "modified_time_zoho", "last_activity_time", "forms_url_link")
        }),
        ("Payload original", {
            "fields": ("raw_zoho_pretty",)
        }),
        ("Trazas locales", {
            "fields": ("created_at", "updated_at")
        }),
    )

    actions = ("marcar_actualizar", "desmarcar_actualizar")

    def forms_url_link(self, obj):
        if obj.forms_url:
            return format_html('<a href="{}" target="_blank">Abrir formulario</a>', obj.forms_url)
        return "-"
    forms_url_link.short_description = "Forms URL"

    def raw_zoho_pretty(self, obj):
        if not obj.raw_zoho:
            return "-"
        # Render mínimo y seguro
        import json
        try:
            pretty = json.dumps(obj.raw_zoho, ensure_ascii=False, indent=2)
        except Exception:
            pretty = str(obj.raw_zoho)
        # Caja scrollable
        return mark_safe(f'<div style="max-height:300px; overflow:auto;"><pre>{pretty}</pre></div>')
    raw_zoho_pretty.short_description = "Raw Zoho (JSON)"

    @admin.action(description="Marcar 'Actualizar' = True")
    def marcar_actualizar(self, request, queryset):
        updated = queryset.update(actualizar=True)
        self.message_user(request, f"{updated} funcionario(s) marcados para actualizar.")

    @admin.action(description="Marcar 'Actualizar' = False")
    def desmarcar_actualizar(self, request, queryset):
        updated = queryset.update(actualizar=False)
        self.message_user(request, f"{updated} funcionario(s) desmarcados.")

@admin.register(MachineEmployee)
class MachineEmployeeAdmin(admin.ModelAdmin):
    list_display = ("machine","employee","is_active","assigned_at","assigned_by")
    list_filter  = ("is_active", "assigned_at", "assigned_by", "machine")
    search_fields = ("machine__nombre","employee__name","employee__numero_documento")
    