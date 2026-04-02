import os
import shutil
from pathlib import Path


class AssetService:
    def __init__(self, assets_root: str | None = None):
        self.assets_root = assets_root

    def set_assets_root(self, assets_root: str | None) -> None:
        self.assets_root = assets_root

    def import_asset(self, src_path: str) -> str:
        normalized_src = src_path.replace("\\", "/")
        if not self.assets_root:
            return normalized_src

        assets_root = Path(self.assets_root)
        src = Path(src_path)

        if assets_root not in src.parents and src != assets_root:
            target = assets_root / src.name
            if target.resolve() != src.resolve():
                shutil.copy2(src, target)
            src = target

        return os.path.relpath(src, assets_root).replace("\\", "/")