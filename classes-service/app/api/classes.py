from flask import Blueprint, request, jsonify, current_app
from pydantic import ValidationError
from datetime import datetime
from app.infraestructure.kafka_publisher import publish_event



from app.auth.keycloak import requires_roles
from app.infraestructure.db import SessionLocal
from app.infraestructure.repositories import create_class, list_classes, get_class, has_classes
from app.domain.schemas import ClassCreate, ClassRead
from app.infraestructure.trainers_client import (
    ensure_trainer_exists,
    list_trainers,
    TrainerNotFound,
    TrainersUnavailable,
)
from app.infraestructure.rabbitmq_publisher import (
    publish_notification,
    publish_rabbit_event,
)

bp = Blueprint("classes", __name__, url_prefix="/classes")


@bp.post("")
@requires_roles("ROLE_CLASSES_WRITE")
def create():
    """
    Crear clase
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - name
            - schedule
            - max_capacity
            - trainer_id
          properties:
            name:
              type: string
              example: Pilates
            schedule:
              type: string
              example: Miercoles 7am
            max_capacity:
              type: integer
              example: 18
            trainer_id:
              type: integer
              example: 1
    responses:
      201:
        description: Clase creada correctamente
      400:
        description: Error de negocio o entrenador no encontrado
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      422:
        description: Error de validación
      503:
        description: trainers-service no disponible
    """
    db = SessionLocal()
    try:
        data = request.get_json(silent=True) or {}
        payload = ClassCreate.model_validate(data)

        #auth_header = request.headers.get("Authorization")

        try:
          auth_header = request.headers.get("Authorization")
          ensure_trainer_exists(payload.trainer_id, auth_header=auth_header)

        except TrainerNotFound:
            return jsonify({"error": "trainer_not_found", "trainer_id": payload.trainer_id}), 400
        except TrainersUnavailable:
            return jsonify({"error": "trainers_unavailable"}), 503

        c = create_class(db, payload)

        out = ClassRead(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            max_capacity=c.max_capacity,
            trainer_id=c.trainer_id,
        )

        # RabbitMQ automático al crear clase
        try:
            rabbit_payload = {
                "tipo": "clase_creada",
                "classId": str(c.id),
                "className": c.name,
                "schedule": c.schedule,
                "trainerId": str(c.trainer_id),
            }
            publish_rabbit_event("clase.creada", rabbit_payload)
        except Exception as e:
            current_app.logger.warning(f"RabbitMQ publish failed (class created): {e}")

        # Kafka automático al crear clase (ocupación inicial)
        try:
            kafka_payload = {
                "classId": str(c.id),
                "className": c.name,
                "ocupacionActual": 0,
                "capacidadMaxima": c.max_capacity,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
            publish_event(kafka_payload, key=str(c.id))
        except Exception as e:
            current_app.logger.warning(f"Kafka publish failed (class created): {e}")

        return jsonify(out.model_dump()), 201

    except ValidationError as ve:
        db.rollback()
        return jsonify({"error": "validation_error", "details": ve.errors()}), 422
    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e)}), 400
    finally:
        db.close()


@bp.get("")
@requires_roles("ROLE_CLASSES_READ")
def list_all():
    """
    Listar clases
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Lista de clases
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    db = SessionLocal()
    try:
        classes = list_classes(db)
        out = [
            ClassRead(
                id=c.id,
                name=c.name,
                schedule=c.schedule,
                max_capacity=c.max_capacity,
                trainer_id=c.trainer_id,
            ).model_dump()
            for c in classes
        ]
        return jsonify(out), 200
    finally:
        db.close()


@bp.get("/<int:class_id>")
@requires_roles("ROLE_CLASSES_READ")
def get_one(class_id: int):
    """
    Obtener clase por ID
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    parameters:
      - in: path
        name: class_id
        type: integer
        required: true
        example: 1
    responses:
      200:
        description: Clase encontrada
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      404:
        description: Clase no encontrada
    """
    db = SessionLocal()
    try:
        c = get_class(db, class_id)
        if not c:
            return jsonify({"error": "class_not_found", "class_id": class_id}), 404

        out = ClassRead(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            max_capacity=c.max_capacity,
            trainer_id=c.trainer_id,
        )
        return jsonify(out.model_dump()), 200
    finally:
        db.close()


@bp.post("/seed")
@requires_roles("ROLE_CLASSES_WRITE")
def seed():
    """
    Sembrar clases de ejemplo
    ---
    tags:
      - Classes
    security:
      - bearerAuth: []
    produces:
      - application/json
    responses:
      200:
        description: Ya existían clases de ejemplo
      201:
        description: Clases sembradas correctamente
      400:
        description: No hay suficientes entrenadores para sembrar
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      503:
        description: trainers-service no disponible
    """
    db = SessionLocal()
    try:
        if has_classes(db):
            return jsonify({"status": "already_seeded"}), 200

        try:
            auth_header = request.headers.get("Authorization")
            trainers = list_trainers(auth_header=auth_header)
        except TrainersUnavailable:
            return jsonify({"error": "trainers_unavailable"}), 503

        trainer_ids = [t.get("id") for t in trainers if isinstance(t, dict) and t.get("id")]
        if len(trainer_ids) < 2:
            return jsonify({"error": "not_enough_trainers_to_seed"}), 400

        samples = [
            ClassCreate(name="Yoga Matutino", schedule="Lunes 8am", max_capacity=20, trainer_id=trainer_ids[0]),
            ClassCreate(name="Crossfit", schedule="Martes 6pm", max_capacity=15, trainer_id=trainer_ids[1]),
        ]

        created = []
        for s in samples:
          ensure_trainer_exists(s.trainer_id, auth_header=auth_header)
          c = create_class(db, s)

          created.append(
              ClassRead(
            id=c.id,
            name=c.name,
            schedule=c.schedule,
            max_capacity=c.max_capacity,
            trainer_id=c.trainer_id,
            ).model_dump()
          )
          try:
            kafka_payload = {
            "classId": str(c.id),
            "className": c.name,
            "ocupacionActual": 0,
            "capacidadMaxima": c.max_capacity,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            }   
            publish_event(kafka_payload, key=str(c.id))
          except Exception as e:
           current_app.logger.warning(f"Kafka publish failed (seed class {c.id}): {e}")
        

        return jsonify({"status": "seeded", "created": created}), 201

    except TrainerNotFound:
        return jsonify({"error": "trainer_not_found_during_seed"}), 400
    except TrainersUnavailable:
        return jsonify({"error": "trainers_unavailable"}), 503
    finally:
        db.close()


@bp.post("/rabbit/enroll-demo")
@requires_roles("ROLE_CLASSES_WRITE")
def rabbit_enroll_demo():
    """
    Demo RabbitMQ: nueva inscripción
    ---
    tags:
      - RabbitMQ Demo
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - memberId
            - classId
            - mensaje
          properties:
            memberId:
              type: string
              example: "1"
            classId:
              type: string
              example: "3"
            mensaje:
              type: string
              example: Nuevo miembro inscrito en Pilates
    responses:
      200:
        description: Evento de inscripción enviado a RabbitMQ
      400:
        description: Payload inválido
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    data = request.get_json(silent=True) or {}

    required = ["memberId", "classId", "mensaje"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "validation_error", "missing": missing}), 400

    payload = {
        "tipo": "nueva_inscripcion",
        "memberId": str(data["memberId"]),
        "classId": str(data["classId"]),
        "mensaje": data["mensaje"],
    }

    try:
        publish_rabbit_event("inscripcion.nueva", payload)
        return jsonify({
            "status": "published",
            "exchange": "gym.events.exchange",
            "routing_key": "inscripcion.nueva",
            "payload": payload,
        }), 200
    except Exception as e:
        current_app.logger.warning(f"RabbitMQ publish failed (enroll-demo): {e}")
        return jsonify({"error": "rabbitmq_publish_failed", "details": str(e)}), 503


@bp.post("/rabbit/schedule-demo")
@requires_roles("ROLE_CLASSES_WRITE")
def rabbit_schedule_demo():
    """
    Demo RabbitMQ: cambio de horario
    ---
    tags:
      - RabbitMQ Demo
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - classId
            - scheduleAnterior
            - scheduleNuevo
          properties:
            classId:
              type: string
              example: "3"
            scheduleAnterior:
              type: string
              example: Lunes 8am
            scheduleNuevo:
              type: string
              example: Martes 6pm
    responses:
      200:
        description: Evento de cambio de horario enviado a RabbitMQ
      400:
        description: Payload inválido
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    data = request.get_json(silent=True) or {}

    required = ["classId", "scheduleAnterior", "scheduleNuevo"]
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({"error": "validation_error", "missing": missing}), 400

    payload = {
        "tipo": "horario_cambiado",
        "classId": str(data["classId"]),
        "scheduleAnterior": data["scheduleAnterior"],
        "scheduleNuevo": data["scheduleNuevo"],
    }

    try:
        publish_rabbit_event("clase.horario.cambiado", payload)
        return jsonify({
            "status": "published",
            "exchange": "gym.events.exchange",
            "routing_key": "clase.horario.cambiado",
            "payload": payload,
        }), 200
    except Exception as e:
        current_app.logger.warning(f"RabbitMQ publish failed (schedule-demo): {e}")
        return jsonify({"error": "rabbitmq_publish_failed", "details": str(e)}), 503


@bp.post("/rabbit/payment-demo")
@requires_roles("ROLE_CLASSES_WRITE")
def rabbit_payment_demo():
    """
    Demo RabbitMQ: pago con posible fallo y DLQ
    ---
    tags:
      - RabbitMQ Demo
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - memberId
            - classId
            - amount
            - simulateFailure
          properties:
            memberId:
              type: string
              example: "1"
            classId:
              type: string
              example: "3"
            amount:
              type: integer
              example: 50000
            simulateFailure:
              type: boolean
              example: true
    responses:
      200:
        description: Evento de pago enviado a RabbitMQ
      400:
        description: Payload inválido
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
    """
    data = request.get_json(silent=True) or {}

    required = ["memberId", "classId", "amount", "simulateFailure"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "validation_error", "missing": missing}), 400

    payload = {
        "tipo": "pago_procesar",
        "memberId": str(data["memberId"]),
        "classId": str(data["classId"]),
        "amount": data["amount"],
        "simulateFailure": bool(data["simulateFailure"]),
    }

    try:
        publish_rabbit_event("pago.procesar", payload)
        return jsonify({
            "status": "published",
            "exchange": "gym.events.exchange",
            "routing_key": "pago.procesar",
            "payload": payload,
        }), 200
    except Exception as e:
        current_app.logger.warning(f"RabbitMQ publish failed (payment-demo): {e}")
        return jsonify({"error": "rabbitmq_publish_failed", "details": str(e)}), 503


@bp.post("/kafka/ocupacion-demo")
@requires_roles("ROLE_CLASSES_WRITE")
def kafka_ocupacion_demo():
    """
    Demo Kafka: actualización de ocupación de clase
    ---
    tags:
      - Kafka Demo
    security:
      - bearerAuth: []
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - classId
            - className
            - ocupacionActual
            - capacidadMaxima
          properties:
            classId:
              type: string
              example: "3"
            className:
              type: string
              example: Pilates
            ocupacionActual:
              type: integer
              example: 7
            capacidadMaxima:
              type: integer
              example: 18
    responses:
      200:
        description: Evento Kafka publicado correctamente
      400:
        description: Payload inválido
      401:
        description: Token ausente o inválido
      403:
        description: Sin rol suficiente
      503:
        description: Error al publicar en Kafka
    """
    data = request.get_json(silent=True) or {}

    required = ["classId", "className", "ocupacionActual", "capacidadMaxima"]
    missing = [f for f in required if f not in data]
    if missing:
        return jsonify({"error": "validation_error", "missing": missing}), 400

    payload = {
        "classId": str(data["classId"]),
        "className": data["className"],
        "ocupacionActual": int(data["ocupacionActual"]),
        "capacidadMaxima": int(data["capacidadMaxima"]),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    try:
        publish_event(payload, key=str(data["classId"]))
        return jsonify({
            "status": "published",
            "topic": "ocupacion-clases",
            "payload": payload,
        }), 200
    except Exception as e:
        current_app.logger.warning(f"Kafka publish failed (ocupacion-demo): {e}")
        return jsonify({"error": "kafka_publish_failed", "details": str(e)}), 503
    