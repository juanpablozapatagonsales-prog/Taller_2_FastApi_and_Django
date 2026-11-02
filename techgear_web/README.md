# TechGear Django

## Ejecutar

Las cuentas se guardan en la colección `users` de MongoDB a través de FastAPI. Inicia los dos servidores en terminales separadas, desde la raíz del repositorio.

Instala las dependencias de ambos servicios:

```powershell
.\virtual\Scripts\python.exe -m pip install -r techgear_api\requirements.txt
.\virtual\Scripts\python.exe -m pip install -r techgear_web\requirements.txt
```

Terminal 1 — FastAPI:

```powershell
Set-Location .\techgear_api
..\virtual\Scripts\python.exe -m uvicorn main:app --reload --app-dir src
```

Terminal 2 — Django:

```powershell
.\virtual\Scripts\python.exe manage.py migrate
.\virtual\Scripts\python.exe manage.py runserver 127.0.0.1:8001
```

Abre `http://127.0.0.1:8001/`. Django envía las operaciones de cuenta a `FASTAPI_BASE_URL`, que por defecto es `http://127.0.0.1:8000`. FastAPI debe iniciar correctamente y conectarse a MongoDB para que registro e inicio de sesión funcionen. SQLite solo sirve para las tablas internas de Django; no almacena estas cuentas. Los productos de la portada y la bolsa son contenido de muestra.

Configura una clave estable `JWT_SECRET_KEY` en `techgear_api/.env` antes de usar las sesiones, por ejemplo, generándola localmente con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

El JWT dura ocho horas. Si no se configura `JWT_SECRET_KEY`, FastAPI genera una clave aleatoria de desarrollo al iniciar; las sesiones activas dejarán de ser válidas cuando se reinicie el proceso.

## Sesiones y usuarios

Las rutas Django actúan como proxy del endpoint FastAPI de usuarios. FastAPI valida los datos, guarda el usuario en MongoDB y genera el JWT. Django entrega el JWT al navegador en una cookie `HttpOnly`, con protección CSRF para las solicitudes `POST`.

| Método | Ruta en Django | Ruta FastAPI | Uso |
|---|---|---|---|
| `POST` | `/api/usuarios/` | `POST /usuarios/` | Registrar `{ "username", "email", "password" }` en MongoDB |
| `POST` | `/api/usuarios/login/` | `POST /usuarios/login` | Validar credenciales almacenadas en MongoDB |
| `POST` | `/api/usuarios/logout/` | — | Borrar la cookie JWT |
| `GET` | `/api/usuarios/me/` | `GET /usuarios/me` | Validar el JWT y consultar el usuario en MongoDB |

`/api/usuarios/me/` también acepta `Authorization: Bearer <token>`. Los endpoints originales FastAPI de usuarios permanecen disponibles.

## Pruebas

```powershell
.\virtual\Scripts\python.exe manage.py test techgear_web.store
```
