from dataclasses import fields

from PyQt6.QtCore import Qt
from PyQt6 import QtWidgets

from models import NodeRef, WeaponBehaviorDef, ActionDef, StateDef


class TreeService:

    def _sequences_root(self, doc):
        sequences_root = QtWidgets.QTreeWidgetItem(["actionSequences"])
        sequences_root.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind="actionSequencesRoot", path=[]),
        )
        for sequence_name, actions in doc.actionSequences.items():
            sequence_item = QtWidgets.QTreeWidgetItem([sequence_name])
            sequence_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                NodeRef(kind="actionSequence", path=[sequence_name]),
            )
            sequences_root.addChild(sequence_item)

            for action_index, action in enumerate(actions):
                action_item = self._action_item(
                    action,
                    "actionSequenceAction",
                    path=[sequence_name, action_index],
                )
                sequence_item.addChild(action_item)
        return sequences_root

    def _states_root(self, doc):
        states_root = QtWidgets.QTreeWidgetItem(["states"])
        states_root.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind="statesRoot", path=[]),
        )
        for state_name, state in doc.states.items():
            state_item = QtWidgets.QTreeWidgetItem([state_name])
            state_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                NodeRef(kind="state", path=[state_name]),
            )
            states_root.addChild(state_item)

            states_on_enter_root = self._states_on_enter_root(state, state_name)
            state_item.addChild(states_on_enter_root)

            states_on_exit_root = self._states_on_exit_root(state, state_name)
            state_item.addChild(states_on_exit_root)

            states_transitions_root = self._states_transitions_root(state, state_name)
            state_item.addChild(states_transitions_root)

        return states_root

    def _states_on_enter_root(self, state, state_name):
        on_enter_root = QtWidgets.QTreeWidgetItem(["onEnter"])
        on_enter_root.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind="stateOnEnterRoot", path=[state_name]),
        )
        for action_index, action in enumerate(state.onEnter):
            action_item = self._action_item(
                action,
                "stateOnEnterAction",
                path=[state_name, action_index],
            )
            on_enter_root.addChild(action_item)
        return on_enter_root

    @staticmethod
    def _action_item(action: ActionDef, action_kind, path: list):
        action_item = QtWidgets.QTreeWidgetItem([f"[{path[-1]}] {action.type}"])
        action_item.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind=action_kind, path=path),
        )

        for field in fields(action):
            if getattr(action, field.name) not in [None, []]:
                action_field_item = QtWidgets.QTreeWidgetItem([f"{field.name}={getattr(action, field.name)}"])
                action_item.addChild(action_field_item)

        return action_item

    def _states_on_exit_root(self, state: StateDef, state_name):
        on_exit_root = QtWidgets.QTreeWidgetItem(["onExit"])
        on_exit_root.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind="stateOnExitRoot", path=[state_name]),
        )
        for action_index, action in enumerate(state.onExit):
            action_item = self._action_item(
                action,
                "stateOnExitAction",
                path=[state_name, action_index],
            )
            on_exit_root.addChild(action_item)
        return on_exit_root

    def _states_transitions_root(self, state: StateDef, state_name):
        transitions_root = QtWidgets.QTreeWidgetItem(["transitions"])
        transitions_root.setData(
            0,
            Qt.ItemDataRole.UserRole,
            NodeRef(kind="transitionsRoot", path=[state_name]),
        )
        for transition_index, transition in enumerate(state.transitions):
            transition_item = QtWidgets.QTreeWidgetItem(
                [f"[{transition_index}] {transition.event} -> {transition.target}"]
            )
            transition_item.setData(
                0,
                Qt.ItemDataRole.UserRole,
                NodeRef(kind="transition", path=[state_name, transition_index]),
            )
            transitions_root.addChild(transition_item)

            actions_root = QtWidgets.QTreeWidgetItem(["actions"])
            actions_root.setData(
                0,
                Qt.ItemDataRole.UserRole,
                NodeRef(kind="transitionActionsRoot", path=[state_name, transition_index]),
            )
            transition_item.addChild(actions_root)

            for action_index, action in enumerate(transition.actions):
                action_kind = "transitionAction"

                action_item = self._action_item(
                    action,
                    action_kind,
                    path=[state_name, transition_index, action_index],
                )

                actions_root.addChild(action_item)
        return transitions_root

    def rebuild_tree(self, doc: WeaponBehaviorDef) -> QtWidgets.QTreeWidgetItem:
        root = QtWidgets.QTreeWidgetItem([doc.weapon or "<weapon>"])
        root.setData(0, Qt.ItemDataRole.UserRole, NodeRef(kind="weapon", path=[]))

        sequences_root = self._sequences_root(doc)
        root.addChild(sequences_root)

        states_root = self._states_root(doc)
        root.addChild(states_root)

        root.setExpanded(True)
        sequences_root.setExpanded(True)
        states_root.setExpanded(True)

        return root


