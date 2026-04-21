import dataclasses
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
    model: str = "llama3.2"
    temperature: float = 1.0
    max_tokens: Optional[int] = None
    timeout: int = 60
    keep_alive: str = "5m"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ProvidersConfig:
    primary: str = field(default="openai")

    openai: OpenAIConfig = field(default_factory=OpenAIConfig)
    anthropic: AnthropicConfig = field(default_factory=AnthropicConfig)
    ollama: OllamaConfig = field(default_factory=OllamaConfig)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self) # applies asdict to nested dataclasses, no clue why claude was persistent on manually packing

# ACTUALLY modularized config + defaults
def _update_from_dict(config_obj, data: Dict[str, Any]) -> None:
    for f in dataclasses.fields(config_obj):
        if f.name not in data:
            continue
        attr = getattr(config_obj, f.name)
        value = data[f.name]
        if dataclasses.is_dataclass(attr):
            _update_from_dict(attr, value if isinstance(value, dict) else {})
        else:
            setattr(config_obj, f.name, value)


@dataclass
class MCPConfig:
    transport:str = field(default="stdio")
    host:str = field(default="127.0.0.1")
    port:int = field(default=8000)

    # will search the library for new skills whenever skills are listed
    # configurable because a large library might add latency if not necessary.
    list_rediscovery:bool = field(default=True)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

@dataclass
class Config:
    # config.json fixed to filepath, paths inside still relative to cwd
    CONFIG_FILE = Path(__file__).parent / "config.json"

    skills_path: str = field(default_factory=lambda: str((Config.CONFIG_FILE.parent / ".skills").resolve())) # messy but wtv
    mcp: MCPConfig = field(default_factory=MCPConfig)
    providers: ProvidersConfig = field(default_factory=ProvidersConfig)

    # again, doesn't hardcode the keys
    def __post_init__(self):
        if self.CONFIG_FILE.exists():
            try:
                data = json.loads(self.CONFIG_FILE.read_text())
                _update_from_dict(self, data)
            except Exception as e:
                print(f"Warning loading config: {e}")
        else:
            self._save_to_file()

    def _save_to_file(self, path: Path = None) -> None:
        path = path or self.CONFIG_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self) # same thing
        # return {
        #     "skills_path": self.skills_path,
        #     "providers": self.providers.to_dict()
        # }


_config: Optional[Config] = None


def get_config() -> Config:
    global _config
    if _config is None:
        _config = Config()

    assert _config is not None # SHUT UP LINTER
    return _config


def save_config(path: Path = None) -> None:
    cfg = get_config()
    path = path or cfg.CONFIG_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(cfg.to_dict(), f, indent=2)


def reset_config() -> None:
    """
    Drops the cached config state, but does not clear the config from file.
    """
    global _config
    _config = None


def _get_provider_kwargs(name: str) -> Dict[str, Any]:
    cfg = get_config()
    if not hasattr(cfg.providers, name):
        raise ValueError(f"Unknown provider: {name}")
    return getattr(cfg.providers, name).to_dict()

def load_provider(name: str):
    kwargs = _get_provider_kwargs(name)
    return providers.get_provider(name, **kwargs)

def load_primary_provider():
    cfg = get_config()
    return load_provider(cfg.providers.primary)