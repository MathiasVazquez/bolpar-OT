# bolpar-server

Backend Django + Django REST Framework para sincronizar **Sales Orders desde Zoho CRM** y operar como sistema de **Órdenes de Trabajo (OT)** sobre piso de planta: planificación de producción, consumo real de insumos, asignación de máquinas y funcionarios, y notificaciones de estado de máquina hacia Zoho.

El front externo consume esta API vía JWT.

## 📚 Documentación del proyecto

| Documento | Para qué |
|---|---|
| **[README.md](README.md)** (este) | Guía de uso: instalación, endpoints, payloads |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | Diseño técnico: arquitectura, modelo de datos, decisiones (ADR), capas, flujos de request |
| **[HANDOVER.md](HANDOVER.md)** | Cesión del proyecto: accesos, despliegue, runbook, backups, trampas conocidas |
| **[Bolpar.postman_collection.json](Bolpar.postman_collection.json)** | Colección Postman validada con tests |

---

## Tabla de contenidos

1. [Stack](#stack)
2. [Estructura](#estructura)
3. [Configuración](#configuración)
4. [Puesta en marcha local](#puesta-en-marcha-local)
5. [Despliegue](#despliegue)
6. [Modelo de datos](#modelo-de-datos)
7. [Autenticación](#autenticación)
8. [Endpoints REST](#endpoints-rest)
9. [Flujos clave](#flujos-clave)
10. [Webhook saliente a Zoho](#webhook-saliente-a-zoho)
11. [Admin de Django](#admin-de-django)
12. [Notas de seguridad y operación](#notas-de-seguridad-y-operación)

---

## Stack

| Componente | Versión / detalle |
|---|---|
| Lenguaje | Python (virtualenv en `myenv/`) |
| Framework | Django + Django REST Framework |
| Auth | `djangorestframework-simplejwt` (con blacklist) + `rest_framework.authtoken` |
| Filtros | `django-filter` |
| CORS | `django-cors-headers` |
| HTTP cliente saliente | `requests` |
| DB | SQLite (`db.sqlite3`) |
| Servidor prod | Gunicorn detrás de Nginx |

Dependencias (ver [requirements.txt](requirements.txt)):

```
django
djangorestframework
djangorestframework-simplejwt
django-filter
django-cors-headers
requests
```

---

## Estructura

```
bolpar-server/
├── manage.py
├── config.py                    # Secrets, hosts, CORS, URL del webhook Zoho (gitignored)
├── db.sqlite3                   # SQLite local (gitignored)
├── requirements.txt
├── api_rest/                    # Proyecto Django
│   ├── settings.py              # Settings + override de ZOHO_WEBHOOK_URL desde env
│   ├── urls.py                  # Routing raíz
│   └── wsgi.py
└── apps/
    ├── authentication/          # CustomUser + JWT con claim machineTurn
    │   ├── models.py
    │   ├── serializers.py
    │   ├── views.py
    │   ├── urls.py
    │   └── admin.py
    └── inventario/              # Núcleo del dominio
        ├── models.py            # SalesOrder, OrderedItem, PlanningProduction,
        │                        # ConsumptionInput, Machine, MachineSnapshot,
        │                        # MachineStatusLog, Employee, MachineEmployee
        ├── serializers.py
        ├── views.py             # ViewSets + acciones custom
        ├── urls.py              # DRF router
        ├── admin.py
        └── forms.py
```

---

## Configuración

### `config.py` (gitignored)

Mantiene las claves y hosts. Ejemplo mínimo:

```python
SECRET_KEY = "<random-string>"
DEBUG = True

HOSTING = "bolpar-server.probusinesspy.xyz"
NGROK_HOST = "xxxx.ngrok-free.app"

ALLOWED_HOSTS = [
    HOSTING,
    NGROK_HOST,
    ".ngrok-free.app",
    "http://localhost:9000/",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:9000",
    "https://bolpar-server.probusinesspy.xyz",
]
CORS_ALLOW_ALL_ORIGINS = True   # ⚠ revisar antes de producción
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://localhost:9000$",
    r"^https://.*\.ngrok-free\.app$",
]
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Webhook Zoho
ZOHO_WEBHOOK_URL = "https://www.zohoapis.com/crm/v7/functions/webhook_bolpar_app/actions/execute?auth_type=apikey&zapikey=..."
ZOHO_WEBHOOK_TIMEOUT = 5

# DB legado (no se usa con SQLite)
SERVER_BD = ""
USERNAME_BD = ""
PASSWORD_BD = ""
DATABASE = ""
```

### Variables de entorno (opcionales, override)

| Variable | Default | Uso |
|---|---|---|
| `ZOHO_WEBHOOK_URL` | valor de `config.py` | URL del webhook Zoho que recibe los `MachineStatusLog` |
| `ZOHO_WEBHOOK_TIMEOUT` | 5 | Timeout en segundos del POST saliente |

Si la env var existe, gana sobre `config.py` (ver [api_rest/settings.py](api_rest/settings.py)). Útil para apuntar a un mock en staging sin tocar archivos.

### Settings relevantes

- `AUTH_USER_MODEL = "authentication.CustomUser"`
- DRF: `IsAuthenticated` por defecto, autenticación dual `JWTAuthentication` + `TokenAuthentication`, filtro por defecto `DjangoFilterBackend`.
- JWT: access 19 h, refresh 20 h, rotación + blacklist activos, headers aceptados `Bearer` y `JWT`, claim de usuario `user_id`.

---

## Puesta en marcha local

```bash
# 1. Activar virtualenv
# Windows:
myenv\Scripts\activate
# Linux/Mac:
source myenv/bin/activate

# 2. Dependencias
pip install -r requirements.txt

# 3. Crear config.py local (no está en git, usar el ejemplo de arriba)

# 4. Migraciones y superusuario
python manage.py migrate
python manage.py createsuperuser

# 5. Servidor de desarrollo
python manage.py runserver 0.0.0.0:8000
```

Validaciones rápidas:

```bash
python manage.py check
python manage.py makemigrations --dry-run --check
```

---

## Despliegue

Pistas dejadas en [config.py](config.py) (Gunicorn + Nginx + Certbot + tmux):

```bash
gunicorn --timeout 120 api_rest.wsgi:application

sudo systemctl daemon-reload
sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -f
sudo systemctl restart nginx

sudo certbot --nginx -d bolpar-server.probusinesspy.xyz -d www.bolpar-server.probusinesspy.xyz
```

---

## Modelo de datos

### Diagrama de relaciones

```
SalesOrder ──┬──N OrderedItem
             ├──N PlanningProduction
             ├──N ConsumptionInput
             └──N Machine ──┬──N MachineStatusLog ──post_save──▶ Webhook Zoho (async)
                            ├──N MachineSnapshot
                            └──N MachineEmployee N──1 Employee
```

### `SalesOrder` — Orden de Venta / OT
Identificador único: `so_number` (BigInteger). Replica los campos de un Sales Order de Zoho.

| Bloque | Campos |
|---|---|
| Identificación | `so_number`, `subject`, `purchase_order`, `tag` |
| Partes | `account_name`, `deal_name`, `contact_name`, `quote_name`, `customer_no`, `created_by`, `modified_by`, `owner` |
| Direcciones envío/facturación | `shipping_*`, `billing_*` (street, city, state, country, code) |
| Producción / medidas | `ancho_util`, `largo_util`, `fondo_util`, `fuerte_util`, `cilindro`, `distancia_tacas`, `cantidad_kilogramos`, `cantidad_metros`, `ajuste` |
| Económicos | `currency` (`PYG`/`USD`), `exchange_rate`, `discount`, `tax`, `excise_duty`, `sales_commission`, `sub_total` (calc), `grand_total` (calc), `total1`, `campo_de_agregacion_1` |
| Estado | `status` ∈ `pendiente`/`en_proceso`/`completado`, `pending`, `due_date`, `terms_and_conditions`, `description` |

**Lógica de `save`**: tras guardar, recalcula
`sub_total = Σ items.net_total` y `grand_total = sub_total + tax + excise_duty`.

### `OrderedItem`
Items de la OT. FK `order → SalesOrder` (`related_name="items"`, CASCADE).
Campos: `quantity`, `list_price`, `discount`, `tax`, `product_name`, `description`, `created_by`, `estado_op` ∈ `activo`/`cerrado`.
**`net_total = quantity * list_price - discount`** (computado en `save`).

### `PlanningProduction`
Planificación de producción por OT. FK `order` (`related_name="planificacion_produccion"`).
Campos: `cant`, `fecha`, `linea` ∈ `linea1`/`linea2`, `linea_new`, `producto`, `producto_medio`, `observacion`, `created_by`.

### `ConsumptionInput`
Consumo real de insumos por OT. FK `order` (`related_name="consumo_insumos"`).
Campos: `insumo`, `cantidad` (redondeada a 2 decimales con `ROUND_HALF_UP`), `unidad` ∈ `kg`/`m`, `linea`, `lote`, `created_by`.

### `Machine`
Máquina asignada a una OT. FK `sales_order` (`related_name="machines"`).
Campos: `nombre`, `numero`, `data_json` (estado libre, p. ej. parámetros corrientes de la máquina).

### `MachineSnapshot`
Histórico inmutable de `data_json`. Se crea con la acción `POST /machines/{id}/finalize/`.
Campos: `data_json`, `captured_at` (auto), `captured_by`, `notes`. Orden default `-captured_at`.

### `MachineStatusLog`
Log de estados de máquina. FK `machine`. Campos: `estado`, `fecha_hora`, `motivo`.
Cada `save()` dispara un POST asíncrono al webhook de Zoho (ver [Webhook saliente a Zoho](#webhook-saliente-a-zoho)).

### `Employee`
Funcionario sincronizado desde Zoho. Identificador externo único: `zoho_id`.

| Bloque | Campos |
|---|---|
| Identificación | `zoho_id`, `name`, `numero_documento` |
| Contacto / personal | `email`, `secondary_email`, `movil`, `fecha_nacimiento`, `ciudad_nacimiento`, `estado_civil`, `grupo_sanguineo`, `alergico_a` |
| Dirección | `direccion`, `ciudad`, `barrio`, `latitud`, `longitud` |
| Laboral | `sector`, `rol`, `turno`, `salario`, `acceso_sistema`, `trasladar_a`, `maquina_name`, `maquina_zoho_id` |
| Owner Zoho | `owner_id`, `owner_name`, `owner_email` |
| Metadatos Zoho | `created_time_zoho`, `modified_time_zoho`, `last_activity_time`, `forms_url`, `actualizar` |
| Raw + trazas | `raw_zoho` (JSON íntegro), `created_at`, `updated_at` |

Indexes: `zoho_id`, `numero_documento`.

### `MachineEmployee`
Asignación funcionario ⇄ máquina. FKs `machine`, `employee`. Campos: `assigned_at`, `assigned_by`, `is_active`.
`unique_together = (machine, employee, is_active)` permite múltiples asignaciones históricas pero un único registro activo simultáneo por par.

### `CustomUser`
Extiende `AbstractUser` con dos campos:
- `fav_color` — campo demo, se inyecta como custom claim en el JWT.
- `machineTurn` — turno del operario (p. ej. usado para filtrar máquinas por turno).

---

## Autenticación

JWT (simplejwt) con rotación y blacklist. Los tokens incluyen claims `fav_color` y `machineTurn` además de los estándar.

| Método | Ruta | Auth | Descripción |
|---|---|---|---|
| POST | `/api/user/create/` | público | Crea usuario (`username`, `email`, `password ≥ 8`) |
| POST | `/api/token/obtain/` | público | Login → `{access, refresh}` con claims extra |
| POST | `/api/token/refresh/` | público | Renueva access (rota refresh) |
| GET | `/api/hello/` | JWT | Healthcheck autenticado |
| POST | `/api/blacklist/` | público | Logout: blacklista `refresh_token` |
| POST | `/api-token-auth/` | público | Token tradicional (DRF authtoken) |

Header esperado en endpoints protegidos:

```
Authorization: Bearer <access_token>
```

---

## Endpoints REST

Montados en `/api/inventario/` por un `DefaultRouter` de DRF (ver [apps/inventario/urls.py](apps/inventario/urls.py)). Cada `ModelViewSet` expone CRUD completo.

### Sales Orders (OT)

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/inventario/orders/` | Lista todas las OT |
| POST | `/api/inventario/orders/` | Crea OT (admite anidados `items`, `planificacion_produccion`, `consumo_insumos`) |
| GET | `/api/inventario/orders/{id}/` | Detalle |
| PUT/PATCH | `/api/inventario/orders/{id}/` | Update parcial. Si llegan anidados se **borran y recrean** (replace-on-update) |
| DELETE | `/api/inventario/orders/{id}/` | Borra |
| POST | `/api/inventario/orders/{id}/consumos/real/bulk/` | Acción custom — alta masiva de consumos reales |

`POST .../consumos/real/bulk/` body:

```json
{
  "replace": false,
  "items": [
    {"insumo": "Hilo 40", "cantidad": 12.5, "unidad": "kg", "linea": "linea1", "lote": "L-001"},
    {"insumo": "Tela X",  "cantidad": 300,  "unidad": "m",  "linea": "linea2"}
  ],
  "created_by": "operario_xx"
}
```

- `replace=true` borra los `ConsumptionInput` previos de la OT antes de insertar.
- Respuesta: `{ "saved": N, "total_for_order": M }`.

### Items de OT

`/api/inventario/items/` — CRUD plano de `OrderedItem`.
⚠ Editar items vía estos endpoints **no** dispara recálculo de totales en `SalesOrder`. Para mantener coherencia, usar `PUT /orders/{id}/` enviando los items anidados.

### Planificación / Insumos

- `/api/inventario/planificacion/` — CRUD de `PlanningProduction`.
- `/api/inventario/insumos/` — CRUD de `ConsumptionInput`.

### Machines

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/inventario/machines/` | Lista. Filtro: `?ot=<sales_order_pk>` |
| POST | `/api/inventario/machines/` | Crea (admite `status_logs` anidados) |
| GET | `/api/inventario/machines/{id}/` | Detalle (incluye `snapshots` y `status_logs`) |
| PUT/PATCH | `/api/inventario/machines/{id}/` | Update parcial |
| DELETE | `/api/inventario/machines/{id}/` | Borra |
| GET | `/api/inventario/machines/{id}/employees/` | Funcionarios activos asignados |
| POST | `/api/inventario/machines/{id}/set-employees/` | Asigna funcionarios |
| GET | `/api/inventario/machines/{id}/snapshots/` | Histórico de `data_json` |
| POST | `/api/inventario/machines/{id}/finalize/` | Crea snapshot del `data_json` actual |

`POST .../set-employees/` body:

```json
{
  "employee_ids": [1, 2, 3],
  "mode": "replace",
  "assigned_by": "supervisor_xx"
}
```

- `mode="replace"` (default): desactiva las asignaciones activas y crea las nuevas.
- `mode="append"`: agrega sin tocar las activas.
- Si algún `employee_id` no existe, responde 400 con `{ "not_found": [...] }`.
- Respuesta: `{mode, created, deactivated, current_count, current: [...]}`.

`POST .../finalize/` body (todo opcional):

```json
{
  "data_json": { "...": "..." },
  "captured_by": "operario",
  "notes": "fin de turno",
  "reset_machine": true,
  "next_data_json": { "...": "..." }
}
```

- Si no se envía `data_json`, se snapshotea `machine.data_json`.
- `reset_machine=true` reemplaza `machine.data_json` por `next_data_json` (o `null`).
- `reset_machine` acepta string truthy: `"true"`, `"1"`, `"yes"`, `"si"`, `"on"`.
- Respuesta 201 con el snapshot creado.

### Machine status logs

`/api/inventario/machine-status-logs/` — CRUD de `MachineStatusLog`. Cada `POST`/`PATCH` dispara el webhook async a Zoho.

### Funcionarios

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/inventario/funcionarios/` | Lista. Filtros: `?documento=`, `?name=`, `?sector=`, `?rol=` |
| POST | `/api/inventario/funcionarios/` | Crea funcionario manual |
| GET/PUT/PATCH/DELETE | `/api/inventario/funcionarios/{id}/` | CRUD |
| POST | `/api/inventario/funcionarios/upsert-zoho/` | **UPSERT por `zoho_id`** desde payload Zoho |

`POST .../upsert-zoho/` acepta un objeto Zoho o una lista. El mapeo (`map_zoho_to_employee_fields`) tolera variantes de claves Zoho (`N_mero_de_Documento` / `Numero_de_Documento` / `Nro_de_Documento`, `M_vil` / `Movil` / `Mobile`, etc.) y parsea fechas/datetimes.

Respuesta:

```json
{ "created": 2, "updated": 5, "ids": [12, 13, 14, 15, 16, 17, 18] }
```

---

## Flujos clave

### 1. Llegada de Sales Orders desde Zoho
Una Function de Zoho (o el front) hace `POST /api/inventario/orders/` con el payload completo de la OT (incluyendo items, planificación y consumos esperados, todos opcionales). Cuando cambia algo, `PUT/PATCH` con el set completo de anidados que se desean conservar (recordá la semántica replace-on-update).

### 2. Sincronización de funcionarios
Zoho golpea `POST /api/inventario/funcionarios/upsert-zoho/` con uno o varios registros. Upsert idempotente por `zoho_id`. El payload original queda guardado en `raw_zoho` para auditoría.

### 3. Operación de planta (front externo)
1. Login operario → `POST /api/token/obtain/` (JWT con `machineTurn`).
2. Listar máquinas de una OT → `GET /api/inventario/machines/?ot=<id>`.
3. Asignar funcionarios → `POST /api/inventario/machines/{id}/set-employees/`.
4. Cambiar estado → `POST /api/inventario/machine-status-logs/` (el webhook async notifica a Zoho).
5. Registrar consumo real → `POST /api/inventario/orders/{id}/consumos/real/bulk/`.
6. Finalizar turno / OT en máquina → `POST /api/inventario/machines/{id}/finalize/` (crea snapshot inmutable, opcionalmente resetea el `data_json`).

### 4. Recálculo de totales
- Crear/editar la OT vía `SalesOrderSerializer` mantiene totales consistentes (recrea items y guarda la orden, lo que dispara el recálculo de `sub_total` y `grand_total`).
- Editar items directamente por `/items/` deja totales desactualizados hasta el próximo `save()` de la OT.

---

## Webhook saliente a Zoho

Disparador: signal `post_save` sobre `MachineStatusLog`.

Implementación: el POST se ejecuta en un **hilo daemon** (`threading.Thread`), por lo que **no bloquea** la transacción que creó/actualizó el log (antes el timeout de 5 s frenaba cada request).

URL configurable por:
1. `settings.ZOHO_WEBHOOK_URL` (env var `ZOHO_WEBHOOK_URL` con prioridad sobre `config.py`).
2. Si no hay URL configurada, el webhook se omite silenciosamente.

Timeout configurable por `ZOHO_WEBHOOK_TIMEOUT` (default 5 s).

Payload enviado:

```json
{
  "machine_id": 42,
  "estado": "produciendo",
  "fecha_hora": "2026-04-26T10:15:00+00:00",
  "motivo": "",
  "nuevo": true
}
```

Logging: éxito y fallos van al logger `apps.inventario.models` (en lugar de `print`).

---

## Admin de Django

Disponible en `/admin/`. Highlights:

- **`SalesOrderAdmin`**: con inlines de `OrderedItem`, `PlanningProduction`, `ConsumptionInput`. Filtros por `status` y `due_date`.
- **`MachineAdmin`**: con inline `MachineStatusLog`.
- **`EmployeeAdmin`**: fieldsets organizados, render seguro de `raw_zoho` (JSON pretty-print scrollable), enlace clicable a `forms_url`, bulk actions `marcar_actualizar` / `desmarcar_actualizar`.
- **`MachineEmployeeAdmin`**: filtros por `is_active`, `assigned_at`, `assigned_by`, `machine`.
- **`CustomUserAdmin`**: incluye filtro por `machineTurn`.

---

## Notas de seguridad y operación

| Punto | Estado | Recomendación |
|---|---|---|
| `SECRET_KEY` en `config.py` | Local, ya gitignored | Mover a env var en prod |
| URL/API key Zoho | ✅ movida a `settings.ZOHO_WEBHOOK_URL`, override por env | Rotar la `zapikey` que estuvo histórica en código |
| Webhook bloqueante | ✅ ahora se dispara en hilo daemon | Para tráfico alto, considerar Celery/RQ |
| `DEBUG = True` | Sigue como default local | En prod: `DEBUG = False` y `ALLOWED_HOSTS` cerrado |
| `CORS_ALLOW_ALL_ORIGINS = True` | Activo | Cerrar a la lista de orígenes reales antes de prod |
| Tests | Vacíos (`tests.py`) | Agregar al menos smoke tests de los endpoints custom |
| Imports duplicados en `views.py` | ✅ consolidados (`Employee` ahora se importa una vez al tope) | — |
| `ConsumptionInputSerializer` duplicado | ✅ deduplicado, queda la versión con `lote` permisivo | — |
| Código comentado muerto en viewsets | ✅ removido | — |

### Validaciones automáticas

```bash
python manage.py check                       # System check
python manage.py makemigrations --dry-run --check   # No hay migraciones pendientes
```

Ambas pasan limpias tras los cambios documentados acá.
