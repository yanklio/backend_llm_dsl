"""Semantic resolver for the textual DSL AST."""

from dataclasses import dataclass

from .ast import EntityNode, FieldNode, ProgramNode
from .errors import ResolveError, SourceLocation

PRIMITIVE_FIELD_TYPES = {"string", "number", "boolean", "date"}
RELATION_ANNOTATIONS = {"OneToMany", "ManyToOne", "OneToOne", "ManyToMany"}
ARRAY_RELATIONS = {"OneToMany", "ManyToMany"}
SCALAR_RELATIONS = {"ManyToOne", "OneToOne"}
INVERSE_RELATIONS = {
    "OneToMany": {"ManyToOne"},
    "ManyToOne": {"OneToMany"},
    "OneToOne": {"OneToOne"},
    "ManyToMany": {"ManyToMany"},
}


@dataclass(frozen=True)
class ResolvedProgram:
    """Program AST plus symbol tables built during semantic resolution."""

    program: ProgramNode
    entities: dict[str, EntityNode]
    enums: dict[str, list[str]]


class Resolver:
    """Validate cross-references before YAML blueprint emission."""

    def resolve(self, program: ProgramNode) -> ResolvedProgram:
        """Resolve symbols and validate semantic constraints."""
        entities = {entity.name: entity for entity in program.entities}
        enums = {enum.name: enum.values for enum in program.enums}
        self._check_duplicate_top_level_symbols(program)
        self._check_entity_fields(program, entities, enums)
        self._check_modules(program, entities)
        self._check_inverse_relations(program, entities)
        return ResolvedProgram(program, entities, enums)

    def _check_duplicate_top_level_symbols(self, program: ProgramNode) -> None:
        seen: dict[str, SourceLocation] = {}
        for declaration in [*program.entities, *program.enums, *program.modules]:
            if declaration.name in seen:
                self._raise("Duplicate top-level symbol", declaration.location, "RESOLVE_E001")
            seen[declaration.name] = declaration.location

    def _check_entity_fields(
        self,
        program: ProgramNode,
        entities: dict[str, EntityNode],
        enums: dict[str, list[str]],
    ) -> None:
        for entity in program.entities:
            self._check_duplicate_fields(entity)
            for field in entity.fields:
                relation = self._relation_name(field)
                if relation:
                    self._check_relation_target(field, entities)
                    self._check_relation_cardinality(entity, field, relation)
                elif field.type_name in entities:
                    self._raise(
                        f"entity field {entity.name}.{field.name} references entity "
                        f"{field.type_name} but has no relation annotation",
                        field.location,
                        "RESOLVE_E006",
                    )
                elif field.type_name not in PRIMITIVE_FIELD_TYPES and field.type_name not in enums:
                    self._raise(f"Unknown field type '{field.type_name}'", field.location, "RESOLVE_E002")

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

    def _check_relation_target(self, field: FieldNode, entities: dict[str, EntityNode]) -> None:
        if field.type_name not in entities:
            self._raise(f"Unknown relation target entity '{field.type_name}'", field.location, "RESOLVE_E002")

    def _check_relation_cardinality(self, entity: EntityNode, field: FieldNode, relation: str) -> None:
        if relation in ARRAY_RELATIONS and not field.is_array:
            self._raise(
                f"{relation} relation {entity.name}.{field.name} must use an array type",
                field.location,
                "RESOLVE_E007",
            )
        if relation in SCALAR_RELATIONS and field.is_array:
            self._raise(
                f"{relation} relation {entity.name}.{field.name} must not use an array type",
                field.location,
                "RESOLVE_E007",
            )

    def _check_modules(self, program: ProgramNode, entities: dict[str, EntityNode]) -> None:
        for module in program.modules:
            if module.entity_name not in entities:
                self._raise(f"Unknown module entity '{module.entity_name}'", module.location, "RESOLVE_E003")

    def _check_inverse_relations(self, program: ProgramNode, entities: dict[str, EntityNode]) -> None:
        for entity in program.entities:
            for field in entity.fields:
                relation = self._relation_name(field)
                inverse_name = self._inverse_name(field)
                if not relation or not inverse_name:
                    continue
                target = entities[field.type_name]
                inverse = next((item for item in target.fields if item.name == inverse_name), None)
                if inverse is None:
                    self._raise(
                        f"inverse field {target.name}.{inverse_name} does not exist",
                        field.location,
                        "RESOLVE_E008",
                    )
                inverse_relation = self._relation_name(inverse)
                if inverse_relation not in INVERSE_RELATIONS[relation]:
                    self._raise(
                        f"incompatible inverse relation {entity.name}.{field.name} "
                        f"({relation}) -> {target.name}.{inverse.name} ({inverse_relation})",
                        field.location,
                        "RESOLVE_E009",
                    )

    def _relation_name(self, field: FieldNode) -> str | None:
        for annotation in field.annotations:
            if annotation.name in RELATION_ANNOTATIONS:
                return annotation.name
        return None

    def _inverse_name(self, field: FieldNode) -> str | None:
        for annotation in field.annotations:
            if annotation.name in RELATION_ANNOTATIONS:
                return annotation.args.get("inverse")
        return None

    def _raise(self, message: str, location: SourceLocation, code: str) -> None:
        raise ResolveError(message, location, code)


def resolve(program: ProgramNode) -> ResolvedProgram:
    """Resolve a textual DSL program."""
    return Resolver().resolve(program)
