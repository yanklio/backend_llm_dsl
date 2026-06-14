"""Semantic resolver for the textual DSL AST."""

from dataclasses import dataclass

from .ast import DtoNode, EntityNode, FieldNode, ProgramNode, RouteNode
from .errors import ResolveError, SourceLocation

PRIMITIVE_FIELD_TYPES = {"string", "number", "boolean", "date"}
PRIMITIVE_ROUTE_TYPES = PRIMITIVE_FIELD_TYPES | {"void"}
RELATION_ANNOTATIONS = {"OneToMany", "ManyToOne", "OneToOne", "ManyToMany"}


@dataclass(frozen=True)
class ResolvedProgram:
    """Program AST plus symbol tables built during semantic resolution."""

    program: ProgramNode
    entities: dict[str, EntityNode]
    enums: dict[str, list[str]]
    types: set[str]


class Resolver:
    """Validate cross-references before YAML blueprint emission."""

    def resolve(self, program: ProgramNode) -> ResolvedProgram:
        """Resolve symbols and validate semantic constraints."""
        entities = self._collect_entities(program)
        enums = self._collect_enums(program)
        types = self._collect_types(program)

        self._check_duplicate_top_level_symbols(program)
        self._check_entity_fields(program, entities, enums, types)
        self._check_modules(program, entities)
        self._check_dtos(program, entities)
        self._check_routes(program, entities, enums, types)

        return ResolvedProgram(program, entities, enums, types)

    def _collect_entities(self, program: ProgramNode) -> dict[str, EntityNode]:
        return {entity.name: entity for entity in program.entities}

    def _collect_enums(self, program: ProgramNode) -> dict[str, list[str]]:
        return {enum.name: enum.values for enum in program.enums}

    def _collect_types(self, program: ProgramNode) -> set[str]:
        return {type_node.name for type_node in program.types}

    def _check_duplicate_top_level_symbols(self, program: ProgramNode) -> None:
        seen: dict[str, SourceLocation] = {}
        declarations = [
            *program.entities,
            *program.enums,
            *program.types,
            *program.modules,
            *program.dtos,
        ]
        for declaration in declarations:
            name = declaration.name
            if name in seen:
                self._raise(
                    "Duplicate top-level symbol",
                    declaration.location,
                    "RESOLVE_E001",
                )
            seen[name] = declaration.location

    def _check_entity_fields(
        self,
        program: ProgramNode,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
        types: set[str],
    ) -> None:
        for entity in program.entities:
            self._check_duplicate_fields(entity)
            for field in entity.fields:
                if self._is_relation_field(field):
                    self._check_relation_target(field, entities)
                elif not self._is_known_field_type(field.type_name, entities, enums, types):
                    self._raise(
                        f"Unknown field type '{field.type_name}'",
                        field.location,
                        "RESOLVE_E002",
                    )

    def _check_duplicate_fields(self, entity: EntityNode) -> None:
        seen = set()
        for field in entity.fields:
            if field.name in seen:
                self._raise(
                    f"Duplicate field '{field.name}' in entity '{entity.name}'",
                    field.location,
                    "RESOLVE_E001",
                )
            seen.add(field.name)

    def _check_relation_target(
        self,
        field: FieldNode,
        entities: dict[str, EntityNode],
    ) -> None:
        if field.type_name in entities:
            return
        self._raise(
            f"Unknown relation target entity '{field.type_name}'",
            field.location,
            "RESOLVE_E002",
        )

    def _check_modules(
        self,
        program: ProgramNode,
        entities: dict[str, EntityNode],
    ) -> None:
        for module in program.modules:
            if module.entity_name not in entities:
                self._raise(
                    f"Unknown module entity '{module.entity_name}'",
                    module.location,
                    "RESOLVE_E003",
                )

    def _check_dtos(
        self,
        program: ProgramNode,
        entities: dict[str, EntityNode],
    ) -> None:
        for dto in program.dtos:
            entity = self._entity_for_dto(dto, entities)
            field_names = {field.name for field in entity.fields}
            for field_name in dto.fields:
                if field_name not in field_names:
                    self._raise(
                        f"DTO field '{field_name}' does not exist on '{entity.name}'",
                        dto.location,
                        "RESOLVE_E004",
                    )

    def _entity_for_dto(
        self,
        dto: DtoNode,
        entities: dict[str, EntityNode],
    ) -> EntityNode:
        entity = entities.get(dto.entity_name)
        if entity is None:
            self._raise(
                f"Unknown DTO entity '{dto.entity_name}'",
                dto.location,
                "RESOLVE_E003",
            )
        return entity

    def _check_routes(
        self,
        program: ProgramNode,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
        types: set[str],
    ) -> None:
        for module in program.modules:
            for route in module.routes:
                self._check_route_return_type(route, entities, enums, types)

    def _check_route_return_type(
        self,
        route: RouteNode,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
        types: set[str],
    ) -> None:
        if route.return_type in PRIMITIVE_ROUTE_TYPES:
            return
        if self._is_known_named_type(route.return_type, entities, enums, types):
            return
        self._raise(
            f"Unknown route return type '{route.return_type}'",
            route.location,
            "RESOLVE_E005",
        )

    def _is_relation_field(self, field: FieldNode) -> bool:
        return any(annotation.name in RELATION_ANNOTATIONS for annotation in field.annotations)

    def _is_known_field_type(
        self,
        type_name: str,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
        types: set[str],
    ) -> bool:
        if type_name in PRIMITIVE_FIELD_TYPES:
            return True
        return self._is_known_named_type(type_name, entities, enums, types)

    def _is_known_named_type(
        self,
        type_name: str,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
        types: set[str],
    ) -> bool:
        return type_name in entities or type_name in enums or type_name in types

    def _raise(
        self,
        message: str,
        location: SourceLocation,
        code: str,
    ) -> None:
        raise ResolveError(message, location, code)


def resolve(program: ProgramNode) -> ResolvedProgram:
    """Resolve a textual DSL program."""
    return Resolver().resolve(program)
