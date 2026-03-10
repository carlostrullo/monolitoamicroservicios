from app.infraestructure.kafka_publisher import publish_event

if __name__ == "__main__":
    payload = {
        "usuarioId": "1",
        "mensaje": "Evento de prueba desde classes-service por Kafka"
    }
    publish_event(payload, key="test-1")
    print("Evento enviado a Kafka")