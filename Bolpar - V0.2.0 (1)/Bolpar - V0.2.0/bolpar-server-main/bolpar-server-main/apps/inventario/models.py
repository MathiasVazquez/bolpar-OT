import threading
import logging

from django.db import models
from django.db.models import JSONField
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

class SalesOrder(models.Model):
    so_number             = models.BigIntegerField("Número de SO", unique=True)
    subject               = models.CharField("Asunto", max_length=255, blank=True, null=True)
    ajuste                = models.DecimalField("Ajuste", max_digits=12, decimal_places=2, blank=True, null=True)
    ancho_util            = models.DecimalField("Ancho Útil", max_digits=12, decimal_places=2, blank=True, null=True)
    cantidad_kilogramos   = models.DecimalField("Cantidad (kg)", max_digits=12, decimal_places=2, blank=True, null=True)
    cantidad_metros       = models.DecimalField("Cantidad (m)", max_digits=12, decimal_places=2, blank=True, null=True)
    cilindro              = models.DecimalField("Cilindro", max_digits=12, decimal_places=2, blank=True, null=True)

    shipping_city         = models.CharField("Ciudad de envío", max_length=255, blank=True, null=True)
    billing_city          = models.CharField("Ciudad de facturación", max_length=255, blank=True, null=True)
    shipping_code         = models.CharField("Código de envío", max_length=100, blank=True, null=True)
    billing_code          = models.CharField("Código de facturación", max_length=100, blank=True, null=True)
    shipping_street       = models.CharField("Domicilio de envío", max_length=255, blank=True, null=True)
    billing_street        = models.CharField("Domicilio de facturación", max_length=255, blank=True, null=True)
    shipping_state        = models.CharField("Estado de envío", max_length=100, blank=True, null=True)
    billing_state         = models.CharField("Estado de facturación", max_length=100, blank=True, null=True)

    sales_commission      = models.DecimalField("Comisión de venta", max_digits=12, decimal_places=2, blank=True, null=True)
    created_by            = models.CharField("Creado por", max_length=255, blank=True, null=True)
    description           = models.TextField("Descripción", blank=True)
    discount              = models.DecimalField("Descuento", max_digits=12, decimal_places=2, blank=True, null=True)
    distancia_tacas       = models.DecimalField("Distancia Tacas", max_digits=12, decimal_places=2, blank=True, null=True)

    STATUS_CHOICES = [
        ('pendiente','Pendiente'),
        ('en_proceso','En proceso'),
        ('completado','Completado'),
    ]
    status                = models.CharField("Estado", max_length=20, choices=STATUS_CHOICES, blank=True, null=True)

    tag                   = models.CharField("Etiqueta", max_length=100, blank=True, null=True)
    due_date              = models.DateField("Fecha de vencimiento", blank=True, null=True)
    fondo_util            = models.DecimalField("Fondo Útil", max_digits=12, decimal_places=2, blank=True, null=True)
    fuerte_util           = models.DecimalField("Fuerte Útil", max_digits=12, decimal_places=2, blank=True, null=True)
    tax                   = models.DecimalField("Impuesto", max_digits=12, decimal_places=2, blank=True, null=True)
    excise_duty           = models.DecimalField("Impuesto al consumo", max_digits=12, decimal_places=2, blank=True, null=True)
    largo_util            = models.DecimalField("Largo Útil", max_digits=12, decimal_places=2, blank=True, null=True)
    modified_by           = models.CharField("Modificado por", max_length=255, blank=True, null=True)

    CURRENCY_CHOICES = [
        ('PYG','Guaraní'),
        ('USD','Dólar'),
    ]
    currency              = models.CharField("Moneda", max_length=3, choices=CURRENCY_CHOICES, blank=True, null=True)
    customer_no           = models.CharField("N.º de cliente", max_length=100, blank=True, null=True)
    account_name          = models.CharField("Nombre de Empresa", max_length=255, blank=True, null=True)
    deal_name             = models.CharField("Nombre de Oportunidad", max_length=255, blank=True, null=True)
    contact_name          = models.CharField("Nombre de Persona", max_length=255, blank=True, null=True)
    quote_name            = models.CharField("Nombre de Presupuesto", max_length=255, blank=True, null=True)
    purchase_order        = models.CharField("Orden de Compra", max_length=100, blank=True, null=True)
    shipping_country      = models.CharField("País de envío", max_length=100, blank=True, null=True)
    billing_country       = models.CharField("País de facturación", max_length=100, blank=True, null=True)
    pending               = models.CharField("Pendiente", max_length=100, blank=True, null=True)
    owner                 = models.CharField("Propietario de OT", max_length=255, blank=True, null=True)
    exchange_rate         = models.DecimalField("Tasa de cambio", max_digits=12, decimal_places=4, blank=True, null=True)

    # Campos calculados
    campo_de_agregacion_1 = models.DecimalField("Campo agregación 1", max_digits=12, decimal_places=2,
                                                 editable=False, null=True, blank=True)
    sub_total             = models.DecimalField("Subtotal", max_digits=12, decimal_places=2,
                                                 editable=False, null=True, blank=True)
    grand_total           = models.DecimalField("Total general", max_digits=12, decimal_places=2,
                                                 editable=False, null=True, blank=True)
    total1                = models.DecimalField("TOTAL1", max_digits=12, decimal_places=2,
                                                 editable=False, null=True, blank=True)
    terms_and_conditions  = models.TextField("Términos y condiciones", blank=True)

    def __str__(self):
        return f"SO {self.so_number} – {self.subject}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # recalcular totales…
        self.sub_total = sum(i.net_total or 0 for i in self.items.all())
        self.grand_total = (self.sub_total or 0) + (self.tax or 0) + (self.excise_duty or 0)
        super().save(update_fields=['sub_total', 'grand_total'])


class OrderedItem(models.Model):
    order         = models.ForeignKey(SalesOrder, related_name='items', on_delete=models.CASCADE)
    quantity      = models.DecimalField("Cantidad", max_digits=12, decimal_places=2, blank=True, null=True)
    created_by    = models.CharField("Creado por", max_length=255, blank=True, null=True)
    description   = models.TextField("Descripción", blank=True)
    discount      = models.DecimalField("Descuento", max_digits=12, decimal_places=2, blank=True, null=True)
    ESTADO_OP_CHOICES = [
        ('activo','Activo'),
        ('cerrado','Cerrado'),
    ]
    estado_op     = models.CharField("Estado OP", max_length=20, choices=ESTADO_OP_CHOICES, blank=True, null=True)
    tax           = models.DecimalField("Impuesto", max_digits=12, decimal_places=2, blank=True, null=True)
    product_name  = models.CharField("Nombre de Producto", max_length=255, blank=True, null=True)
    list_price    = models.DecimalField("Precio de lista", max_digits=12, decimal_places=2, blank=True, null=True)
    net_total     = models.DecimalField("Total", max_digits=12, decimal_places=2,
                                        editable=False, null=True, blank=True)

    def save(self, *args, **kwargs):
        self.net_total = (self.quantity or 0) * (self.list_price or 0) - (self.discount or 0)
        super().save(*args, **kwargs)


class PlanningProduction(models.Model):
    order       = models.ForeignKey(SalesOrder, related_name='planificacion_produccion', on_delete=models.CASCADE)
    cant        = models.DecimalField("CANT", max_digits=12, decimal_places=2, blank=True, null=True)
    created_by  = models.CharField("Creado por", max_length=255, blank=True, null=True)
    fecha       = models.DateTimeField("FECHA", blank=True, null=True)
    LINEA_CHOICES = [
        ('linea1','Línea 1'),
        ('linea2','Línea 2'),
    ]
    linea       = models.CharField("LINEA", max_length=50, choices=LINEA_CHOICES, blank=True, null=True)
    observacion = models.TextField("OBSERVACION", max_length=500, blank=True, null=True)
    producto    = models.CharField("PRODUCTO", max_length=255, blank=True, null=True)
    producto_medio    = models.CharField("PRODUCTO_MEDIO", max_length=255, blank=True, null=True)
    linea_new   = models.CharField("LINEA NEW", max_length=255, blank=True, null=True)

from decimal import Decimal, ROUND_HALF_UP
class ConsumptionInput(models.Model):
    order      = models.ForeignKey(SalesOrder, related_name='consumo_insumos', on_delete=models.CASCADE)
    cantidad   = models.DecimalField("CANTIDAD", max_digits=12, decimal_places=2, blank=True, null=True)
    created_by = models.CharField("Creado por", max_length=255, blank=True, null=True)
    insumo     = models.CharField("INSUMO", max_length=255, blank=True, null=True)
    linea      = models.CharField("LINEA", max_length=255, blank=True, null=True)
    lote       = models.CharField("Lote", max_length=100, blank=True, null=True)
    UNIDAD_CHOICES = [
        ('kg', 'Kilogramos'),
        ('m', 'Metros'),
    ]
    unidad     = models.CharField("UNIDAD", max_length=10, choices=UNIDAD_CHOICES, blank=True, null=True)
    def save(self, *args, **kwargs):
        if self.cantidad is not None:
            self.cantidad = (Decimal(self.cantidad)
                             .quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        super().save(*args, **kwargs)

class Machine(models.Model):
    sales_order = models.ForeignKey('SalesOrder', on_delete=models.CASCADE, related_name='machines')  # Relación con OT
    nombre       = models.CharField("Nombre de máquina", max_length=100)
    numero       = models.IntegerField("Número de máquina")
    data_json    = models.JSONField("Datos JSON", blank=True, null=True)  # Usar JSONField si Django >= 3.1

    def __str__(self):
        return f"{self.nombre} #{self.numero}"


class MachineSnapshot(models.Model):
    machine      = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='snapshots')
    data_json    = models.JSONField("Datos JSON (histórico)", blank=True, null=True)
    captured_at  = models.DateTimeField("Capturado el", auto_now_add=True)
    captured_by  = models.CharField("Capturado por", max_length=150, blank=True, null=True)
    notes        = models.TextField("Notas", blank=True, null=True)

    class Meta:
        ordering = ["-captured_at"]
        verbose_name = "Snapshot de máquina"
        verbose_name_plural = "Snapshots de máquina"

    def __str__(self):
        return f"Snapshot {self.machine} @ {self.captured_at:%d/%m/%Y %H:%M}"


class MachineStatusLog(models.Model):
    machine      = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name='status_logs')
    estado       = models.CharField("Estado", max_length=100)
    fecha_hora   = models.DateTimeField("Fecha y hora")
    motivo       = models.TextField("Motivo", blank=True, null=True)

    def __str__(self):
        return f"{self.machine} - {self.estado} - {self.fecha_hora.strftime('%d/%m/%Y %H:%M')}"


def _post_zoho_webhook(url, payload, timeout):
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        logger.info("Zoho webhook OK %s: %s", url, resp.status_code)
    except requests.RequestException as e:
        logger.error("Zoho webhook FAIL %s: %s", url, e)


@receiver(post_save, sender='inventario.MachineStatusLog')
def notify_external_api(sender, instance, created, **kwargs):
    """
    Envía un POST a Zoho cada vez que se guarda un MachineStatusLog.
    Se ejecuta en un hilo aparte para no bloquear la transacción que
    creó/actualizó el log (antes el timeout de 5s frenaba el request).
    """
    url = getattr(settings, "ZOHO_WEBHOOK_URL", None)
    if not url:
        return

    payload = {
        "machine_id": instance.machine_id,
        "estado": instance.estado,
        "fecha_hora": instance.fecha_hora.isoformat() if instance.fecha_hora else None,
        "motivo": instance.motivo or "",
        "nuevo": created,
    }
    timeout = getattr(settings, "ZOHO_WEBHOOK_TIMEOUT", 5)

    threading.Thread(
        target=_post_zoho_webhook,
        args=(url, payload, timeout),
        daemon=True,
    ).start()



class Employee(models.Model):
    # Identificadores base
    zoho_id            = models.CharField("Zoho ID", max_length=30, unique=True)
    name               = models.CharField("Nombre completo", max_length=255, blank=True, null=True)
    numero_documento   = models.CharField("Número de documento", max_length=50, blank=True, null=True, db_index=True)

    # Datos de contacto / personales
    email              = models.EmailField("Email", blank=True, null=True)
    secondary_email    = models.EmailField("Email secundario", blank=True, null=True)
    movil              = models.CharField("Móvil", max_length=50, blank=True, null=True)
    fecha_nacimiento   = models.DateField("Fecha de nacimiento", blank=True, null=True)
    ciudad_nacimiento  = models.CharField("Ciudad de nacimiento", max_length=100, blank=True, null=True)
    estado_civil       = models.CharField("Estado civil", max_length=50, blank=True, null=True)
    grupo_sanguineo    = models.CharField("Grupo sanguíneo", max_length=20, blank=True, null=True)
    alergico_a         = models.CharField("Alérgico a", max_length=255, blank=True, null=True)

    # Dirección
    direccion          = models.CharField("Dirección", max_length=255, blank=True, null=True)
    ciudad             = models.CharField("Ciudad", max_length=100, blank=True, null=True)
    barrio             = models.CharField("Barrio", max_length=100, blank=True, null=True)
    latitud            = models.CharField("Latitud", max_length=50, blank=True, null=True)
    longitud           = models.CharField("Longitud", max_length=50, blank=True, null=True)

    # Laboral
    sector             = models.CharField("Sector", max_length=100, blank=True, null=True)
    rol                = models.CharField("Rol", max_length=150, blank=True, null=True)
    turno              = models.CharField("Turno", max_length=100, blank=True, null=True)
    salario            = models.DecimalField("Salario", max_digits=14, decimal_places=2, blank=True, null=True)
    acceso_sistema     = models.CharField("Acceso al sistema", max_length=100, blank=True, null=True)
    trasladar_a        = models.CharField("Trasladar a", max_length=100, blank=True, null=True)

    # Máquina (texto + id de Zoho). No enlazo a Machine porque tu Machine depende de SalesOrder.
    maquina_name       = models.CharField("Máquina (nombre)", max_length=120, blank=True, null=True)
    maquina_zoho_id    = models.CharField("Máquina (Zoho ID)", max_length=30, blank=True, null=True)

    # Metadatos Zoho
    owner_id           = models.CharField("Owner Zoho ID", max_length=30, blank=True, null=True)
    owner_name         = models.CharField("Owner nombre", max_length=120, blank=True, null=True)
    owner_email        = models.EmailField("Owner email", blank=True, null=True)

    created_time_zoho  = models.DateTimeField("Created Time (Zoho)", blank=True, null=True)
    modified_time_zoho = models.DateTimeField("Modified Time (Zoho)", blank=True, null=True)
    last_activity_time = models.DateTimeField("Last Activity (Zoho)", blank=True, null=True)

    forms_url          = models.TextField("Forms URL", blank=True, null=True)
    actualizar         = models.BooleanField("Actualizar", default=False)

    # Raw
    raw_zoho           = JSONField("Payload Zoho", blank=True, null=True)

    # Trazas locales
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Funcionario"
        verbose_name_plural = "Funcionarios"
        indexes = [
            models.Index(fields=["zoho_id"]),
            models.Index(fields=["numero_documento"]),
        ]

    def __str__(self):
        return f"{self.name or ''} ({self.zoho_id})"

class MachineEmployee(models.Model):
    machine   = models.ForeignKey(Machine, on_delete=models.CASCADE, related_name="employees_link")
    employee  = models.ForeignKey('Employee', on_delete=models.CASCADE, related_name="machines_link")
    assigned_at = models.DateTimeField(default=timezone.now)
    assigned_by = models.CharField(max_length=150, blank=True, null=True)
    is_active   = models.BooleanField(default=True)

    class Meta:
        unique_together = ("machine", "employee", "is_active")
        verbose_name = "Funcionario asignado a máquina"
        verbose_name_plural = "Funcionarios asignados a máquina"

    def __str__(self):
        return f"{self.machine} ⇄ {self.employee} ({'activo' if self.is_active else 'inactivo'})"
