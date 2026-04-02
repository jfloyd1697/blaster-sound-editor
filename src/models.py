import pathlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from dataclasses_json import DataClassJsonMixin, global_config


global_config.encoders[pathlib.Path] = lambda p: str(p) if p is not None else None
global_config.decoders[pathlib.Path] = lambda p: pathlib.Path(p) if p is not None else None
for subclass in pathlib.Path.__subclasses__():
    global_config.encoders[subclass] = global_config.encoders[pathlib.Path]
    global_config.decoders[subclass] = global_config.decoders[pathlib.Path]


class LightPatternMode(StrEnum):
    Solid = "Solid"
    Flash = "Flash"
    Pulse = "Pulse"
    Sequence = "Sequence"


@dataclass
class LightStepDef(DataClassJsonMixin):
    color: tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    durationMs: int = 0


@dataclass
class LightPatternDef(DataClassJsonMixin):
    mode: str = LightPatternMode.Solid
    color: tuple[int, int, int] = field(default_factory=lambda: (0, 0, 0))
    brightness: int = None
    durationMs: int = None
    count: int = None
    intervalMs: int = None
    steps: list[LightStepDef] = field(default_factory=list)


class ActionType(StrEnum):
    PLAY_SOUND = "play_sound"
    PLAY_SOUND_RANDOM = "play_sound_random"
    STOP_SOUND = "stop_sound"
    SET_LIGHT_PATTERN = "set_light_pattern"
    SET_LIGHT = "set_light"
    EMIT_SHOT = "emit_shot"
    EMIT_EVENT = "emit_event"
    SCHEDULE_EVENT = "schedule_event"
    FLASH_MUZZLE = "flash_muzzle"
    FLASH_LIGHT = "flash_light"
    RUN_SEQUENCE = "run_sequence"
    CONSUME_AMMO = "consume_ammo"
    DELAY = "delay"
    CUSTOM = "custom"


@dataclass
class ActionDef(DataClassJsonMixin):
    type: ActionType = ActionType.PLAY_SOUND
    sound: pathlib.Path = None
    sounds: list[pathlib.Path] = field(default_factory=list)
    loop: bool = None
    pattern: LightPatternDef = None
    event: str = None
    name: str = None
    amount: int = None
    delayMs: int = None

    @classmethod
    def run_sequence(cls, name: str):
        return cls(type=ActionType.RUN_SEQUENCE, name=name)

    @classmethod
    def play_sound(cls, sound: pathlib.Path, loop=None):
        return cls(type=ActionType.PLAY_SOUND, sound=sound, loop=loop)

    @classmethod
    def stop_sound(cls):
        return cls(type=ActionType.STOP_SOUND)

    @classmethod
    def consume_ammo(cls, amount):
        return cls(type=ActionType.CONSUME_AMMO, amount=amount)

    @classmethod
    def set_light_pattern(cls, pattern):
        return cls(type=ActionType.SET_LIGHT_PATTERN, pattern=pattern)


@dataclass
class TransitionDef(DataClassJsonMixin):
    event: str = ""
    target: str = ""
    actions: list[ActionDef] = field(default_factory=list)


@dataclass
class StateDef(DataClassJsonMixin):
    onEnter: list[ActionDef] = field(default_factory=list)
    onExit: list[ActionDef] = field(default_factory=list)
    transitions: list[TransitionDef] = field(default_factory=list)


@dataclass
class WeaponBehaviorDef(DataClassJsonMixin):
    version: int = 1
    weapon: str = "NewWeapon"
    magazineSize: int = 12
    initialState: str = "idle"
    actionSequences: dict[str, list[ActionDef]] = field(default_factory=dict)
    states: dict[str, StateDef] = field(default_factory=dict)

@dataclass
class NodeRef(DataClassJsonMixin):
    kind: str
    path: list[Any] = field(default_factory=list)


DEFAULT_DOC = WeaponBehaviorDef(
    weapon="NewWeapon",
    magazineSize=12,
    initialState="idle",
    actionSequences={
        "fire_once": [
            ActionDef.play_sound(sound=pathlib.Path("sounds/fire.wav"), loop=False)
        ]
    },
    states={
        "idle": StateDef(
            onEnter=[
                ActionDef.set_light_pattern(
                    pattern=LightPatternDef(
                        mode=LightPatternMode.Solid,
                        color=[0, 32, 255],
                        brightness=255,
                    ),
                )
            ],
            transitions=[
                TransitionDef(
                    event="trigger_pull",
                    target="firing",
                    actions=[
                        ActionDef.run_sequence(name="fire_once"),
                        ActionDef.consume_ammo(amount=1),
                    ],
                )
            ],
        ),
        "firing": StateDef(
            transitions=[
                TransitionDef(event="animation_done", target="idle")
            ]
        ),
    },
)