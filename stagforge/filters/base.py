"""Base filter class using Pydantic BaseModel."""

import uuid
from abc import ABC, abstractmethod
from typing import Any, ClassVar

import numpy as np
from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo


class BaseFilter(BaseModel, ABC):
    """Base class for all image filters.

    Uses Pydantic BaseModel for serialization, validation, and auto-generated
    parameter schemas. Matches the LayerEffect pattern.

    Each filter has a VERSION class attribute for serialization migration.
    When filter parameters change, increment VERSION and add migration logic.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        validate_assignment=False,
        extra='ignore',
        arbitrary_types_allowed=True,
    )

    # ClassVar metadata (not serialized as fields)
    filter_type: ClassVar[str] = "base"
    name: ClassVar[str] = "Base Filter"
    description: ClassVar[str] = "Base filter description"
    category: ClassVar[str] = "uncategorized"
    VERSION: ClassVar[int] = 1

    # Registry of filter classes by filter_type
    _registry: ClassVar[dict[str, type['BaseFilter']]] = {}

    # Instance fields for layer attachment
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    enabled: bool = Field(default=True)
    source: str = Field(default='wasm')

    # Serialization metadata
    version: int = Field(default=1, alias='_version')
    type_name: str = Field(default='BaseFilter', alias='_type')

    def __init_subclass__(cls, **kwargs):
        """Register filter subclass in registry."""
        super().__init_subclass__(**kwargs)
        if hasattr(cls, 'filter_type') and cls.filter_type != "base":
            BaseFilter._registry[cls.filter_type] = cls

    @abstractmethod
    def apply(self, image: np.ndarray) -> np.ndarray:
        """Apply the filter to an image.

        Params are instance attributes — not **kwargs.

        Args:
            image: RGBA numpy array, shape (height, width, 4), dtype uint8

        Returns:
            Filtered RGBA numpy array, same shape and dtype
        """
        pass

    # ------------------------------------------------------------------
    # Serialization (JS DynamicFilter.serialize() compatible)
    # ------------------------------------------------------------------

    # Fields that are base infrastructure, not algorithm params
    _BASE_FIELDS: ClassVar[frozenset[str]] = frozenset(
        {'id', 'enabled', 'source', 'version', 'type_name'}
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize matching JS DynamicFilter.serialize() format exactly."""
        params = {}
        for field_name in self.model_fields:
            if field_name not in self._BASE_FIELDS:
                params[field_name] = getattr(self, field_name)
        return {
            'id': self.id,
            'filterId': self.filter_type,
            'name': self.name,
            'enabled': self.enabled,
            'params': params,
            'source': self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'BaseFilter':
        """Deserialize from JS DynamicFilter.serialize() format."""
        filter_type = data.get('filterId') or data.get('type', 'base')
        filter_cls = cls._registry.get(filter_type)
        if filter_cls is None:
            raise ValueError(f"Unknown filter type: {filter_type}")
        params = data.get('params', {})
        return filter_cls(
            id=data.get('id', str(uuid.uuid4())),
            enabled=data.get('enabled', True),
            source=data.get('source', 'wasm'),
            **params,
        )

    # ------------------------------------------------------------------
    # Auto-generated param schema (replaces hand-written get_params_schema)
    # ------------------------------------------------------------------

    @classmethod
    def get_params_schema(cls) -> list[dict[str, Any]]:
        """Auto-generate param schema from model_fields for REST API / JS UI."""
        schema = []
        for field_name, field_info in cls.model_fields.items():
            if field_name in cls._BASE_FIELDS:
                continue
            param = _field_to_param_schema(field_name, field_info)
            if param:
                schema.append(param)
        return schema


def _field_to_param_schema(field_name: str, field_info: FieldInfo) -> dict[str, Any] | None:
    """Map a Pydantic FieldInfo to the REST API schema dict format."""
    extra = field_info.json_schema_extra or {}

    # Determine type from annotation
    annotation = field_info.annotation
    if annotation is None:
        return None

    # Unwrap Optional
    origin = getattr(annotation, '__origin__', None)
    if origin is type(None):
        return None

    schema_type = 'range'  # default
    if annotation is bool:
        schema_type = 'checkbox'
    elif annotation is str:
        if extra.get('options'):
            schema_type = 'select'
        elif 'color' in field_name.lower():
            schema_type = 'color'
        else:
            schema_type = 'text'

    param: dict[str, Any] = {
        'id': field_name,
        'name': extra.get('display_name', field_name.replace('_', ' ').title()),
        'type': schema_type,
        'default': field_info.default,
    }

    # Range constraints from Field(ge=, le=)
    for meta in (field_info.metadata or []):
        if hasattr(meta, 'ge') and meta.ge is not None:
            param['min'] = meta.ge
        if hasattr(meta, 'le') and meta.le is not None:
            param['max'] = meta.le
        if hasattr(meta, 'gt') and meta.gt is not None:
            param['min'] = meta.gt
        if hasattr(meta, 'lt') and meta.lt is not None:
            param['max'] = meta.lt

    # Extra schema hints
    for key in ('step', 'suffix', 'options', 'visible_when'):
        if key in extra:
            param[key] = extra[key]

    return param
