# TechGear: guía del taller

Las cuentas se guardan en MongoDB y FastAPI las administra. Django no crea
usuarios ni contraseñas; conserva en su sesión el JWT y los datos básicos de
la cuenta.

## Preparar el proyecto

En `techgear_api\.env` configura estas variables:

| Variable | Uso |
|---|---|
| `MONGO_URL` | Dirección de conexión de MongoDB Atlas. |
| `DATABASE_NAME` | Nombre de la base de datos. |
| `CLAVE` | Contraseña de MongoDB, si no está incluida en `MONGO_URL`. |
| `JWT_SECRET` | Clave secreta obligatoria para firmar los JWT. |
| `JWT_EXPIRE_MINUTES` | Minutos de vigencia del JWT; si se omite, usa `60`. |

Si hace falta instalar los paquetes, desde la carpeta principal ejecuta:

```powershell
.\virtual\Scripts\python.exe -m pip install -r techgear_api\requirements.txt
.\virtual\Scripts\python.exe -m pip install -r techgear_web\requirements.txt
```

Genera un secreto largo con este comando:

```powershell
.\virtual\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el resultado en `.env` como `JWT_SECRET=...`. No compartas ni subas ese
valor al repositorio. FastAPI muestra un error claro al arrancar si falta.

Para este taller, Django guarda la sesión en una cookie firmada `HttpOnly`, sin
base de datos. Es una decisión simple para aprender: la firma no cifra la
cookie, así que no debe usarse así en una aplicación real.

## Crear el primer administrador

El registro del sitio solo crea cuentas de cliente. Desde la carpeta principal
del proyecto ejecuta:

```powershell
.\virtual\Scripts\python.exe .\techgear_api\crear_admin.py
```

Escribe el nombre de usuario, correo y contraseña cuando los pida. La
contraseña debe tener al menos 8 caracteres; el script la guarda con bcrypt
directamente en MongoDB.

## Ejecutar los servidores

Abre dos terminales en la carpeta principal del proyecto.

Terminal 1 — FastAPI, en el puerto `8001`:

```powershell
Set-Location .\techgear_api
..\virtual\Scripts\python.exe -m uvicorn main:app --app-dir src --reload --host 127.0.0.1 --port 8001
```

Terminal 2 — Django, en el puerto `8000`:

```powershell
.\virtual\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abre `http://127.0.0.1:8000/`. La documentación de FastAPI está en
`http://127.0.0.1:8001/docs`. Si FastAPI usa otra dirección, configura
`API_URL` para Django.

## Probar el sitio

1. Ve a `/registro/`, crea una cuenta de cliente y confirma que se inicia la
   sesión automáticamente.
2. Sal y vuelve a entrar desde `/ingresar/` usando el correo y la contraseña.
3. Crea el administrador con el script y entra desde `/admin-ingresar/`.
   Solo el administrador puede crear, editar o borrar productos.
4. Entra como cliente y crea un pedido. FastAPI toma el identificador de la
   cuenta del JWT, revisa el stock y lo descuenta.
5. Para comprobar la expiración, cambia `JWT_EXPIRE_MINUTES=1` en
   `techgear_api\.env`, reinicia FastAPI, inicia sesión y espera más de un
   minuto. Al hacer una acción protegida, Django borra la sesión y te pide
   entrar de nuevo.

El catálogo y la página de inicio son públicos. Crear pedidos requiere una
sesión de cliente; el panel y sus operaciones requieren una sesión de
administrador. Salir se hace con el formulario POST del sitio.

## Pruebas y revisión

Desde la carpeta `techgear_api`, ejecuta:

```powershell
..\virtual\Scripts\python.exe -m pytest
```

Desde la carpeta principal, ejecuta las pruebas y la revisión de Django:

```powershell
.\virtual\Scripts\python.exe manage.py test
.\virtual\Scripts\python.exe manage.py check
```

FastAPI valida cada acción protegida con el JWT de la cuenta.
