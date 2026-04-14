# Sistema de Gestion de Gimnasio - Microservicios Python

## Descripcion

Este repositorio implementa la evolucion de un monolito de gimnasio hacia una arquitectura de microservicios en Python.

La solucion actual incluye:

- microservicios HTTP con Flask
- un `api-gateway` en FastAPI
- autenticacion y autorizacion con Keycloak y JWT
- documentacion Swagger/OpenAPI
- eventos asincronos con RabbitMQ
- eventos de ocupacion con Kafka
- orquestacion completa con Docker Compose

El objetivo academico es demostrar bounded contexts, separacion de responsabilidades, comunicacion entre servicios y una capa de entrada centralizada con el patron API Gateway.

## Arquitectura actual

### Servicios de negocio

- `members-service`: gestion de miembros
- `trainers-service`: gestion de entrenadores
- `classes-service`: gestion de clases, validacion REST contra entrenadores y publicacion de eventos RabbitMQ y Kafka
- `equipment-service`: gestion de inventario de equipos

### Servicios de integracion

- `api-gateway`: punto unico de entrada, seguridad centralizada, routing, proxy, agregacion y balanceo simple
- `notifications-service`: consumidor RabbitMQ para eventos del gimnasio
- `kafka-service`: consumidor Kafka para eventos de ocupacion de clases

### Infraestructura

- `keycloak`: proveedor de identidad y emisor de JWT
- `rabbitmq`: broker de mensajeria asincrona
- `kafka`: broker de eventos

## Que se implemento

### 1. Microservicios HTTP con Flask

Cada servicio HTTP mantiene su propia base de datos SQLite, su propia documentacion y sus propias rutas:

- `members-service`
- `trainers-service`
- `classes-service`
- `equipment-service`

Todos exponen al menos:

- `GET /health`
- rutas REST de negocio
- Swagger en `/docs/swagger/`

### 2. Seguridad con Keycloak

Los microservicios y el gateway validan JWT usando:

- `Authorization: Bearer <token>`
- verificacion por `issuer`
- descarga de JWKS desde Keycloak
- validacion de firma y expiracion
- validacion opcional de audiencia
- lectura de roles desde `realm_access` y `resource_access`

### 3. API Gateway en FastAPI

Se agrego un nuevo servicio `api-gateway/` para centralizar el acceso al sistema.

Responsabilidades del gateway:

- exponer un punto unico de entrada
- proteger rutas con JWT antes de reenviarlas
- reenviar metodo, query params, body y headers relevantes
- conservar el header `Authorization`
- mapear rutas externas hacia microservicios internos
- implementar balanceo simple por round robin
- agregar respuestas de multiples servicios

### 4. Registro interno de servicios en Python

En el taller original se planteaba Eureka. En esta implementacion no se agrego Eureka porque el stack real del proyecto es Python + Docker Compose, no Spring Cloud.

En su lugar se implemento un equivalente simple y defendible:

- cada servicio se identifica por un nombre logico
- sus URLs reales se leen desde variables de entorno
- se soportan una o varias URLs por servicio
- el gateway rota entre instancias con round robin basico

Ejemplo:

```env
MEMBERS_SERVICE_URLS=http://members-service:8001
TRAINERS_SERVICE_URLS=http://trainers-service:8002
CLASSES_SERVICE_URLS=http://classes-service:8003
EQUIPMENT_SERVICE_URLS=http://equipment-service:8004
```

Si en el futuro existe mas de una instancia, basta con separarlas por comas:

```env
MEMBERS_SERVICE_URLS=http://members-service-1:8001,http://members-service-2:8001
```

### 5. Agregacion de respuestas

El gateway expone:

- `GET /api/dashboard/summary`

Este endpoint consulta en paralelo los servicios de miembros, entrenadores, clases y equipos para devolver:

- totales por entidad
- una vista corta de clases
- una vista corta de entrenadores

### 6. Mensajeria y eventos

#### RabbitMQ

`classes-service` publica eventos al exchange `gym.events.exchange`.

Eventos manejados:

- `clase.creada`
- `inscripcion.nueva`
- `clase.horario.cambiado`
- `pago.procesar`

`notifications-service` consume esos mensajes y tambien maneja una DLQ para pagos fallidos.

#### Kafka

`classes-service` publica eventos de ocupacion en el topic:

- `ocupacion-clases`

`kafka-service` consume esos eventos y los muestra por consola.

## Flujo de una peticion

Cuando un cliente hace una peticion al sistema:

1. La peticion entra por `api-gateway`.
2. FastAPI recibe la solicitud en `app/main.py`.
3. El middleware del gateway valida el JWT en `app/security.py`.
4. Si el token es invalido, el gateway responde `401`.
5. Si el token es valido, la ruta se mapea al servicio correcto.
6. `app/registry.py` resuelve la URL destino usando configuracion y round robin.
7. `app/proxy.py` reenvia la peticion al microservicio interno.
8. El microservicio procesa la solicitud y responde.
9. El gateway devuelve la respuesta al cliente.

Para el caso de `/api/dashboard/summary`, el gateway no solo reenvia: consulta varios servicios y arma una respuesta agregada propia.

## Estructura del proyecto

```text
.
|-- api-gateway/
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- app/
|       |-- __init__.py
|       |-- aggregator.py
|       |-- config.py
|       |-- main.py
|       |-- proxy.py
|       |-- registry.py
|       `-- security.py
|-- members-service/
|-- trainers-service/
|-- classes-service/
|-- equipment-service/
|-- notifications-service/
|-- kafka-service/
|-- docs/
|   |-- arquitectura-componentes.puml
|   `-- arquitectura-componentes.png
|-- docker-compose.yml
`-- README.md
```

## Puertos principales

| Componente | Puerto |
|---|---:|
| api-gateway | `8080` |
| keycloak | `8090` |
| members-service | `8001` |
| trainers-service | `8002` |
| classes-service | `8003` |
| equipment-service | `8004` |
| rabbitmq | `5672` |
| rabbitmq management | `15672` |
| kafka externo | `29092` |

## Requisitos para correr el repositorio

Antes de clonar y ejecutar, asegurate de tener instalado:

- Git
- Docker Desktop o Docker Engine + Docker Compose
- PowerShell o una terminal equivalente

## Como correr el proyecto despues de clonar

### 1. Clonar el repositorio

```powershell
git clone <URL_DEL_REPOSITORIO>
cd "monolito a microservicios"
```

### 2. Levantar todos los servicios

```powershell
docker compose up -d --build
docker compose ps
```

Si quieres reiniciar todo desde cero, incluyendo volumenes:

```powershell
docker compose down -v
docker compose up -d --build
```

### 3. Esperar a que Keycloak este listo

```powershell
do {
  Start-Sleep -Seconds 5
  try {
    $resp = Invoke-WebRequest -UseBasicParsing http://localhost:8090/health/ready
    $ready = $resp.StatusCode -eq 200
  } catch {
    $ready = $false
  }
} until ($ready)

"Keycloak listo"
```

### 4. Crear realm, cliente, usuario demo y roles en Keycloak

El repositorio no importa automaticamente un realm. Por eso, despues del primer arranque, ejecuta este bloque en PowerShell.

```powershell
$ErrorActionPreference = "Stop"

$REALM = "gimnasio"
$CLIENT_ID = "gym-api-client"
$DEMO_USER = "demo.gateway"
$DEMO_PASS = "Demo123!"
$ROLES = @(
  "ROLE_MEMBERS_READ","ROLE_MEMBERS_WRITE",
  "ROLE_TRAINERS_READ","ROLE_TRAINERS_WRITE",
  "ROLE_CLASSES_READ","ROLE_CLASSES_WRITE",
  "ROLE_EQUIPMENT_READ","ROLE_EQUIPMENT_WRITE"
)

docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials --server http://localhost:8080 --realm master --user admin --password admin | Out-Null

docker exec keycloak /opt/keycloak/bin/kcadm.sh get "realms/$REALM" 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
  docker exec keycloak /opt/keycloak/bin/kcadm.sh create realms -s "realm=$REALM" -s "enabled=true" | Out-Null
}

foreach ($role in $ROLES) {
  $existingRole = docker exec keycloak /opt/keycloak/bin/kcadm.sh get roles -r $REALM -q search=$role | ConvertFrom-Json
  if (-not ($existingRole | Where-Object { $_.name -eq $role })) {
    docker exec keycloak /opt/keycloak/bin/kcadm.sh create roles -r $REALM -s "name=$role" | Out-Null
  }
}

$client = docker exec keycloak /opt/keycloak/bin/kcadm.sh get clients -r $REALM -q clientId=$CLIENT_ID | ConvertFrom-Json
if (-not $client) {
  docker exec keycloak /opt/keycloak/bin/kcadm.sh create clients -r $REALM `
    -s "clientId=$CLIENT_ID" `
    -s "enabled=true" `
    -s "publicClient=true" `
    -s "directAccessGrantsEnabled=true" `
    -s "standardFlowEnabled=false" `
    -s "serviceAccountsEnabled=false" | Out-Null
}

$user = docker exec keycloak /opt/keycloak/bin/kcadm.sh get users -r $REALM -q username=$DEMO_USER | ConvertFrom-Json
if (-not $user) {
  docker exec keycloak /opt/keycloak/bin/kcadm.sh create users -r $REALM -s "username=$DEMO_USER" -s "enabled=true" | Out-Null
}

docker exec keycloak /opt/keycloak/bin/kcadm.sh set-password -r $REALM --username $DEMO_USER --new-password $DEMO_PASS | Out-Null

foreach ($role in $ROLES) {
  docker exec keycloak /opt/keycloak/bin/kcadm.sh add-roles -r $REALM --uusername $DEMO_USER --rolename $role 2>$null | Out-Null
}

"Realm, cliente, usuario y roles listos"
```

### 5. Obtener un token JWT

```powershell
$TOKEN = (
  Invoke-RestMethod -Method POST `
    -Uri "http://localhost:8090/realms/gimnasio/protocol/openid-connect/token" `
    -ContentType "application/x-www-form-urlencoded" `
    -Body @{
      client_id  = "gym-api-client"
      grant_type = "password"
      username   = "demo.gateway"
      password   = "Demo123!"
    }
).access_token

$AUTH = @{ Authorization = "Bearer $TOKEN" }
```

### 6. Sembrar datos de ejemplo

Hazlo en este orden para que `classes-service` pueda validar entrenadores existentes.

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/trainers/seed" -Headers $AUTH
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/members/seed" -Headers $AUTH
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/equipment/seed" -Headers $AUTH
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/classes/seed" -Headers $AUTH
```

## Endpoints principales

### Gateway

- `GET /health`
- `GET /docs`
- `GET /openapi.json`
- `GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD /api/members[/...]`
- `GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD /api/trainers[/...]`
- `GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD /api/classes[/...]`
- `GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD /api/equipment[/...]`
- `GET /api/dashboard/summary`

### Servicios HTTP directos

- members: `http://localhost:8001/docs/swagger/`
- trainers: `http://localhost:8002/docs/swagger/`
- classes: `http://localhost:8003/docs/swagger/`
- equipment: `http://localhost:8004/docs/swagger/`

## Comandos de demo

### Validar salud

```powershell
curl.exe http://localhost:8080/health
```

### Validar proteccion sin token

```powershell
curl.exe -i http://localhost:8080/api/classes
curl.exe -i http://localhost:8080/api/members
```

### Probar rutas protegidas con token

```powershell
curl.exe -i -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/classes
curl.exe -i -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/members
curl.exe -i -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/trainers
curl.exe -i -H "Authorization: Bearer $TOKEN" http://localhost:8080/api/equipment
```

### Probar agregacion del gateway

```powershell
Invoke-RestMethod -Method GET -Uri "http://localhost:8080/api/dashboard/summary" -Headers $AUTH | ConvertTo-Json -Depth 6
```

### Ver consumidores de RabbitMQ y Kafka

En una terminal aparte:

```powershell
docker compose logs -f notifications-service
```

```powershell
docker compose logs -f kafka-service
```

Luego puedes disparar eventos a traves del gateway:

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/classes/rabbit/enroll-demo" -Headers $AUTH -ContentType "application/json" -Body '{"memberId":"1","classId":"1","mensaje":"Nuevo miembro inscrito en Pilates"}'
```

```powershell
Invoke-RestMethod -Method POST -Uri "http://localhost:8080/api/classes/kafka/ocupacion-demo" -Headers $AUTH -ContentType "application/json" -Body '{"classId":"1","className":"Pilates","ocupacionActual":7,"capacidadMaxima":18}'
```

## Credenciales de referencia

- Keycloak admin: `admin / admin`
- Realm demo: `gimnasio`
- Client demo: `gym-api-client`
- Usuario demo: `demo.gateway / Demo123!`

## Documentacion util

- Gateway docs: `http://localhost:8080/docs`
- Keycloak: `http://localhost:8090`
- RabbitMQ management: `http://localhost:15672`

## Notas finales

- El gateway protege todo excepto `/health`, `/docs` y `/openapi.json`.
- El header `Authorization` se reenvia a los microservicios internos.
- La validacion JWT sigue la misma idea en gateway y microservicios para mantener coherencia.
- La solucion evita introducir Eureka porque el proyecto esta construido en Python y Docker Compose; se reemplazo por un registro interno por configuracion y round robin, suficiente para este contexto.
