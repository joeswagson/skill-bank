import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, Optional
import providers


@dataclass
class OpenAIConfig:
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    timeout: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnthropicConfig:
    base_url: str = "https://api.anthropic.com"
    api_key: str = ""
    model: str = "claude-3-5-sonnet-latest"
    temperature: float = 1.0
    max_tokens: int = 4096
    timeout: int = 60

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OllamaConfig:
    base_url: str = "http://localhost:11434"
    # api_key: Optional[str] = None
    model: str = "llama3.2"
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    timeout: int = 60
    keep_alive: str = "5m"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvidersConfig:
    primary: str = field(default_factory=lambda: "openai")

    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "primary": self.primary,

            "openai": self.openai.to_dict(),
            "anthropic": self.anthropic.to_dict(),
            "ollama": self.ollama.to_dict()
        }


@dataclass
class Config:
    CONFIG_FILE = Path("config.json")
    providers: ProvidersConfig = field(default_factory=ProvidersConfig)

    def __post_init__(self):
        """Load from file if exists, otherwise create default."""
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text())
                _update_from_dict(self, data.get("providers", {}))
            except Exception as e:
                print(f"Warning loading config: {e}")
        else:
            self._save_to_file()

    def _save_to_file(self, path: Path = None) -> None:
        """Internal save method."""
        path = path or self.CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {"providers": self.providers.to_dict()}
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)


def _update_from_dict(config_obj: Config, provider_data: Dict) -> None:
    """Update config from loaded dictionary."""
    for name in providers.PROVIDERS.keys():
        if name in provider_data:
            obj = getattr(config_obj.providers, name)
            for key, value in provider_data[name].items():
                if hasattr(obj, key):
                    setattr(obj, key, value)


# Singleton instance (created on first access with auto-save of defaults)
_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()  # __post_init__ creates default file automatically
    return _config


def save_config(path: Path = None) -> None:
    """Save current config to file."""
    cfg = get_config()
    path = path or cfg.CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {"providers": cfg.providers.to_dict()}
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def reset_config() -> None:
    """Reset singleton (for testing)."""
    global _config
    _config = None


# Expose providers config directly for convenience
def get_provider_kwargs(name: str) -> Dict[str, Any]:
    """Get kwargs to pass directly into provider constructor."""
    cfg = get_config()
    if not hasattr(cfg.providers, name):
        raise ValueError(f"Unknown provider: {name}")

    return getattr(cfg.providers, name).to_dict()

def load_provider(name: str):
    """Load provider using configuration from file."""
    kwargs = get_provider_kwargs(name)
    return providers.get_provider(name, **kwargs)

def load_primary_provider():
    cfg = get_config()
    return load_provider(cfg.providers.primary)


# if __name__ == "__main__":
#     import pprint
#
#     # Just running this creates the default config.json automatically
#     cfg = get_config()
#     print("Current config:")
#     pprint.pprint(cfg.providers.to_dict())