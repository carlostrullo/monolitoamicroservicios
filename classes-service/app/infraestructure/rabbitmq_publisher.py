import json
import os
import pika

# Publisher viejo
NOTIF_EXCHANGE = "notificacion.exchange"
NOTIF_QUEUE = "notificacion.queue"
NOTIF_ROUTING_KEY = "notificacion.routingkey"

# Publisher nuevo para el gym
GYM_EXCHANGE = "gym.events.exchange"


def _conn_params() -> pika.ConnectionParameters:
    host = os.getenv("RABBITMQ_HOST", "rabbitmq")
    port = int(os.getenv("RABBITMQ_PORT", "5672"))
    user = os.getenv("RABBITMQ_USERNAME", "guest")
    pwd = os.getenv("RABBITMQ_PASSWORD", "guest")
    credentials = pika.PlainCredentials(user, pwd)
    return pika.ConnectionParameters(
        host=host,
        port=port,
        credentials=credentials,
        heartbeat=30,
        blocked_connection_timeout=30,
        connection_attempts=5,
        retry_delay=2,
        socket_timeout=5,
    )


def publish_notification(usuario_id: str, mensaje: str) -> None:
    payload = {"usuarioId": str(usuario_id), "mensaje": mensaje}

    connection = pika.BlockingConnection(_conn_params())
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange=NOTIF_EXCHANGE, exchange_type="topic", durable=True)
        channel.queue_declare(queue=NOTIF_QUEUE, durable=True)
        channel.queue_bind(queue=NOTIF_QUEUE, exchange=NOTIF_EXCHANGE, routing_key=NOTIF_ROUTING_KEY)

        channel.basic_publish(
            exchange=NOTIF_EXCHANGE,
            routing_key=NOTIF_ROUTING_KEY,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()


def publish_rabbit_event(routing_key: str, payload: dict) -> None:
    connection = pika.BlockingConnection(_conn_params())
    try:
        channel = connection.channel()
        channel.exchange_declare(exchange=GYM_EXCHANGE, exchange_type="topic", durable=True)

        channel.basic_publish(
            exchange=GYM_EXCHANGE,
            routing_key=routing_key,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,
            ),
        )
    finally:
        connection.close()