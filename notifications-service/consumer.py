import json
import os
import time
import pika

EXCHANGE = "gym.events.exchange"

CLASES_QUEUE = "clases.queue"
CLASES_ROUTING_KEY = "clase.creada"

INSCRIPCIONES_QUEUE = "inscripciones.queue"
INSCRIPCIONES_ROUTING_KEY = "inscripcion.nueva"

HORARIOS_QUEUE = "horarios.queue"
HORARIOS_ROUTING_KEY = "clase.horario.cambiado"

PAGOS_QUEUE = "pagos-queue"
PAGOS_ROUTING_KEY = "pago.procesar"
PAGOS_DLQ = "pagos-dlq"


def get_connection():
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USERNAME", "guest")
    password = os.getenv("RABBITMQ_PASSWORD", "guest")

    credentials = pika.PlainCredentials(user, password)

    params = pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=5,
        retry_delay=2,
        socket_timeout=5,
    )
    return pika.BlockingConnection(params)


def handle_clase_creada(payload: dict):
    print(
        f"[RABBITMQ][CLASE_CREADA] classId={payload.get('classId')} "
        f"className={payload.get('className')} "
        f"schedule={payload.get('schedule')} "
        f"trainerId={payload.get('trainerId')}"
    )


def handle_inscripcion(payload: dict):
    print(
        f"[RABBITMQ][INSCRIPCION] memberId={payload.get('memberId')} "
        f"classId={payload.get('classId')} mensaje={payload.get('mensaje')}"
    )


def handle_horario(payload: dict):
    print(
        f"[RABBITMQ][HORARIO] classId={payload.get('classId')} "
        f"anterior={payload.get('scheduleAnterior')} "
        f"nuevo={payload.get('scheduleNuevo')}"
    )


def handle_pago(payload: dict):
    print(
        f"[RABBITMQ][PAGO] memberId={payload.get('memberId')} "
        f"classId={payload.get('classId')} amount={payload.get('amount')}"
    )

    if payload.get("simulateFailure", False):
        raise Exception("Pago fallido simulado")


def setup_rabbitmq(channel):
    channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)

    channel.queue_declare(queue=CLASES_QUEUE, durable=True)
    channel.queue_bind(
        queue=CLASES_QUEUE,
        exchange=EXCHANGE,
        routing_key=CLASES_ROUTING_KEY
    )

    channel.queue_declare(queue=INSCRIPCIONES_QUEUE, durable=True)
    channel.queue_bind(
        queue=INSCRIPCIONES_QUEUE,
        exchange=EXCHANGE,
        routing_key=INSCRIPCIONES_ROUTING_KEY
    )

    channel.queue_declare(queue=HORARIOS_QUEUE, durable=True)
    channel.queue_bind(
        queue=HORARIOS_QUEUE,
        exchange=EXCHANGE,
        routing_key=HORARIOS_ROUTING_KEY
    )

    channel.queue_declare(queue=PAGOS_DLQ, durable=True)
    channel.queue_declare(
        queue=PAGOS_QUEUE,
        durable=True,
        arguments={
            "x-dead-letter-exchange": "",
            "x-dead-letter-routing-key": PAGOS_DLQ,
            "x-message-ttl": 30000,
        },
    )
    channel.queue_bind(
        queue=PAGOS_QUEUE,
        exchange=EXCHANGE,
        routing_key=PAGOS_ROUTING_KEY
    )


def main():
    while True:
        try:
            print("[notifications-service][rabbit] intentando conectar a RabbitMQ...")
            connection = get_connection()
            channel = connection.channel()

            setup_rabbitmq(channel)
            channel.basic_qos(prefetch_count=10)

            def callback_clase(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handle_clase_creada(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ERROR][CLASE_CREADA] {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            def callback_inscripcion(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handle_inscripcion(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ERROR][INSCRIPCION] {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            def callback_horario(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handle_horario(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ERROR][HORARIO] {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            def callback_pago(ch, method, properties, body):
                try:
                    payload = json.loads(body.decode("utf-8"))
                    handle_pago(payload)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ERROR][PAGO -> DLQ] {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            channel.basic_consume(
                queue=CLASES_QUEUE,
                on_message_callback=callback_clase,
                auto_ack=False,
            )
            channel.basic_consume(
                queue=INSCRIPCIONES_QUEUE,
                on_message_callback=callback_inscripcion,
                auto_ack=False,
            )
            channel.basic_consume(
                queue=HORARIOS_QUEUE,
                on_message_callback=callback_horario,
                auto_ack=False,
            )
            channel.basic_consume(
                queue=PAGOS_QUEUE,
                on_message_callback=callback_pago,
                auto_ack=False,
            )

            print("[notifications-service][rabbit] esperando mensajes...")
            channel.start_consuming()

        except Exception as e:
            print(f"[notifications-service][rabbit] error: {e}")
            print("[notifications-service][rabbit] reintentando en 5 segundos...")
            time.sleep(5)


if __name__ == "__main__":
    main()