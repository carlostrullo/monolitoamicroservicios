import json
import os
import time
import pika

EXCHANGE = "notificacion.exchange"
QUEUE = "notificacion.queue"
ROUTING_KEY = "notificacion.routingkey"


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


def enviar_notificacion(dto: dict):
    print(f"[NOTIFICACION] usuarioId={dto.get('usuarioId')} mensaje={dto.get('mensaje')}")


def main():
    while True:
        try:
            print("[notifications-service] intentando conectar a RabbitMQ...")
            connection = get_connection()
            channel = connection.channel()

            channel.exchange_declare(
                exchange=EXCHANGE,
                exchange_type="topic",
                durable=True
            )
            channel.queue_declare(queue=QUEUE, durable=True)
            channel.queue_bind(
                queue=QUEUE,
                exchange=EXCHANGE,
                routing_key=ROUTING_KEY
            )

            channel.basic_qos(prefetch_count=10)

            def callback(ch, method, properties, body):
                try:
                    dto = json.loads(body.decode("utf-8"))
                    enviar_notificacion(dto)
                    ch.basic_ack(delivery_tag=method.delivery_tag)
                except Exception as e:
                    print(f"[ERROR] procesando mensaje: {e}")
                    ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

            channel.basic_consume(
                queue=QUEUE,
                on_message_callback=callback,
                auto_ack=False
            )

            print("[notifications-service] esperando mensajes...")
            channel.start_consuming()

        except Exception as e:
            print(f"[notifications-service] error: {e}")
            print("[notifications-service] reintentando en 5 segundos...")
            time.sleep(5)


if __name__ == "__main__":
    main()