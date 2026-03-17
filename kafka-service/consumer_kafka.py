import json
import os
import time
from kafka import KafkaConsumer


def main():
    bootstrap = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:9092")
    topic = os.getenv("KAFKA_TOPIC_GYM_EVENTS", "ocupacion-clases")
    group_id = os.getenv("KAFKA_CONSUMER_GROUP", "ocupacion-monitor-v1")

    while True:
        try:
            print("[kafka-service] iniciando consumer Kafka...")
            print(f"[kafka-service] bootstrap={bootstrap}")
            print(f"[kafka-service] topic={topic}")
            print(f"[kafka-service] group_id={group_id}")

            consumer = KafkaConsumer(
                topic,
                bootstrap_servers=bootstrap,
                group_id=group_id,
                auto_offset_reset="earliest",
                enable_auto_commit=True,
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
            )

            print(f"[kafka-service] escuchando topic '{topic}' ...")

            for message in consumer:
                payload = message.value
                print(
                    f"[KAFKA][OCUPACION] classId={payload.get('classId')} "
                    f"className={payload.get('className')} "
                    f"ocupacion={payload.get('ocupacionActual')}/{payload.get('capacidadMaxima')} "
                    f"timestamp={payload.get('timestamp')}"
                )

        except Exception as e:
            print(f"[kafka-service] error: {e}")
            print("[kafka-service] reintentando en 5 segundos...")
            time.sleep(5)


if __name__ == "__main__":
    main()