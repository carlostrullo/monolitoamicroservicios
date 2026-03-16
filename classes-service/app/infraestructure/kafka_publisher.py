import json
import os
from kafka import KafkaProducer


def _get_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092"),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        key_serializer=lambda k: k.encode("utf-8") if k else None,
    )


def publish_event(payload: dict, key: str | None = None) -> None:
    topic = os.getenv("KAFKA_TOPIC_GYM_EVENTS", "ocupacion-clases")
    producer = _get_producer()
    try:
        future = producer.send(topic, key=key, value=payload)
        future.get(timeout=10)
        producer.flush()
    finally:
        producer.close()