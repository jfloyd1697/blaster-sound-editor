from typing import Any
import json

from models import ActionDef, NodeRef, StateDef, TransitionDef, WeaponBehaviorDef
from utils import unique_name


class DocumentService:
    def __init__(self, doc: WeaponBehaviorDef):
        self.doc = doc

    def set_document(self, doc: WeaponBehaviorDef) -> None:
        self.doc = doc

    def resolve_action_ref(self, ref: NodeRef) -> ActionDef | None:
        if ref.kind == "actionSequenceAction":
            sequence_name, action_index = ref.path
            return self.doc.actionSequences[sequence_name][action_index]

        if ref.kind == "stateOnEnterAction":
            state_name, action_index = ref.path
            return self.doc.states[state_name].onEnter[action_index]

        if ref.kind == "stateOnExitAction":
            state_name, action_index = ref.path
            return self.doc.states[state_name].onExit[action_index]

        if ref.kind == "transitionAction":
            state_name, transition_index, action_index = ref.path
            return self.doc.states[state_name].transitions[transition_index].actions[action_index]

        return None

    def add_node(self, ref: NodeRef) -> None:
        if ref.kind in {"weapon", "statesRoot"}:
            name = unique_name("state", set(self.doc.states.keys()))
            self.doc.states[name] = StateDef()
            return

        if ref.kind == "actionSequencesRoot":
            name = unique_name("sequence", set(self.doc.actionSequences.keys()))
            self.doc.actionSequences[name] = []
            return

        if ref.kind == "actionSequence":
            sequence_name = ref.path[0]
            self.doc.actionSequences[sequence_name].append(ActionDef())
            return

        if ref.kind == "stateOnEnterRoot":
            state_name = ref.path[0]
            self.doc.states[state_name].onEnter.append(ActionDef())
            return

        if ref.kind == "stateOnExitRoot":
            state_name = ref.path[0]
            self.doc.states[state_name].onExit.append(ActionDef())
            return

        if ref.kind == "state":
            state_name = ref.path[0]
            self.doc.states[state_name].transitions.append(TransitionDef())
            return

        if ref.kind == "transitionActionsRoot":
            state_name, transition_index = ref.path
            self.doc.states[state_name].transitions[transition_index].actions.append(ActionDef())

    def remove_node(self, ref: NodeRef) -> None:
        if ref.kind == "state":
            del self.doc.states[ref.path[0]]
            return

        if ref.kind == "actionSequence":
            del self.doc.actionSequences[ref.path[0]]
            return

        if ref.kind == "actionSequenceAction":
            sequence_name, action_index = ref.path
            del self.doc.actionSequences[sequence_name][action_index]
            return

        if ref.kind == "stateOnEnterAction":
            state_name, action_index = ref.path
            del self.doc.states[state_name].onEnter[action_index]
            return

        if ref.kind == "stateOnExitAction":
            state_name, action_index = ref.path
            del self.doc.states[state_name].onExit[action_index]
            return

        if ref.kind == "transition":
            state_name, transition_index = ref.path
            del self.doc.states[state_name].transitions[transition_index]
            return

        if ref.kind == "transitionAction":
            state_name, transition_index, action_index = ref.path
            del self.doc.states[state_name].transitions[transition_index].actions[action_index]

    def rename_state(self, old_name: str, new_name: str) -> None:
        if not new_name or new_name == old_name:
            return

        if new_name in self.doc.states:
            raise ValueError(f"State '{new_name}' already exists.")

        self.doc.states[new_name] = self.doc.states.pop(old_name)

        if self.doc.initialState == old_name:
            self.doc.initialState = new_name

        for state in self.doc.states.values():
            for transition in state.transitions:
                if transition.target == old_name:
                    transition.target = new_name

    def flatten_json_rows(self, value: Any, prefix: str = "") -> list[tuple[str, str]]:
        rows: list[tuple[str, str]] = []
        self._flatten_json(value, rows, prefix)
        return rows

    def _flatten_json(self, value: Any, rows: list[tuple[str, str]], prefix: str = "") -> None:

        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else str(key)
                self._flatten_json(child, rows, path)
        elif isinstance(value, list):
            for index, child in enumerate(value):
                path = f"{prefix}[{index}]"
                self._flatten_json(child, rows, path)
        else:
            rows.append((prefix, json.dumps(value)))