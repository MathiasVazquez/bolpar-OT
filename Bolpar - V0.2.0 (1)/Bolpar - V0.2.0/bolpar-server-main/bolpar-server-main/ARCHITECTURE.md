# Arquitectura técnica — bolpar-server

Documento técnico para entender **cómo está construido el sistema** y poder mantenerlo, extenderlo o cederlo.

Complementa al [README.md](README.md) (que es la guía de uso) con la vista interna: componentes, decisiones de diseño, modelo de datos, integraciones externas, despliegue y operación.

---

## 1. Visión de alto nivel

`bolpar-server` es un **monolito Django + DRF** que actúa como sistema de **Órdenes de Trabajo (OT)** sincronizadas desde **Zoho CRM**, expuesto vía API REST a un front externo y a Zoho mismo (que dispara webhooks contra el backend).

```
                                  ┌────────────────────────────────────────┐
                                  │                Zoho CRM                │
                                  │                                        │
                                  │  ┌──────────┐         ┌──────────────┐ │
                                  │  │ Sales    │         │ Funcionarios │ │
                                  │  │ Orders   │         │ (Custom)     │ │
                                  │  └─────┬────┘         └──────┬───────┘ │
                                  └────────┼─────────────────────┼─────────┘
                                           │ webhook (push)      │ webhook (push)
                                           │ POST /orders/       │ POST /funcionarios/upsert-zoho/
                                           ▼                     ▼
              ┌──────────────────────────────────────────────────────────────┐
   front ──▶  │              bolpar-server (Django + DRF)                    │
   externo    │                                                              │
   (JWT)      │   ┌────────────┐   ┌───────────┐   ┌──────────┐              │
              │   │ apps/auth  │   │ apps/inv  │   │ admin/   │              │
              │   │  (JWT)     │   │ (núcleo)  │   │ (Django) │              │
              │   └────────────┘   └─────┬─────┘   └──────────┘              │
              │                          │                                   │
              │                          ▼ post_save signal (async thread)   │
              │                       ────────────────────────────────────▶  │ Zoho
              │                       webhook MachineStatusLog                │ webhook
              │                                                              │ inbound
              │   ┌───────────────────────────────────────────────────────┐  │
              │   │                  SQLite (db.sqlite3)                  │  │
              │   └───────────────────────────────────────────────────────┘  │
              └──────────────────────────────────────────────────────────────┘
                                           │
                                           ▼
                              Gunicorn → Nginx → HTTPS (Let's Encrypt)
                              Host: bolpar-server.probusinesspy.xyz
                              Server: 128.199.15.221 (DigitalOcean)
```

### Decisiones clave

| Decisión | Por qué |
|---|---|
| **Monolito Django** | Simple para un equipo chico. Toda la lógica de OT, empleados, máquinas y autenticación en un sólo proceso. |
| **SQLite en producción** | Heredado del scaffold; el volumen actual lo soporta. Migrar a PostgreSQL es trivial cuando el tráfico justifique. |
| **JWT (simplejwt) con blacklist** | Front externo stateless; los logs blacklistean refresh tokens al hacer logout. |
| **Webhook saliente async** (`threading.Thread`) | Antes era síncrono y bloqueaba cada `save()` de `MachineStatusLog` hasta 5 s. Para volúmenes mayores, considerar Celery. |
| **Django Admin como UI de soporte** | Permite al equipo de operaciones consultar/corregir datos sin tocar la API. |
| **Anidado replace-on-update** en `SalesOrder` | El front envía la OT completa con sus items/planificación/consumos en un solo PUT. El serializer borra y recrea los anidados. |

---

## 2. Stack y versiones

Capa | Tecnología
---|---
Lenguaje | Python (probado con 3.12/3.14, ver `myenv/pyvenv.cfg`)
Framework web | Django + Django REST Framework
Auth | `djangorestframework-simplejwt` (con `token_blacklist`) + `rest_framework.authtoken` (legacy fallback)
Filtros | `django-filter`
CORS | `django-cors-headers`
HTTP saliente | `requests`
DB local | SQLite 3 (`db.sqlite3`)
WSGI | Gunicorn
Reverse proxy | Nginx
TLS | Let's Encrypt (Certbot)
Procesos | systemd (`bolpar-server.probusinesspy.xyz.gunicorn.service`)
Sesión remota | tmux (script `connect_vpn.exp` con expect)

Versiones exactas instaladas: ver [requirements.txt](requirements.txt). El proyecto no fija versiones — para reproducir un entorno, generar un `requirements.lock` con `pip freeze`.

---

## 3. Estructura del repo

```
bolpar-server/
├── manage.py
├── config.py                       # Secrets locales (gitignored)
├── api_rest/                       # Proyecto Django
│   ├── settings.py                 # Settings principales + override env vars
│   ├── urls.py                     # Routing raíz
│   └── wsgi.py
├── apps/
│   ├── authentication/             # Modelo de usuario + endpoints JWT
│   │   ├── models.py               # CustomUser (AbstractUser + fav_color, machineTurn)
│   │   ├── serializers.py          # TokenObtain con claims custom
│   │   ├── views.py                # Login, registro, blacklist, hello
│   │   ├── urls.py
│   │   ├── admin.py
│   │   ├── tests.py                # Tests unitarios + API
│   │   └── migrations/
│   └── inventario/                 # Núcleo del dominio
│       ├── models.py               # 9 modelos + signal post_save (Zoho webhook async)
│       ├── serializers.py
│       ├── views.py                # 7 ModelViewSets + 6 acciones custom
│       ├── urls.py                 # DRF DefaultRouter
│       ├── admin.py
│       ├── forms.py                # Formsets para vistas server-rendered (no usadas en API)
│       ├── tests.py                # Tests de modelos + endpoints
│       ├── tests_postman.py        # Validación de la colección Postman
│       └── migrations/
├── README.md                       # Guía de uso
├── ARCHITECTURE.md                 # Este archivo
├── HANDOVER.md                     # Checklist de cesión + runbook
├── Bolpar.postman_collection.json  # Colección Postman
├── requirements.txt
└── db.sqlite3                      # DB local (gitignored)
```

---

## 4. Modelo de datos (lógico)

### Diagrama entidad-relación (ASCII)

```
                           ┌──────────────┐
                           │  CustomUser  │  (Django auth)
                           │  + machineTurn│
                           └──────────────┘
                                    │ (no FK directa, sólo claim en JWT)
                                    ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          SalesOrder (OT)                                   │
│   PK: id, UNIQUE: so_number                                                │
│   Campos calculados: sub_total, grand_total                                │
└──────┬───────────┬───────────────┬──────────────────────┬──────────────────┘
       │1:N        │1:N            │1:N                   │1:N
       ▼           ▼               ▼                      ▼
 ┌──────────┐  ┌─────────┐  ┌──────────────┐   ┌─────────────────┐
 │OrderedItem│  │Planning │  │ Consumption  │   │    Machine      │
 │           │  │Production│  │   Input     │   │ data_json (JSON)│
 │net_total  │  │          │  │             │   └────┬────────────┘
 │(calc)     │  │          │  │             │        │
 └───────────┘  └─────────┘  └──────────────┘        │
                                                     │1:N           1:N
                                                     ▼              ▼
                                       ┌──────────────────┐  ┌──────────────────┐
                                       │ MachineSnapshot  │  │ MachineStatusLog │
                                       │ (histórico       │  │ post_save → Zoho │
                                       │  inmutable)      │  │ webhook (async)  │
                                       └──────────────────┘  └──────────────────┘
                                                     │
                                                     │1:N
                                                     ▼
                                          ┌─────────────────────┐
                                          │  MachineEmployee    │ ◀──┐
                                          │ assigned_at,        │     │ N:1
                                          │ is_active           │     │
                                          └─────────────────────┘     │
                                                                      │
                                                              ┌───────────┐
                                                              │ Employee  │
                                                              │ zoho_id   │
                                                              │ (UPSERT)  │
                                                              └───────────┘
```

### Reglas de negocio embebidas (a tener en cuenta al refactorizar)

| Modelo | Regla | Dónde está |
|---|---|---|
| `OrderedItem` | `net_total = quantity * list_price - discount`, computado en `save()` | [apps/inventario/models.py:105-107](apps/inventario/models.py#L105-L107) |
| `SalesOrder` | `sub_total = Σ items.net_total`; `grand_total = sub_total + tax + excise_duty`. Recalculado en `save()` con `update_fields=['sub_total','grand_total']` | [apps/inventario/models.py:80-85](apps/inventario/models.py#L80-L85) |
| `ConsumptionInput` | `cantidad` redondeada a 2 decimales con `ROUND_HALF_UP` | [apps/inventario/models.py:138-142](apps/inventario/models.py#L138-L142) |
| `MachineEmployee` | `unique_together = (machine, employee, is_active)` → permite varios pares históricos pero un sólo activo simultáneo | [apps/inventario/models.py:276-277](apps/inventario/models.py#L276-L277) |
| `MachineStatusLog` | Cada `save()` dispara un webhook saliente a Zoho en un thread daemon | [apps/inventario/models.py:185-216](apps/inventario/models.py#L185-L216) |
| `Employee` | UPSERT por `zoho_id` desde la acción `funcionarios/upsert-zoho/` (no se borra cuando Zoho marca como inactivo, se mantiene la traza) | [apps/inventario/views.py:303-356](apps/inventario/views.py#L303-L356) |
| `SalesOrderSerializer` | Anidados (`items`, `planificacion_produccion`, `consumo_insumos`) son **replace-on-update**: en `PUT/PATCH` se borran y recrean | [apps/inventario/serializers.py:75-126](apps/inventario/serializers.py#L75-L126) |
| `MachineStatusLogSerializer` | `machine` opcional cuando se anida (padre lo asigna), obligatorio standalone (validado por `self.parent is None`) | [apps/inventario/serializers.py:120-138](apps/inventario/serializers.py#L120-L138) |

---

## 5. Capas y flujo de un request

```
HTTP request
   │
   ▼
Nginx ─ TLS termination, gzip, static, proxy_pass → Gunicorn ─┐
                                                              │
   ┌──────────────────────────────────────────────────────────┘
   ▼
Gunicorn (workers WSGI) ─ corre api_rest.wsgi:application
   │
   ▼
Django middleware stack:
   1. corsheaders.middleware.CorsMiddleware
   2. SecurityMiddleware
   3. SessionMiddleware
   4. CommonMiddleware
   5. CsrfViewMiddleware
   6. AuthenticationMiddleware
   7. MessageMiddleware
   8. XFrameOptionsMiddleware
   │
   ▼
URL resolver (api_rest/urls.py)
   ├─ /admin/   → Django admin
   ├─ /api/...  → apps.authentication.urls
   └─ /api/inventario/... → apps.inventario.urls (DRF DefaultRouter)
   │
   ▼
DRF ViewSet:
   - DEFAULT_AUTHENTICATION_CLASSES: JWTAuthentication, TokenAuthentication
   - DEFAULT_PERMISSION_CLASSES: IsAuthenticated
   - DEFAULT_FILTER_BACKENDS: DjangoFilterBackend
   │
   ▼
Serializer ─ valida y transforma JSON ↔ instancias
   │
   ▼
Modelo ─ lógica de negocio en save()
   │
   ▼
SQLite ─ persistencia
   │
   ▼ (opcional)
post_save signal ─ thread daemon → POST a Zoho (no bloquea respuesta)
   │
   ▼
HTTP response (JSON)
```

---

## 6. Endpoints (referencia rápida)

### Autenticación

```
POST /api/user/create/                      público
POST /api/token/obtain/                     público   (devuelve {access, refresh} con claims fav_color, machineTurn)
POST /api/token/refresh/                    público   (rota refresh, invalida el anterior)
POST /api/blacklist/                        público   (logout)
GET  /api/hello/                            JWT
POST /api-token-auth/                       público   (DRF authtoken legacy)
```

### Inventario (montados en `/api/inventario/` por DRF DefaultRouter)

```
# CRUD estándar
/api/inventario/orders/                     SalesOrder
/api/inventario/items/                      OrderedItem
/api/inventario/planificacion/              PlanningProduction
/api/inventario/insumos/                    ConsumptionInput
/api/inventario/machines/                   Machine     (filtro: ?ot=<sales_order_id>)
/api/inventario/machine-status-logs/        MachineStatusLog
/api/inventario/funcionarios/               Employee    (filtros: ?documento=, ?name=, ?sector=, ?rol=)

# Acciones custom
POST /api/inventario/orders/{id}/consumos/real/bulk/      Inserción masiva de consumos
GET  /api/inventario/machines/{id}/employees/             Funcionarios activos asignados
POST /api/inventario/machines/{id}/set-employees/         Asignar/reemplazar/agregar funcionarios
GET  /api/inventario/machines/{id}/snapshots/             Histórico de data_json
POST /api/inventario/machines/{id}/finalize/              Snapshot inmutable + opcional reset
POST /api/inventario/funcionarios/upsert-zoho/            UPSERT por zoho_id (uno o lista)
```

Detalles de payload y respuestas: [README.md](README.md#endpoints-rest).

---

## 7. Integración con Zoho CRM

### 7.1 Inbound — Zoho → bolpar-server (push de datos)

Zoho envía datos a este backend mediante:

| Origen | Endpoint | Cómo |
|---|---|---|
| Sales Orders | `POST /api/inventario/orders/` | Una Function de Zoho o un workflow. Payload: la OT con sus items/planificación/consumos. |
| Funcionarios | `POST /api/inventario/funcionarios/upsert-zoho/` | UPSERT por `zoho_id`. El mapeador (`map_zoho_to_employee_fields`) tolera variantes de claves: `N_mero_de_Documento` / `Numero_de_Documento` / `Nro_de_Documento`, `M_vil` / `Movil` / `Mobile`. |

El payload original siempre se guarda en `Employee.raw_zoho` (JSONField) para auditoría.

### 7.2 Outbound — bolpar-server → Zoho (push de estado de máquina)

**Disparador**: cada `save()` de `MachineStatusLog` (tanto `INSERT` como `UPDATE`) dispara el signal `post_save`.

**Implementación** ([apps/inventario/models.py:185-216](apps/inventario/models.py#L185-L216)):

```python
@receiver(post_save, sender='inventario.MachineStatusLog')
def notify_external_api(sender, instance, created, **kwargs):
    url = getattr(settings, "ZOHO_WEBHOOK_URL", None)
    if not url:
        return
    payload = {...}
    timeout = getattr(settings, "ZOHO_WEBHOOK_TIMEOUT", 5)
    threading.Thread(
        target=_post_zoho_webhook,
        args=(url, payload, timeout),
        daemon=True,
    ).start()
```

**Características**:
- Async (thread daemon) → no bloquea la transacción ni la respuesta HTTP.
- Si `ZOHO_WEBHOOK_URL` está vacía o no definida, el webhook se omite silenciosamente (útil en tests/staging).
- Errores van al logger `apps.inventario.models` (no a `print`).
- **Sin retry ni cola** → si Zoho está caído, el evento se pierde. Para garantías, migrar a Celery + Redis.

**Configuración**:
```python
# Vía env var (gana sobre config.py):
ZOHO_WEBHOOK_URL=https://www.zohoapis.com/crm/v7/functions/...?zapikey=...
ZOHO_WEBHOOK_TIMEOUT=5
```

**Payload enviado**:
```json
{
  "machine_id": 42,
  "estado": "produciendo",
  "fecha_hora": "2026-04-26T10:15:00+00:00",
  "motivo": "",
  "nuevo": true
}
```

---

## 8. Autenticación y autorización

### 8.1 JWT con simplejwt

- **Lifetime access**: 19 h ([api_rest/settings.py:137](api_rest/settings.py#L137))
- **Lifetime refresh**: 20 h
- **Rotación**: cada `POST /api/token/refresh/` rota el refresh y blacklistea el anterior.
- **Algoritmo**: HS256 con `SETTINGS.SECRET_KEY` como signing key.
- **Headers aceptados**: `Bearer <token>` o `JWT <token>`.

### 8.2 Claims custom

`MyTokenObtainPairSerializer` ([apps/authentication/serializers.py:7-16](apps/authentication/serializers.py#L7-L16)) inyecta:
- `fav_color` (campo demo, no usado en lógica)
- `machineTurn` (turno del operario)

El frontend puede leer `machineTurn` del JWT para filtrar UI sin hacer otra llamada.

### 8.3 Permisos

Por defecto: `IsAuthenticated`. No hay roles ni grupos definidos a nivel de aplicación — cualquier usuario autenticado puede acceder a cualquier endpoint. Si se necesita granularidad, agregar `permission_classes` por ViewSet.

### 8.4 Endpoints públicos por diseño

- `POST /api/user/create/` (registro)
- `POST /api/token/obtain/` (login)
- `POST /api/token/refresh/`
- `POST /api/blacklist/` (logout)
- `POST /api-token-auth/` (DRF authtoken legacy)

### 8.5 CORS

Configurado en [config.py:28](config.py#L28). Actualmente `CORS_ALLOW_ALL_ORIGINS = True`. ⚠ **En producción real**: cerrar a la lista de dominios del front.

---

## 9. Persistencia y migraciones

- **Engine**: SQLite (`django.db.backends.sqlite3`).
- **Archivo**: `db.sqlite3` en la raíz del proyecto. Gitignored.
- **Migraciones**: rastreadas por Django en `apps/*/migrations/`. Cada app tiene un `0001_initial.py`.
- **Aplicar**: `python manage.py migrate`.
- **Crear nuevas**: `python manage.py makemigrations`.

### ⚠ Implicaciones de SQLite en producción

- Concurrencia limitada (un sólo writer simultáneo).
- Sin replicación nativa.
- Backup = copiar el archivo `db.sqlite3` (con la base detenida o usando `.backup` del cliente sqlite3 para consistencia).
- Tablas grandes (>1M filas) o múltiples workers: considerar PostgreSQL.

### Migración a PostgreSQL (si se decide)

1. Instalar `psycopg2-binary` y agregarlo a `requirements.txt`.
2. En `settings.py`:
   ```python
   DATABASES = {
       'default': {
           'ENGINE': 'django.db.backends.postgresql',
           'NAME': 'bolpar',
           'USER': '...',
           'PASSWORD': '...',
           'HOST': 'localhost',
           'PORT': '5432',
       }
   }
   ```
3. `python manage.py dumpdata > backup.json` (con SQLite activo)
4. Cambiar settings, `migrate`, luego `loaddata backup.json`.

---

## 10. Despliegue (servidor remoto)

### 10.1 Datos del servidor

| Item | Valor |
|---|---|
| IP | `128.199.15.221` (DigitalOcean droplet) |
| Hostname | `bolpar-server.probusinesspy.xyz` |
| Acceso | SSH (rotar la contraseña root y migrar a auth por clave) |
| OS | Ubuntu/Debian (a confirmar con `lsb_release -a`) |
| Servicio systemd | `bolpar-server.probusinesspy.xyz.gunicorn.service` |
| Reverse proxy | Nginx |
| TLS | Let's Encrypt (Certbot) |
| Multiplexer | tmux |
| VPN | script `connect_vpn.exp` (con `expect`) en `/home/base-jwt/connect_vpn.exp` |

### 10.2 Stack de despliegue (esperado)

```
Internet
   │ HTTPS (443)
   ▼
Nginx (puertos 80/443)
   ├─ /static/ → archivos estáticos servidos directo
   └─ /         → proxy_pass a unix socket o 127.0.0.1:8000 (Gunicorn)
   │
   ▼
Gunicorn (gestionado por systemd)
   - command: gunicorn --timeout 120 api_rest.wsgi:application
   - workers: (a confirmar con `systemctl cat bolpar-server.probusinesspy.xyz.gunicorn.service`)
   - virtualenv: probablemente /home/<user>/bolpar-server/myenv/bin/python
   │
   ▼
Django (api_rest.settings)
   │
   ▼
SQLite (db.sqlite3 en el filesystem)
```

### 10.3 Comandos de operación

```bash
# Ver estado del servicio
sudo systemctl status bolpar-server.probusinesspy.xyz.gunicorn.service

# Reiniciar Gunicorn (después de un deploy)
sudo systemctl daemon-reload
sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service

# Logs en vivo
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -f

# Reiniciar Nginx (después de cambios de config)
sudo systemctl restart nginx

# Renovar certificado TLS (Certbot suele tener un cron, verificar)
sudo certbot renew --dry-run
sudo certbot --nginx -d bolpar-server.probusinesspy.xyz -d www.bolpar-server.probusinesspy.xyz

# Sesión persistente
tmux attach
tmux list-sessions
tmux attach-session -t 0

# Salir de tmux sin matarlo: Ctrl-b, d
```

### 10.4 Flujo de deploy (manual, hoy)

1. SSH al server.
2. `cd` al directorio del repo.
3. `git pull` (rama de producción).
4. Activar virtualenv y `pip install -r requirements.txt` si cambiaron deps.
5. `python manage.py migrate` si hay migraciones nuevas.
6. `python manage.py collectstatic --noinput` si cambió algo de admin/static.
7. `sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service`.
8. `journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -f` para verificar arranque limpio.

> **Recomendación a futuro**: automatizar con un script `deploy.sh` o un runner de CI (GitHub Actions con `appleboy/ssh-action` o similar).

---

## 11. Configuración y secretos

### 11.1 `config.py` (gitignored)

Contiene:
- `SECRET_KEY` (clave de firma de JWT y CSRF)
- `DEBUG` (debe ser `False` en prod)
- `HOSTING`, `NGROK_HOST`, `ALLOWED_HOSTS`
- `CORS_ALLOWED_ORIGINS`, `CORS_ALLOW_ALL_ORIGINS`, `CORS_ALLOWED_ORIGIN_REGEXES`
- `SECURE_PROXY_SSL_HEADER`
- `ZOHO_WEBHOOK_URL`, `ZOHO_WEBHOOK_TIMEOUT`

### 11.2 Variables de entorno con prioridad (override)

| Variable | Default (config.py) | Uso |
|---|---|---|
| `ZOHO_WEBHOOK_URL` | URL hardcoded de la Function de Zoho | Apuntar a un mock en staging/tests |
| `ZOHO_WEBHOOK_TIMEOUT` | 5 | Ajustar tolerancia |

Definir en systemd con `Environment="VAR=valor"` o un archivo `EnvironmentFile=/etc/bolpar/.env`.

### 11.3 Recomendaciones para producción

- [ ] Mover `SECRET_KEY` a env var (no a `config.py` aunque esté gitignored — sigue siendo un archivo en el filesystem).
- [ ] `DEBUG = False`.
- [ ] `CORS_ALLOW_ALL_ORIGINS = False` y mantener sólo la lista blanca.
- [ ] Rotar la `zapikey` de Zoho (estuvo histórica en código).
- [ ] Auth SSH por clave, no por contraseña.

---

## 12. Logging y observabilidad

### Estado actual

- Django escribe logs a stdout/stderr → capturados por Gunicorn → systemd → `journalctl`.
- El webhook a Zoho usa el logger `apps.inventario.models` (logger Python estándar).
- No hay APM, ni métricas, ni alertas.

### Sugerencias

- Configurar `LOGGING` en `settings.py` con un handler de archivo rotativo (`RotatingFileHandler`).
- Para alertas: integrar Sentry (solo agregar `sentry-sdk[django]` y `sentry_sdk.init(...)`).
- Para métricas: `django-prometheus` + Grafana.

---

## 13. Tests automáticos

| Archivo | Cobertura |
|---|---|
| [apps/authentication/tests.py](apps/authentication/tests.py) | 9 tests — registro, login, claims JWT, refresh, blacklist, hello |
| [apps/inventario/tests.py](apps/inventario/tests.py) | 32 tests — modelos (totales, redondeo), signal webhook (mockeado), endpoints CRUD + acciones custom |
| [apps/inventario/tests_postman.py](apps/inventario/tests_postman.py) | 16 tests — reproduce cada request de la colección Postman |

**Total**: 57 tests, ~26 segundos.

```bash
python manage.py test apps -v 2
```

Para ampliar la suite con una métrica de cobertura:
```bash
pip install coverage
coverage run --source='.' manage.py test apps
coverage report -m
coverage html  # genera htmlcov/index.html
```

---

## 14. Decisiones documentadas (ADR-light)

### ADR-1: Webhook saliente con `threading.Thread` (no Celery)

- **Contexto**: el webhook se dispara por cada cambio de estado de máquina. El timeout de 5 s bloqueaba la respuesta HTTP.
- **Decisión**: thread daemon en proceso. Sin retry ni persistencia.
- **Consecuencia**: simple, sin dependencias nuevas. Pierde eventos si Zoho está caído. Aceptable para el volumen actual.
- **Cuándo migrar**: si los eventos son críticos o el volumen pasa de ~10/s.

### ADR-2: SQLite en producción

- **Contexto**: scaffold inicial usa SQLite. El volumen actual es bajo.
- **Decisión**: mantener SQLite hasta que haya un caso de bloqueo (concurrencia, escalado horizontal).
- **Cuándo migrar**: cuando aparezcan errores `database is locked` bajo carga, o cuando se necesiten múltiples workers Gunicorn escribiendo simultáneamente.

### ADR-3: Anidados replace-on-update en `SalesOrder`

- **Contexto**: el front envía la OT entera con sus colecciones. Calcular diff es complicado.
- **Decisión**: `update()` borra todos los anidados y los recrea desde el payload.
- **Consecuencia**: simple para el front (siempre envía el set completo). El backend debe recordar disparar un `instance.save()` posterior para recalcular totales (ya implementado).

### ADR-4: `MachineStatusLog.machine` opcional al anidar

- **Contexto**: `POST /machines/` con `status_logs` anidados fallaba porque DRF marcaba `machine` como required.
- **Decisión**: campo opcional con validación condicional `self.parent is None`.
- **Alternativa descartada**: dos serializers separados (más código por mantener).

---

## 15. Próximas mejoras sugeridas

Categorizadas por costo/beneficio:

### Quick wins
- [ ] `DEBUG = False` en producción.
- [ ] `CORS_ALLOW_ALL_ORIGINS = False` y dejar sólo la lista blanca.
- [ ] Rotar `zapikey` de Zoho.
- [ ] Configurar logging a archivo rotativo en `settings.py`.

### Calidad
- [ ] Lock file de dependencias (`pip freeze > requirements.lock`).
- [ ] Cobertura de tests con `coverage`.
- [ ] CI con GitHub Actions (lint + tests en cada PR).

### Operación
- [ ] Script `deploy.sh` o pipeline de CD.
- [ ] Backups automatizados de `db.sqlite3` (cron diario + retención semanal).
- [ ] Sentry para errores en producción.

### Escalado
- [ ] Migrar a PostgreSQL.
- [ ] Webhook a Zoho con Celery + Redis (retry + dead-letter).
- [ ] Cache de queries pesadas con Redis.
