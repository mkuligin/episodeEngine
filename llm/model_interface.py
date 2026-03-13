from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request

from utils.config import AppConfig, ModelRoute, normalize_provider

logger = logging.getLogger(__name__)


class TextModel(Protocol):
    def generate(self, prompt: str) -> str: ...


@dataclass(slots=True)
class ModelResponse:
    text: str
    provider: str
    model: str
    latency_seconds: float


class ModelProviderError(RuntimeError):
    pass


class OpenAICompatibleProvider:
    def __init__(
        self,
        name: str,
        base_url: str,
        api_key: str,
        timeout_seconds: int,
        temperature: float,
        max_tokens: int,
        extra_headers: dict[str, str] | None = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.extra_headers = extra_headers or {}

    def is_configured(self) -> bool:
        if self.name == "ollama":
            return bool(self.base_url)
        return bool(self.base_url and self.api_key)

    def generate(self, route: ModelRoute, system_prompt: str, prompt: str) -> ModelResponse:
        url = f"{self.base_url}/chat/completions"
        messages = []
        if system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": route.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        for key, value in self.extra_headers.items():
            if value:
                headers[key] = value

        logger.debug("Calling provider=%s model=%s url=%s", self.name, route.model, url)
        started = time.perf_counter()
        req = request.Request(url=url, data=data, headers=headers, method="POST")
        try:
            with request.urlopen(req, timeout=self.timeout_seconds) as response:
                body = json.loads(response.read().decode("utf-8"))
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise ModelProviderError(
                f"{self.name}:{route.model} HTTP {exc.code} {details[:400]}"
            ) from exc
        except error.URLError as exc:
            raise ModelProviderError(f"{self.name}:{route.model} unavailable: {exc}") from exc

        latency = time.perf_counter() - started
        text = self._extract_text(body)
        actual_model = str(body.get("model") or route.model)
        logger.debug(
            "Provider response provider=%s requested_model=%s actual_model=%s latency=%.2fs",
            self.name,
            route.model,
            actual_model,
            latency,
        )
        return ModelResponse(
            text=text,
            provider=self.name,
            model=actual_model,
            latency_seconds=latency,
        )

    def _extract_text(self, body: dict) -> str:
        choices = body.get("choices") or []
        if not choices:
            raise ModelProviderError(f"{self.name} returned no choices")
        message = choices[0].get("message") or {}
        content = message.get("content", "")
        if isinstance(content, list):
            parts = []
            for item in content:
                if isinstance(item, dict) and item.get("type") == "text":
                    parts.append(item.get("text", ""))
            return "\n".join(part for part in parts if part).strip()
        return str(content).strip()


class ModelRouter:
    def __init__(self, config: AppConfig, system_prompt: str):
        self.config = config
        self.system_prompt = system_prompt
        self.mode = config.router_mode
        self.manual_route = config.primary_route
        self.providers = {
            name: OpenAICompatibleProvider(
                name=provider.name,
                base_url=provider.base_url,
                api_key=provider.api_key,
                timeout_seconds=config.timeout_seconds,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                extra_headers=provider.extra_headers,
            )
            for name, provider in config.providers.items()
        }

    def generate(self, prompt: str) -> str:
        errors: list[str] = []
        for route in self._candidate_routes():
            provider = self.providers.get(route.provider)
            if provider is None:
                message = f"Unknown provider {route.provider}"
                errors.append(message)
                logger.warning(message)
                continue
            if not provider.is_configured():
                message = f"Provider {route.provider} is not configured"
                errors.append(message)
                logger.warning(message)
                continue
            try:
                response = provider.generate(route, self.system_prompt, prompt)
                self.manual_route = ModelRoute(provider=response.provider, model=response.model)
                return response.text
            except ModelProviderError as exc:
                message = str(exc)
                errors.append(message)
                logger.warning("Route failed: %s", message)
                if self.mode == "manual":
                    break
        raise RuntimeError("All model routes failed: " + " | ".join(errors or ["No configured model routes available"]))

    def set_mode(self, mode: str) -> None:
        normalized = mode.strip().lower()
        if normalized not in {"auto", "manual"}:
            raise ValueError("mode must be auto or manual")
        self.mode = normalized
        logger.info("Router mode changed to %s", self.mode)

    def set_manual_route(self, provider: str, model: str) -> None:
        self.manual_route = ModelRoute(provider=normalize_provider(provider), model=model.strip())
        self.mode = "manual"
        logger.info("Manual route selected: %s", self.manual_route.label)

    def describe_routes(self) -> list[dict[str, str]]:
        routes = [self.config.primary_route, *self.config.fallback_routes]
        seen: set[str] = set()
        described: list[dict[str, str]] = []
        for route in routes:
            key = route.label
            if key in seen:
                continue
            seen.add(key)
            provider = self.providers.get(route.provider)
            described.append(
                {
                    "provider": route.provider,
                    "model": route.model,
                    "configured": "yes" if provider and provider.is_configured() else "no",
                    "active": "yes" if route.label == self.active_route_label else "",
                }
            )
        return described

    @property
    def active_route_label(self) -> str:
        return self.manual_route.label

    def _candidate_routes(self) -> list[ModelRoute]:
        if self.mode == "manual":
            return [self.manual_route]
        routes = [self.config.primary_route, *self.config.fallback_routes]
        unique: list[ModelRoute] = []
        seen: set[str] = set()
        for route in routes:
            key = route.label
            if key in seen:
                continue
            seen.add(key)
            unique.append(route)
        return unique


def build_model(config: AppConfig, system_prompt: str) -> ModelRouter:
    return ModelRouter(config=config, system_prompt=system_prompt)
