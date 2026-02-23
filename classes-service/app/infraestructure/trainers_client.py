import os
import requests

TRAINERS_BASE_URL = os.getenv("TRAINERS_BASE_URL", "http://localhost:8002")
HTTP_TIMEOUT_SECONDS = float(os.getenv("HTTP_TIMEOUT_SECONDS", "2"))


class TrainerNotFound(Exception):
    pass


class TrainersUnavailable(Exception):
    pass


def ensure_trainer_exists(trainer_id: int) -> None:
    """
    Decisión:
    - Si el trainer NO existe => error de negocio / request inválido (400 o 404).
    - Si el servicio de trainers NO responde / falla => 503 (dependencia caída).
    """
    try:
        r = requests.get(
            f"{TRAINERS_BASE_URL}/trainers/{trainer_id}",
            timeout=HTTP_TIMEOUT_SECONDS,
        )
    except requests.RequestException as e:
        raise TrainersUnavailable("trainers_service_unreachable") from e

    if r.status_code == 404:
        raise TrainerNotFound(f"trainer_id {trainer_id} not found")
    if r.status_code != 200:
        raise TrainersUnavailable(f"trainers_service_error status={r.status_code}")


def list_trainers() -> list[dict]:
    """Útil para /seed: trae entrenadores y saca IDs."""
    try:
        r = requests.get(f"{TRAINERS_BASE_URL}/trainers", timeout=HTTP_TIMEOUT_SECONDS)
    except requests.RequestException as e:
        raise TrainersUnavailable("trainers_service_unreachable") from e

    if r.status_code != 200:
        raise TrainersUnavailable(f"trainers_service_error status={r.status_code}")

    data = r.json()
    # Esperamos lista de dicts: [{"id":1,...}, ...]
    if not isinstance(data, list):
        raise TrainersUnavailable("unexpected_trainers_payload")
    return data