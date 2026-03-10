import json
import os
import pika

EXCHANGE = "notificacion.exchange"
QUEUE = "notificacion.queue"
ROUTING_KEY = "notificacion.routingkey"

def _conn_params() -> pika.ConnectionParameters:
    host = os.getenv("RABBITMQ_HOST", "localhost")
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
    )

def publish_notification(usuario_id: str, mensaje: str) -> None:
    payload = {"usuarioId": str(usuario_id), "mensaje": mensaje}  # NotificacionDTO

    connection = pika.BlockingConnection(_conn_params())
    try:
        channel = connection.channel()

        # Equivalente a: Queue + TopicExchange + Binding (durables)
        channel.exchange_declare(exchange=EXCHANGE, exchange_type="topic", durable=True)
        channel.queue_declare(queue=QUEUE, durable=True)
        channel.queue_bind(queue=QUEUE, exchange=EXCHANGE, routing_key=ROUTING_KEY)

        channel.basic_publish(
            exchange=EXCHANGE,
            routing_key=ROUTING_KEY,
            body=json.dumps(payload).encode("utf-8"),
            properties=pika.BasicProperties(
                content_type="application/json",
                delivery_mode=2,  # persistente
            ),
        )
    finally:
        connection.close()