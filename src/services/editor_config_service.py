from pathlib import Path
from typing import Any

from persistence.editor_configs import (
    EditorConfig,
)


class EditorConfigService:
    def __init__(self, config: EditorConfig | None = None):
        self.config = config or EditorConfig()

    def load_from_path(self, path: str | Path) -> EditorConfig:
        with open(path, "r", encoding="utf-8") as f:
            self.config = EditorConfig.from_json(f.read())
        return self.config

    def to_dict(self) -> dict[str, Any]:
        return self.config.to_dict()
