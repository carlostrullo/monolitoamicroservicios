from collections.abc import Mapping, Sequence
from threading import Lock


class ServiceRegistry:
    def __init__(self, services: Mapping[str, Sequence[str]]):
        self._services: dict[str, list[str]] = {}
        self._indexes: dict[str, int] = {}
        self._locks: dict[str, Lock] = {}

        for service_name, urls in services.items():
            cleaned_urls = [url.rstrip("/") for url in urls if url]
            if not cleaned_urls:
                raise ValueError(f"Service '{service_name}' does not have configured URLs")

            self._services[service_name] = cleaned_urls
            self._indexes[service_name] = 0
            self._locks[service_name] = Lock()

    def get_next_base_url(self, service_name: str) -> str:
        urls = self._services.get(service_name)
        if not urls:
            raise KeyError(f"Service '{service_name}' is not registered")

        lock = self._locks[service_name]
        with lock:
            index = self._indexes[service_name]
            base_url = urls[index % len(urls)]
            self._indexes[service_name] = (index + 1) % len(urls)

        return base_url

    def build_url(self, service_name: str, resource_path: str) -> str:
        normalized_path = resource_path if resource_path.startswith("/") else f"/{resource_path}"
        return f"{self.get_next_base_url(service_name)}{normalized_path}"
