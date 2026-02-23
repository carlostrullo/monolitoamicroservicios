# Sistema de Gestión de Gimnasio - Microservicios con DDD (Flask)

## Descripción

Este proyecto corresponde a la transformación de un **monolito** de gestión de gimnasio a una arquitectura de **microservicios**, aplicando principios de **Domain-Driven Design (DDD)**.

El sistema original (Spring Boot / Java) gestionaba:

- Miembros
- Clases
- Entrenadores
- Equipos

En esta solución se implementó una arquitectura de **4 microservicios independientes** en **Python + Flask**, manteniendo la funcionalidad base del monolito y agregando comunicación REST entre servicios.

---

## Justificación técnica (Python vs Java)

Aunque el proyecto base del curso está en Java/Spring Boot, esta implementación se realizó en **Python/Flask** para:

- reducir la curva de aprendizaje,
- minimizar riesgo de entrega,
- y enfocarse en lo que evalúa la rúbrica: **DDD, microservicios, segregación de responsabilidades, funcionalidad y demostración**.

> La arquitectura y los principios de diseño se mantienen; solo cambia la tecnología de implementación.

---

## Objetivo académico

Aplicar DDD para transformar un monolito en microservicios, definiendo:

- **Bounded Contexts**
- **Entidades / Agregados**
- **Repositorios**
- **Servicios**
- **Comunicación entre microservicios**

---

## Arquitectura propuesta (DDD + Microservicios)

### Bounded Contexts / Microservicios

1. **members-service**  
   Responsable de la gestión de miembros.

2. **trainers-service**  
   Responsable de la gestión de entrenadores.

3. **classes-service**  
   Responsable de la gestión de clases (programación).  
   Valida entrenadores por REST contra `trainers-service`.

4. **equipment-service**  
   Responsable de la gestión de inventario de equipos.

### Regla clave de arquitectura

Cada microservicio:

- tiene su **propia base de datos** (SQLite),
- expone sus **propios endpoints REST**,
- y se comunica con otros servicios por **IDs y contratos**, no por relaciones ORM compartidas.

---

## Estructura del proyecto

```text
.
├── members-service/
├── trainers-service/
├── classes-service/
├── equipment-service/
├── docs/
│   ├── arquitectura-componentes.puml
│
└── README.md
```
