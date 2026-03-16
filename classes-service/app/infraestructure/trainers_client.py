import os
import requests


class TrainerNotFound(Exception):
    pass


class TrainersUnavailable(Exception):
    pass


def _base_url() -> str:
    return os.getenv("TRAINERS_BASE_URL", "http://localhost:8002").rstrip("/")


def _timeout() -> float:
    try:
        return float(os.getenv("REQUEST_TIMEOUT_SECONDS", "2"))
    except Exception:
        return 2.0


def _headers(auth_header: str | None = None) -> dict:
    headers = {}
    if auth_header:
        headers["Authorization"] = auth_header
    return headers


def ensure_trainer_exists(trainer_id: int, auth_header: str | None = None) -> None:
    url = f"{_base_url()}/trainers/{trainer_id}"

    try:
        resp = requests.get(
            url,
            headers=_headers(auth_header),
            timeout=_timeout(),
        )
    except requests.RequestException as e:
        raise TrainersUnavailable(str(e))

    if resp.status_code == 200:
        return

    if resp.status_code == 404:
        raise TrainerNotFound()

    # 401 / 403 / 5xx / otros
    raise TrainersUnavailable(f"trainers-service returned {resp.status_code}")


def list_trainers(auth_header: str | None = None) -> list[dict]:
    url = f"{_base_url()}/trainers"

    try:
        resp = requests.get(
            url,
            headers=_headers(auth_header),
            timeout=_timeout(),
        )
    except requests.RequestException as e:
        raise TrainersUnavailable(str(e))

    if resp.status_code == 200:
        return resp.json()

    raise TrainersUnavailable(f"trainers-service returned {resp.status_code}")