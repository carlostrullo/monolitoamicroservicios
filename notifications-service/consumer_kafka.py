import json
import os
from kafka import KafkaConsumer

def main():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
    topic = os.getenv("KAFKA_TOPIC_GYM_EVENTS", "gym-events")
    group_id = os.getenv("KAFKA_CONSUMER_GROUP", "notifications-group")

    consumer = KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap,
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=True,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    )

    print(f"[notifications-service] escuchando topic '{topic}' en {bootstrap} ...")

    for message in consumer:
        payload = message.value
        print(
            f"[KAFKA] Notificación recibida para usuarioId={payload.get('usuarioId')}: "
            f"{payload.get('mensaje')}"
        )

if __name__ == "__main__":
    main()