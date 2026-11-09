# Cesión del proyecto — bolpar-server

Documento operacional para **transferir el proyecto a un nuevo equipo**. Va al grano: qué entregar, qué accesos pedir/rotar, cómo desplegar, qué hacer cuando algo se rompe, y dónde están las trampas conocidas.

Acompaña a [README.md](README.md) (uso) y [ARCHITECTURE.md](ARCHITECTURE.md) (diseño).

---

## 1. Checklist de cesión (qué entregar)

### Código y documentación
- [x] Repositorio Git completo
- [x] [README.md](README.md) — instalación, uso, endpoints
- [x] [ARCHITECTURE.md](ARCHITECTURE.md) — diseño, decisiones, modelo de datos
- [x] [HANDOVER.md](HANDOVER.md) — este archivo
- [x] Colección Postman ([Bolpar.postman_collection.json](Bolpar.postman_collection.json))
- [x] Suite de tests (57 tests, `python manage.py test apps`)

### Accesos (a transferir o rotar)
- [ ] Servidor SSH: `root@128.199.15.221` ⚠ **rotar contraseña** y migrar a auth por clave SSH
- [ ] Cuenta DigitalOcean (donde está el droplet)
- [ ] Dominio `bolpar-server.probusinesspy.xyz` (registrador + DNS)
- [ ] Cuenta Cloudflare (si aplica)
- [ ] Zoho CRM: usuario admin + acceso a las Functions y a la `zapikey` del webhook
- [ ] Cuenta de email para alertas / Let's Encrypt
- [ ] Repositorio Git (GitHub/GitLab/Bitbucket): transferir owner o agregar al nuevo equipo como admin

### Credenciales y secretos
- [ ] `SECRET_KEY` de Django (en `config.py` del server)
- [ ] `ZOHO_WEBHOOK_URL` con la `zapikey` (en `config.py` o env var del systemd)
- [ ] Superuser de Django admin (crear uno nuevo y borrar los antiguos: `python manage.py createsuperuser`)
- [ ] Cualquier otro secreto en `/etc/bolpar/`, `~/.env`, o systemd `EnvironmentFile=`

### Sesiones tmux y procesos
- [ ] Hablar de qué corre en tmux y por qué (VPN persistente, `connect_vpn.exp`)

---

## 2. Datos del entorno

| Item | Valor |
|---|---|
| **Servidor** | DigitalOcean Droplet — `128.199.15.221` |
| **Hostname** | `bolpar-server.probusinesspy.xyz` |
| **OS** | Ubuntu/Debian (a confirmar — ver §6) |
| **Servicio** | systemd unit `bolpar-server.probusinesspy.xyz.gunicorn.service` |
| **Web server** | Nginx |
| **App server** | Gunicorn |
| **DB** | SQLite (`db.sqlite3` en el filesystem del repo) |
| **TLS** | Let's Encrypt (Certbot) |
| **VPN** | Script `connect_vpn.exp` (en `/home/base-jwt/`) — corre dentro de tmux |
| **Repo local del dueño actual** | Windows, virtualenv en `myenv/` |

---

## 3. Comandos read-only que el dueño actual debe correr

Para llenar los espacios vacíos del documento, estos comandos no modifican nada:

```bash
ssh <usuario>@128.199.15.221  # con la nueva clave SSH

# 1. Sistema
lsb_release -a
uname -a
df -h
free -h
uptime

# 2. Versiones
python3 --version
which python3
which gunicorn
nginx -v

# 3. Servicio Gunicorn
systemctl cat bolpar-server.probusinesspy.xyz.gunicorn.service
systemctl status bolpar-server.probusinesspy.xyz.gunicorn.service

# 4. Nginx
sudo nginx -T | sed -n '/server_name bolpar/,/^}$/p'   # vhost completo
ls /etc/nginx/sites-enabled/

# 5. Certificados
sudo certbot certificates

# 6. Cron (backups u otros)
crontab -l
sudo crontab -l
ls /etc/cron.d/

# 7. Repo en el server
cd <ruta-del-proyecto>
pwd
git remote -v
git log --oneline -5
git status

# 8. Virtualenv
ls myenv/bin/python* 2>/dev/null || ls .venv/bin/python* 2>/dev/null

# 9. Variables de entorno del servicio
sudo systemctl show bolpar-server.probusinesspy.xyz.gunicorn.service \
    --property=Environment,EnvironmentFiles,User,WorkingDirectory,ExecStart

# 10. Tamaño actual de la DB
ls -lh db.sqlite3
sqlite3 db.sqlite3 "SELECT name FROM sqlite_master WHERE type='table';"
sqlite3 db.sqlite3 "SELECT COUNT(*) FROM inventario_salesorder;"
```

Pegame el output y completo este documento con los valores exactos del server.

---

## 4. Despliegue (manual, hoy)

### 4.1 Pre-requisitos en el server

- Python 3.10+ con `venv`
- `git`
- Nginx instalado y con vhost configurado
- Gunicorn dentro del virtualenv
- Certbot

### 4.2 Pasos para un release

```bash
# 1. SSH al server
ssh <usuario>@128.199.15.221

# 2. Ir al repo
cd <path>/bolpar-server

# 3. Pull
git fetch
git checkout main
git pull

# 4. Activar venv
source myenv/bin/activate

# 5. Dependencias (si requirements.txt cambió)
pip install -r requirements.txt

# 6. Migraciones
python manage.py migrate

# 7. Static (si hubo cambios en admin/static)
python manage.py collectstatic --noinput

# 8. Reiniciar servicio
sudo systemctl daemon-reload
sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service

# 9. Verificar
sudo systemctl status bolpar-server.probusinesspy.xyz.gunicorn.service
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -f
# Ctrl-C para salir del seguimiento

# 10. Smoke test
curl -i https://bolpar-server.probusinesspy.xyz/api/hello/   # debe pedir auth
```

### 4.3 Rollback rápido

```bash
git log --oneline -10
git checkout <commit-bueno-anterior>
sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service
```

---

## 5. Runbook — qué hacer cuando algo se rompe

### 5.1 La API responde 502 / 504

Indica que Nginx no puede hablar con Gunicorn.

```bash
# 1. Estado de Gunicorn
sudo systemctl status bolpar-server.probusinesspy.xyz.gunicorn.service

# 2. Si está down, arrancar y revisar el log
sudo systemctl restart bolpar-server.probusinesspy.xyz.gunicorn.service
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -n 200

# 3. Si el log muestra "ImportError" o falla de migración → corregir y redeployar
# 4. Si muestra timeout: aumentar --timeout en el systemd unit
```

### 5.2 Certificado TLS expirado

```bash
sudo certbot certificates              # ver fechas
sudo certbot renew                     # renovar manualmente
sudo systemctl reload nginx
```

### 5.3 La DB devuelve "database is locked"

SQLite no soporta múltiples writers concurrentes. Mitigaciones:
1. Confirmar que sólo hay un worker Gunicorn (configurado en el systemd unit con `--workers 1`).
2. Reducir transacciones largas.
3. Migrar a PostgreSQL ([ARCHITECTURE.md §9](ARCHITECTURE.md#9-persistencia-y-migraciones)).

### 5.4 Webhook a Zoho falla

```bash
# Ver logs del logger apps.inventario.models
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -n 500 | grep "Zoho webhook"
```

Posibles causas:
- `ZOHO_WEBHOOK_URL` mal configurada.
- `zapikey` rotada del lado de Zoho.
- Function de Zoho con error → revisar en el panel de Zoho.

El backend NO reintenta. Si el evento es crítico, recrear el `MachineStatusLog` (un PATCH dispara el signal de nuevo).

### 5.5 Disk full

```bash
df -h
du -sh /var/log/*
sudo journalctl --vacuum-time=2weeks   # comprimir logs viejos
```

Si crece `db.sqlite3`: archivar OTs antiguas (no hay limpieza automática).

### 5.6 Cambiar el dominio

1. Apuntar el nuevo DNS A-record a `128.199.15.221`.
2. Editar el vhost de Nginx (`/etc/nginx/sites-available/bolpar...`).
3. `sudo certbot --nginx -d nuevo.dominio.com`.
4. Agregar el nuevo dominio a `ALLOWED_HOSTS` y `CORS_ALLOWED_ORIGINS` en `config.py`.
5. Reiniciar Gunicorn y Nginx.

---

## 6. Backups

### 6.1 Estado actual

⚠ **No hay backup automatizado** (a confirmar con `crontab -l`). En SQLite, perder el archivo = perder todo.

### 6.2 Backup manual

```bash
# En el server
cd <path>/bolpar-server

# Snapshot consistente con el cliente sqlite3 (no hace falta detener el servicio)
sqlite3 db.sqlite3 ".backup /backups/db-$(date +%Y%m%d-%H%M).sqlite3"

# O dump SQL portable
sqlite3 db.sqlite3 ".dump" | gzip > /backups/db-$(date +%Y%m%d-%H%M).sql.gz
```

### 6.3 Cron diario sugerido

```bash
sudo crontab -e
```

```cron
# Backup diario a las 3 AM, retención de 7 días
0 3 * * * sqlite3 /path/to/db.sqlite3 ".backup /backups/db-$(date +\%Y\%m\%d).sqlite3" && find /backups -name 'db-*.sqlite3' -mtime +7 -delete
```

### 6.4 Restore

```bash
sudo systemctl stop bolpar-server.probusinesspy.xyz.gunicorn.service
cp /backups/db-YYYYMMDD.sqlite3 <path>/bolpar-server/db.sqlite3
chown <usuario>:<grupo> <path>/bolpar-server/db.sqlite3
sudo systemctl start bolpar-server.probusinesspy.xyz.gunicorn.service
```

---

## 7. Tareas inmediatas para el equipo nuevo

Por orden de prioridad:

### Día 0 (antes de tocar nada)
1. **Rotar contraseña SSH del root** y migrar a auth por clave.
2. **Hacer backup full**: copiar `db.sqlite3` y todo el repo del server.
3. **Clonar el repo** local y correr la suite de tests (`python manage.py test apps`) — debe dar 57/57 OK.

### Semana 1
4. Crear superuser propio en Django admin, eliminar los antiguos.
5. Rotar `SECRET_KEY` de Django y `zapikey` de Zoho.
6. Confirmar que el webhook saliente funciona (crear un `MachineStatusLog` y verificar que llega a Zoho).
7. Configurar backups automáticos (§6.3).

### Mes 1
8. Configurar Sentry para errores en producción.
9. Endurecer producción: `DEBUG=False`, `CORS_ALLOW_ALL_ORIGINS=False`, lista blanca explícita.
10. CI con GitHub Actions: tests + lint en cada PR.

### Cuando el volumen lo justifique
11. Migrar a PostgreSQL.
12. Webhook a Zoho con Celery + Redis.

---

## 8. Trampas conocidas (read this first)

### 8.1 `config.py` está en `.gitignore`
- Cuando clonas el repo nuevo, **falta `config.py`**. Hay que pedírselo al dueño actual o reconstruirlo (ver [README.md](README.md#configuración)).

### 8.2 Tests mockean el webhook a Zoho
- En tests, `@override_settings(ZOHO_WEBHOOK_URL="")` desactiva el webhook. Si en producción `ZOHO_WEBHOOK_URL` queda vacía, **los eventos de máquina no llegan a Zoho**. Verificar que esté seteada después de cualquier deploy.

### 8.3 Anidados replace-on-update
- `PUT /api/inventario/orders/{id}/` con `items=[...]` **borra y recrea** los items. Si el front envía sólo un item, los demás desaparecen. El front debe siempre enviar el set completo.

### 8.4 `MachineStatusLog` dispara el webhook también en update
- `PATCH /machine-status-logs/{id}/` re-dispara el webhook. Atención al editar logs antiguos (Zoho recibe un evento "nuevo": false).

### 8.5 `Employee.zoho_id` es la clave de UPSERT
- Si Zoho cambia el ID de un funcionario, el endpoint `upsert-zoho/` lo creará como nuevo en vez de actualizar. No debería pasar (los IDs Zoho son inmutables), pero si pasa, hay duplicados.

### 8.6 `OrderedItem` editado por `/items/` directo no recalcula totales
- Al editar items vía `/api/inventario/items/{id}/`, `SalesOrder.sub_total` no se actualiza. Para mantener coherencia, usar siempre `PUT /orders/{id}/` con todos los items anidados.

### 8.7 `ConsumptionInputSerializer` redondea cantidad a 2 decimales
- Pasar `12.345 kg` se guarda como `12.35`. Documentar al front.

### 8.8 `tmux` y la VPN
- Hay una sesión tmux corriendo `connect_vpn.exp`. Si el server reinicia, esa VPN no se levanta sola. Ver `/home/base-jwt/connect_vpn.exp` y considerar systemd o cron @reboot.

### 8.9 No hay rate limiting
- Los endpoints están abiertos al volumen que sea. Si se expone más, agregar `django-ratelimit` o configurarlo a nivel Nginx.

---

## 9. Contactos

| Rol | Quién | Cómo contactar |
|---|---|---|
| Dueño actual | rduarte01 (`sistemacrm@protek.com.py`) | _completar_ |
| DigitalOcean | _completar_ | _completar_ |
| Zoho admin | _completar_ | _completar_ |
| DNS / dominio | _completar_ | _completar_ |
| Soporte de planta | _completar_ | _completar_ |

---

## 10. Smoke test post-cesión

Para confirmar que el equipo nuevo tiene todo lo que necesita:

```bash
# 1. Acceso al server
ssh <usuario>@128.199.15.221 echo OK

# 2. Acceso al admin
curl -I https://bolpar-server.probusinesspy.xyz/admin/

# 3. Login de operario funcional
curl -X POST https://bolpar-server.probusinesspy.xyz/api/token/obtain/ \
     -H "Content-Type: application/json" \
     -d '{"username":"<user>","password":"<pass>"}'

# 4. Repo cloneable
git clone <url-repo>
cd bolpar-server
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# Crear config.py local con valores de dev
python manage.py migrate
python manage.py test apps   # 57/57 OK

# 5. Webhook saliente vivo (en el server)
sudo journalctl -u bolpar-server.probusinesspy.xyz.gunicorn -f
# En otra terminal, crear un MachineStatusLog vía API y observar el log "Zoho webhook OK"
```

Si los 5 pasos pasan, la cesión está completa.
