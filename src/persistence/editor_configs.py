from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from dataclasses_json import DataClassJsonMixin


class WidgetType(StrEnum):
    LineEdit = "lineedit"
    SpinBox = "spinbox"
    CheckBox = "checkbox"
    Combo = "combo"
    AssetPath = "asset_path"
    StringList = "string_list"
    RgbColor = "rgb_color"
    LightStepsTable = "light_steps_table"


class GraphLayout(StrEnum):
    Circle = "circle"


@dataclass
class GraphUiConfig(DataClassJsonMixin):
    showAutoscaleButton: bool = True
    allowNodeDragging: bool = True
    showArrowheads: bool = True
    curveOffset: int = 24
    nodeRadius: int = 34
    layout: str = GraphLayout.Circle.value


@dataclass
class TreeUiConfig(DataClassJsonMixin):
    expandRootOnLoad: bool = True
    expandStatesOnLoad: bool = True
    expandActionSequencesOnLoad: bool = True
    sortStates: bool = False
    sortActionSequences: bool = False


@dataclass
class AssetsUiConfig(DataClassJsonMixin):
    copyDroppedFilesIntoAssetsRoot: bool = True
    storeRelativePaths: bool = True
    allowedExtensions: list[str] = field(default_factory=list)


@dataclass
class UiConfig(DataClassJsonMixin):
    showTopLevelFields: bool = True
    showTree: bool = True
    showJsonPreview: bool = True
    showGraph: bool = True
    showAssets: bool = True
    showStateEditor: bool = True
    showActionEditor: bool = True
    graph: GraphUiConfig = field(default_factory=GraphUiConfig)
    tree: TreeUiConfig = field(default_factory=TreeUiConfig)
    assets: AssetsUiConfig = field(default_factory=AssetsUiConfig)


@dataclass
class FieldConfig(DataClassJsonMixin):
    visible: bool = True
    widget: WidgetType | None = None
    required: bool = False
    readOnly: bool = False
    default: Any = None
    min: int | None = None
    max: int | None = None
    suffix: str | None = None
    options: list[str] = field(default_factory=list)
    acceptDrop: bool = False
    source: str | None = None
    columns: list[str] = field(default_factory=list)
    showWhen: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransitionFieldsConfig(DataClassJsonMixin):
    event: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.LineEdit, required=True))
    target: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.LineEdit, required=True))


@dataclass
class TopLevelFieldsConfig(DataClassJsonMixin):
    version: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.SpinBox, min=1, max=999, default=1))
    weapon: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.LineEdit, default=""))
    magazineSize: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.SpinBox, min=0, max=999999, default=0))
    initialState: FieldConfig = field(default_factory=lambda: FieldConfig(visible=True, widget=WidgetType.LineEdit, default="idle", required=True))


@dataclass
class FieldsConfig(DataClassJsonMixin):
    topLevel: TopLevelFieldsConfig = field(default_factory=TopLevelFieldsConfig)
    transition: TransitionFieldsConfig = field(default_factory=TransitionFieldsConfig)


@dataclass
class ActionTypeConfig(DataClassJsonMixin):
    label: str = ""
    fields: dict[str, FieldConfig] = field(default_factory=dict)


@dataclass
class EditorConfig(DataClassJsonMixin):
    version: int = 1
    ui: UiConfig = field(default_factory=UiConfig)
    fields: FieldsConfig = field(default_factory=FieldsConfig)
    actionTypes: dict[str, ActionTypeConfig] = field(default_factory=dict)
