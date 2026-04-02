from __future__ import annotations

import copy
from dataclasses import asdict
from typing import Callable

from models import WeaponBehaviorDef


class UndoRedoService:
    def __init__(
        self,
        get_doc: Callable[[], WeaponBehaviorDef],
        set_doc: Callable[[WeaponBehaviorDef], None],
    ):
        self._get_doc = get_doc
        self._set_doc = set_doc
        self._undo_stack: list[str] = []
        self._redo_stack: list[str] = []
        self._is_restoring = False

    @property
    def is_restoring(self) -> bool:
        return self._is_restoring

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def capture_undo(self) -> None:
        if self._is_restoring:
            return
        snap = self._snapshot()
        if self._undo_stack and self._undo_stack[-1] == snap:
            return
        self._undo_stack.append(snap)
        self._redo_stack.clear()

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def undo(self) -> None:
        if not self._undo_stack:
            return

        current = self._snapshot()
        previous = self._undo_stack.pop()
        self._redo_stack.append(current)
        self._restore(previous)

    def redo(self) -> None:
        if not self._redo_stack:
            return

        current = self._snapshot()
        nxt = self._redo_stack.pop()
        self._undo_stack.append(current)
        self._restore(nxt)

    def _snapshot(self) -> str:
        doc = self._get_doc()
        return doc.to_json()

    def _restore(self, payload: str) -> None:
        self._is_restoring = True
        try:
            restored = WeaponBehaviorDef.from_json(payload)
            self._set_doc(restored)
        finally:
            self._is_restoring = False
