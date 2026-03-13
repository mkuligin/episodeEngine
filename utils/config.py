from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


def _parse_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _get(env: dict[str, str], key: str, default: str) -> str:
    return env.get(key, default)


def _get_int(env: dict[str, str], key: str, default: int) -> int:
    value = env.get(key)
    if value is None:
        return default
    return int(value)


def _get_float(env: dict[str, str], key: str, default: float) -> float:
    value = env.get(key)
    if value is None:
        return default
    return float(value)


@dataclass(slots=True)
class ModelRoute:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


@dataclass(slots=True)
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    default_model: str
    extra_headers: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class AppConfig:
    app_name: str
    workspace_dir: Path
    storage_dir: Path
    log_dir: Path
    system_prompt_file: Path
    max_attempts: int
    router_mode: str
    primary_route: ModelRoute
    fallback_routes: list[ModelRoute]
    temperature: float
    max_tokens: int
    timeout_seconds: int
    providers: dict[str, ProviderConfig]


def normalize_provider(provider: str) -> str:
    cleaned = provider.strip().lower()
    if cleaned in {"z.ai", "zai", "glm"}:
        return "zai"
    return cleaned


def _parse_route(value: str) -> ModelRoute:
    provider, model = value.split(":", 1)
    return ModelRoute(provider=normalize_provider(provider), model=model.strip())


def _parse_fallbacks(value: str) -> list[ModelRoute]:
    routes: list[ModelRoute] = []
    for chunk in value.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        routes.append(_parse_route(chunk))
    return routes


def _build_provider_configs(env: dict[str, str]) -> dict[str, ProviderConfig]:
    return {
        "ollama": ProviderConfig(
            name="ollama",
            base_url=_get(env, "OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            api_key=_get(env, "OLLAMA_API_KEY", ""),
            default_model=_get(env, "OLLAMA_MODEL", "qwen2.5-coder:7b"),
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            base_url=_get(env, "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=_get(env, "OPENROUTER_API_KEY", ""),
            default_model=_get(env, "OPENROUTER_MODEL", "openai/gpt-4.1-mini"),
            extra_headers={
                "HTTP-Referer": _get(env, "OPENROUTER_HTTP_REFERER", ""),
                "X-Title": _get(env, "OPENROUTER_APP_TITLE", "episodeEngine"),
            },
        ),
        "zai": ProviderConfig(
            name="zai",
            base_url=_get(env, "ZAI_BASE_URL", "https://api.z.ai/api/paas/v4"),
            api_key=_get(env, "ZAI_API_KEY", ""),
            default_model=_get(env, "ZAI_MODEL", "glm-4.5-air"),
        ),
    }


def load_app_config(root: Path) -> AppConfig:
    env = _parse_env_file(root / ".env")
    providers = _build_provider_configs(env)

    primary_provider = normalize_provider(_get(env, "MODEL_PROVIDER", "ollama"))
    primary_model = _get(env, "MODEL_NAME", providers[primary_provider].default_model)
    primary_route = ModelRoute(provider=primary_provider, model=primary_model)

    fallback_value = env.get("MODEL_FALLBACKS", "")
    if fallback_value:
        fallback_routes = _parse_fallbacks(fallback_value)
    else:
        fallback_routes = [
            ModelRoute(provider=name, model=provider.default_model)
            for name, provider in providers.items()
            if name != primary_provider
        ]

    return AppConfig(
        app_name=_get(env, "APP_NAME", "episodeEngine"),
        workspace_dir=(root / _get(env, "WORKSPACE_DIR", ".")).resolve(),
        storage_dir=(root / _get(env, "STORAGE_DIR", "storage")).resolve(),
        log_dir=(root / _get(env, "LOG_DIR", "log")).resolve(),
        system_prompt_file=(root / _get(env, "SYSTEM_PROMPT_FILE", "system_prompt.md")).resolve(),
        max_attempts=_get_int(env, "MAX_ATTEMPTS", 8),
        router_mode=_get(env, "MODEL_MODE", "auto").strip().lower(),
        primary_route=primary_route,
        fallback_routes=fallback_routes,
        temperature=_get_float(env, "MODEL_TEMPERATURE", 0.0),
        max_tokens=_get_int(env, "MODEL_MAX_TOKENS", 1200),
        timeout_seconds=_get_int(env, "MODEL_TIMEOUT", 180),
        providers=providers,
    )
