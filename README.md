# TechGear 🛒

Proyecto educativo de tienda en línea construido con **Django** y **FastAPI**.
El sitio Django muestra la tienda y sus formularios; la API FastAPI administra
usuarios, productos y pedidos; **MongoDB Atlas** guarda esos datos.

> 📚 Este proyecto es para aprender y practicar. La sesión de Django usa una
> cookie firmada para simplificar el taller: su contenido no está cifrado. No
> copies esta decisión a una aplicación real sin revisar sus requisitos de
> seguridad.

## 📑 Contenido

- [Qué contiene el proyecto](#-qué-contiene-el-proyecto)
- [Cómo funciona la autenticación](#-cómo-funciona-la-autenticación)
- [Requisitos y configuración local](#-requisitos-y-configuración-local)
- [Ejecutar los servidores](#-ejecutar-los-servidores)
- [Crear el primer administrador](#-crear-el-primer-administrador)
- [Probar las funciones](#-probar-las-funciones)
- [Rutas principales de la API](#-rutas-principales-de-la-api)
- [Pruebas automáticas](#-pruebas-automáticas)
- [Despliegue en Vercel](#-despliegue-en-vercel)
- [Notas y solución de problemas](#-notas-y-solución-de-problemas)

## 🧩 Qué contiene el proyecto

| Parte | Tecnología | Responsabilidad |
|---|---|---|
| `techgear_web/` | Django | Páginas de la tienda, formularios, sesión del navegador y llamadas a la API. |
| `techgear_api/` | FastAPI | Inicio de sesión, autorización, productos, pedidos y conexión a MongoDB. |
| MongoDB Atlas | Base de datos | Guarda usuarios, productos y pedidos. Las contraseñas de usuarios se guardan con bcrypt. |
| `vercel.json` | Vercel Services | Declara los servicios de Django y FastAPI y el binding entre ellos. |

El archivo `manage.py` está en la raíz del proyecto. Django tiene sus
dependencias en `techgear_web/requirements.txt`; FastAPI tiene las suyas en
`techgear_api/requirements.txt`.

La aplicación de tienda de Django no guarda las cuentas, los productos ni los
pedidos: esos datos pertenecen a FastAPI y MongoDB. Django usa sesiones en
cookies firmadas, no sesiones almacenadas en su base de datos. El proyecto
conserva la configuración SQLite predeterminada de Django para sus componentes
integrados.

## 🔐 Cómo funciona la autenticación

1. La persona envía su correo y contraseña a Django.
2. Django solicita el inicio de sesión a FastAPI, que compara la contraseña con
   el hash bcrypt guardado en MongoDB.
3. FastAPI devuelve un JWT firmado con HS256 y los datos básicos de la cuenta.
   El token contiene el identificador, nombre de usuario, rol y vencimiento; no
   contiene la contraseña.
4. Django guarda el JWT y los datos básicos en su sesión, enviada al navegador
   dentro de una cookie firmada. La cookie es `HttpOnly` y usa `SameSite=Lax`.
5. Para las operaciones protegidas, Django envía el JWT a FastAPI en el
   encabezado de autorización de tipo Bearer.
6. FastAPI valida el token y aplica los permisos: un cliente solo ve sus
   pedidos; un administrador puede ver todos y administrar productos.

El registro desde el sitio crea cuentas con rol `cliente`. El rol `admin` se
asigna creando la primera cuenta con el script de administración.

## 🧰 Requisitos y configuración local

Necesitas Python, pip y una base de datos MongoDB Atlas accesible desde tu
equipo. Abre PowerShell en la carpeta raíz del proyecto.

### 1. Instalar dependencias

Si ya existe el entorno `virtual`, puedes usarlo:

```powershell
.\virtual\Scripts\python.exe -m pip install -r .\techgear_api\requirements.txt
.\virtual\Scripts\python.exe -m pip install -r .\techgear_web\requirements.txt
```

Si aún no existe, créalo primero:

```powershell
python -m venv virtual
.\virtual\Scripts\python.exe -m pip install -r .\techgear_api\requirements.txt
.\virtual\Scripts\python.exe -m pip install -r .\techgear_web\requirements.txt
```

### 2. Configurar FastAPI y MongoDB

Crea `techgear_api/.env` (no lo subas al repositorio) y configura las variables
que necesita la API:

| Variable | Obligatoria | Descripción |
|---|:---:|---|
| `MONGO_URL` | Sí | URI de MongoDB Atlas. Debe incluir el usuario de la base de datos. |
| `CLAVE` | Depende | Contraseña de MongoDB si no está escrita en la URI, o si allí se usa un marcador como `<CONTRASENA>`. |
| `DATABASE_NAME` | No | Nombre de la base de datos. Si se omite, la aplicación usa `Pedidos_y_productos`. |
| `JWT_SECRET` | Sí | Secreto para firmar y validar los JWT. FastAPI no arranca si falta. |
| `JWT_EXPIRE_MINUTES` | No | Duración del token en minutos; por defecto es `60`. Debe ser un entero positivo. |

Genera un secreto JWT desde PowerShell:

```powershell
.\virtual\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Copia el resultado como valor de `JWT_SECRET` en `techgear_api/.env`. No
compartas el valor ni lo escribas en el código. Usa las credenciales de MongoDB
Atlas y permite el acceso de red desde el entorno donde ejecutarás la
aplicación.

### 3. Configurar Django

Django lee sus variables del entorno del proceso. En local, `DEBUG` es `True`
por defecto y Django genera una clave de desarrollo si `DJANGO_SECRET_KEY` no
está definida. Para definir una clave en la terminal actual de PowerShell:

```powershell
$env:DJANGO_SECRET_KEY = (.\virtual\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))")
```

`API_URL` no es obligatoria en local: por defecto Django consulta
`http://127.0.0.1:8001`. Para apuntar a otra dirección, define esa variable en
la terminal donde ejecutarás Django.

## 🚀 Ejecutar los servidores

Necesitas **dos terminales** abiertas en la carpeta raíz. Mantén ambas
ejecutándose mientras pruebas el sitio.

**Terminal 1 — FastAPI, puerto 8001**

```powershell
Set-Location .\techgear_api
..\virtual\Scripts\python.exe -m uvicorn main:app --app-dir src --reload --host 127.0.0.1 --port 8001
```

La documentación interactiva de FastAPI estará en
[http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs).

**Terminal 2 — Django, puerto 8000**

```powershell
Set-Location ..
.\virtual\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Abre la tienda en [http://127.0.0.1:8000/](http://127.0.0.1:8000/).

## 👑 Crear el primer administrador

El formulario de registro no permite crear administradores. Con MongoDB y las
variables necesarias configuradas en `techgear_api/.env`, ejecuta desde la
raíz:

```powershell
.\virtual\Scripts\python.exe .\techgear_api\crear_admin.py
```

Escribe el nombre de usuario, correo y contraseña cuando el programa los pida.
La contraseña debe tener al menos 8 caracteres; el script la guarda como hash
bcrypt en MongoDB. Después, entra desde `/admin-ingresar/`.

## 🧪 Probar las funciones

1. Inicia FastAPI y Django con los comandos anteriores.
2. En `/registro/`, crea una cuenta de cliente. Al registrarse, el sitio inicia
   la sesión automáticamente.
3. Cierra sesión con el botón **Salir** y prueba el acceso desde `/ingresar/`
   usando el correo y la contraseña.
4. Crea el administrador con el script y entra por `/admin-ingresar/`.
5. Como administrador, abre el panel para crear, editar o eliminar productos.
6. Como cliente, selecciona un producto y crea un pedido. La API toma el ID del
   usuario del token, guarda el pedido y descuenta las unidades del inventario.
7. Para probar el vencimiento de sesión, configura `JWT_EXPIRE_MINUTES=1` en
   `techgear_api/.env`, reinicia FastAPI, inicia sesión y espera más de un
   minuto. Al hacer una operación protegida, la sesión se borra y el sitio pide
   iniciar sesión otra vez.

### 🖥️ Páginas principales del sitio

| Ruta | Uso |
|---|---|
| `/` | Inicio y productos disponibles. |
| `/productos/` | Catálogo público. |
| `/registro/` | Crear una cuenta de cliente. |
| `/ingresar/` | Iniciar sesión como cliente con correo y contraseña. |
| `/admin-ingresar/` | Iniciar sesión como administrador. |
| `/dashboard/` | Panel privado de administración de productos y pedidos. |
| `/salir/` | Cerrar la sesión mediante el formulario del sitio. |
| `/robots.txt` | Instrucciones básicas para rastreadores. |
| `/favicon.ico` | Redirige al favicon SVG del sitio. |

### 👥 Permisos

| Acción | Sin iniciar sesión | Cliente | Administrador |
|---|:---:|:---:|:---:|
| Ver inicio y catálogo | ✅ | ✅ | ✅ |
| Crear una cuenta de cliente | ✅ | — | — |
| Crear un pedido | ❌ | ✅ | ✅ |
| Ver pedidos | ❌ | Solo los propios | Todos |
| Crear, editar o eliminar productos en FastAPI | ❌ | ❌ | ✅ |
| Entrar al dashboard de la tienda | ❌ | ❌ | ✅ |

## 🌐 Rutas principales de la API

En local, las rutas se prueban en `http://127.0.0.1:8001`. Las operaciones
protegidas reciben el JWT en el encabezado de autorización de tipo Bearer.

| Método | Ruta | Acceso | Para qué sirve |
|---|---|---|---|
| `POST` | `/usuarios/registro` | Público | Registrar un cliente. El correo debe ser único. |
| `POST` | `/usuarios/login` | Público | Validar correo y contraseña y obtener un JWT. |
| `GET` | `/usuarios/me` | Con JWT | Consultar los datos del usuario del token. |
| `GET` | `/productos/` | Público | Listar productos. |
| `GET` | `/productos/{id}` | Público | Consultar un producto. |
| `POST` | `/productos/` | Administrador | Crear un producto. |
| `PUT` | `/productos/{id}` | Administrador | Editar un producto. |
| `DELETE` | `/productos/{id}` | Administrador | Eliminar un producto. |
| `POST` | `/pedidos/` | Con JWT | Crear un pedido para la cuenta del token. |
| `GET` | `/pedidos/` | Con JWT | Listar los pedidos permitidos para la cuenta. |
| `GET` | `/pedidos/{id}` | Con JWT | Consultar un pedido propio o, como administrador, cualquiera. |

FastAPI valida el token y devuelve `401` si falta, es inválido o expiró; las
operaciones de administrador rechazan a otros usuarios con `403`. Puedes
consultar ejemplos y esquemas desde `/docs` cuando FastAPI corre localmente.

## ✅ Pruebas automáticas

Ejecuta las pruebas de FastAPI desde la raíz:

```powershell
Set-Location .\techgear_api
..\virtual\Scripts\python.exe -m pytest
Set-Location ..
```

Ejecuta las pruebas y la revisión de Django desde la raíz:

```powershell
.\virtual\Scripts\python.exe manage.py test
.\virtual\Scripts\python.exe manage.py check
```

## ☁️ Despliegue en Vercel

La configuración actual de `vercel.json` declara dos servicios en un mismo
proyecto Vercel Services:

- **Django (`django`)** es el servicio público y recibe las rutas web.
- **FastAPI (`api`)** es un servicio privado al que Django llama mediante un
  binding. Vercel inyecta la URL de ese binding en `API_URL`.
- El entrypoint ASGI de la API es `src.main:app`, con raíz `techgear_api/`.
- El rewrite público actual envía las peticiones a Django. Por eso `/docs` y las
  rutas directas de la API **no están publicadas** en esta configuración. La
  documentación `/docs` sí está disponible al ejecutar FastAPI localmente.

Configura estas variables en el proyecto Vercel:

| Variable | Qué valor usar |
|---|---|
| `DJANGO_SECRET_KEY` | Genera un valor secreto nuevo para Django. Es obligatoria en producción; Django falla claramente si falta. |
| `JWT_SECRET` | Genera un secreto JWT con el comando de la sección de configuración. No reutilices una clave pública. |
| `MONGO_URL` | URI de conexión de MongoDB Atlas para el usuario y la base de datos del proyecto. |
| `CLAVE` | Configúrala si la URI de MongoDB necesita una contraseña separada o contiene un marcador de contraseña. |
| `DATABASE_NAME` | Opcional; nombre de la base de datos. Por defecto: `Pedidos_y_productos`. |
| `JWT_EXPIRE_MINUTES` | Opcional; minutos de validez del token. Por defecto: `60`. |

**No configures `API_URL` manualmente en Vercel**: la define el binding entre
Django y el servicio FastAPI. `DEBUG` también es `False` por defecto cuando
Vercel define `VERCEL=1`. `SESSION_COOKIE_SECURE` se activa automáticamente
cuando `DEBUG` es `False`.

No incluyas archivos `.env` ni secretos en Git. Después de configurar las
variables y los servicios en Vercel, revisa los logs de construcción y de
ejecución para confirmar que FastAPI se conecta a MongoDB y que Django alcanza
la API a través del binding.

## 🛠️ Notas y solución de problemas

- **FastAPI dice que falta `JWT_SECRET`:** revisa `techgear_api/.env` en local o
  la variable de entorno `JWT_SECRET` en Vercel.
- **FastAPI no se conecta a MongoDB:** confirma `MONGO_URL`, `CLAVE` si aplica,
  el nombre de la base de datos y la lista de acceso de red de Atlas.
- **Django no puede comunicarse con FastAPI en local:** confirma que FastAPI
  está activo en el puerto `8001`. Si usas otro puerto, configura `API_URL` para
  Django.
- **El token venció:** inicia sesión de nuevo. El JWT dura 60 minutos por
  defecto y su duración se puede cambiar con `JWT_EXPIRE_MINUTES`.
- **`/docs` no abre en Vercel:** la API está privada en la configuración
  actual; usa `/docs` localmente o revisa los logs de Vercel para diagnosticar
  el servicio.
- **Sesión y privacidad:** la cookie firmada ayuda a detectar modificaciones,
  pero no cifra su contenido. No guardes contraseñas ni otros datos sensibles
  en la sesión.

---

🎓 **Objetivo del taller:** practicar la integración de un frontend Django con
una API FastAPI, autenticación JWT, autorización por roles, persistencia en
MongoDB y despliegue de varios servicios.
