"""AST node definitions for the textual DSL compiler."""

from dataclasses import dataclass, field
from typing import Any

from .errors import SourceLocation


@dataclass(frozen=True)
class AnnotationNode:
    """Annotation attached to a field, relation, or route declaration."""

    name: str
    args: dict[str, Any]
    location: SourceLocation


@dataclass(frozen=True)
class FieldNode:
    """Entity or type field declaration."""

    name: str
    type_name: str
    required: bool
    is_array: bool
    annotations: list[AnnotationNode]
    location: SourceLocation


@dataclass(frozen=True)
class EntityNode:
    """Entity declaration."""

    name: str
    fields: list[FieldNode]
    location: SourceLocation


@dataclass(frozen=True)
class EnumNode:
    """Enumeration declaration."""

    name: str
    values: list[str]
    location: SourceLocation


@dataclass(frozen=True)
class TypeNode:
    """Named structural type declaration."""

    name: str
    fields: list[FieldNode]
    location: SourceLocation


@dataclass(frozen=True)
class DtoNode:
    """DTO declaration validated against a target entity."""

    name: str
    entity_name: str
    fields: list[str]
    location: SourceLocation


@dataclass(frozen=True)
class RouteNode:
    """HTTP route declaration used for semantic specification."""

    method: str
    path: str
    return_type: str
    returns_array: bool
    location: SourceLocation


@dataclass(frozen=True)
class ModuleNode:
    """Generated NestJS module declaration."""

    name: str
    entity_name: str
    routes: list[RouteNode]
    location: SourceLocation


@dataclass(frozen=True)
class AppNode:
    """Root application configuration declaration."""

    name: str
    database_type: str = "sqlite"
    database_path: str = "./data/app.db"
    features: list[str] = field(default_factory=lambda: ["cors", "swagger"])
    location: SourceLocation = field(default_factory=lambda: SourceLocation(1, 1))


@dataclass(frozen=True)
class ProgramNode:
    """Top-level textual DSL program."""

    app: AppNode | None
    entities: list[EntityNode]
    modules: list[ModuleNode]
    dtos: list[DtoNode]
    enums: list[EnumNode]
    types: list[TypeNode]
    location: SourceLocation
