"""Emit existing YAML blueprint dictionaries from resolved textual DSL AST."""

from typing import Any

from .ast import AnnotationNode, AppNode, EntityNode, FieldNode, ModuleNode
from .resolver import RELATION_ANNOTATIONS, ResolvedProgram

DEFAULT_GENERATED_FILES = ["controller", "service", "module", "entity", "dto"]
FIELD_VALIDATION_ANNOTATIONS = {
    "email": "isEmail",
    "minLength": "minLength",
    "maxLength": "maxLength",
    "min": "min",
    "max": "max",
}


class BlueprintEmitter:
    """Convert resolved textual DSL programs into generator blueprints."""

    def emit(self, resolved: ResolvedProgram) -> dict[str, Any]:
        """Emit a blueprint dictionary accepted by the existing generator."""
        program = resolved.program
        return {
            "root": self._emit_root(program.app),
            "modules": [self._emit_module(module, resolved) for module in self._modules_to_emit(resolved)],
        }

    def _emit_root(self, app: AppNode | None) -> dict[str, Any]:
        app = app or AppNode(name="TextualDslApp")
        return {
            "name": app.name,
            "database": {
                "type": app.database_type,
                "database": app.database_path,
                "synchronize": True,
                "logging": False,
            },
            "features": {
                "cors": "cors" in app.features,
                "swagger": "swagger" in app.features,
            },
        }

    def _modules_to_emit(self, resolved: ResolvedProgram) -> list[ModuleNode]:
        declared_modules = {module.entity_name: module for module in resolved.program.modules}
        return [
            declared_modules.get(
                entity.name,
                ModuleNode(entity.name, entity.name, [], entity.location),
            )
            for entity in resolved.program.entities
        ]

    def _emit_module(
        self,
        module: ModuleNode,
        resolved: ResolvedProgram,
    ) -> dict[str, Any]:
        entity = resolved.entities[module.entity_name]
        return {
            "name": entity.name,
            "generate": list(DEFAULT_GENERATED_FILES),
            "entity": self._emit_entity(entity, resolved),
        }

    def _emit_entity(
        self,
        entity: EntityNode,
        resolved: ResolvedProgram,
    ) -> dict[str, Any]:
        fields = []
        relations = []
        for field in entity.fields:
            if self._is_relation(field):
                relations.append(self._emit_relation(field))
            else:
                fields.append(self._emit_field(field, resolved))
        return {"fields": fields, "relations": relations}

    def _emit_field(
        self,
        field: FieldNode,
        resolved: ResolvedProgram,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "name": field.name,
            "type": self._blueprint_field_type(field, resolved),
            "required": self._is_required(field),
        }
        self._copy_enum_values(payload, field, resolved)
        self._copy_field_annotations(payload, field)
        return payload

    def _blueprint_field_type(
        self,
        field: FieldNode,
        resolved: ResolvedProgram,
    ) -> str:
        if field.type_name in resolved.enums:
            return "enum"
        if field.type_name in resolved.types or field.type_name in resolved.entities:
            return "custom"
        return field.type_name

    def _copy_enum_values(
        self,
        payload: dict[str, Any],
        field: FieldNode,
        resolved: ResolvedProgram,
    ) -> None:
        values = resolved.enums.get(field.type_name)
        if values is not None:
            payload["enumValues"] = values

    def _copy_field_annotations(
        self,
        payload: dict[str, Any],
        field: FieldNode,
    ) -> None:
        validation: dict[str, Any] = {}
        for annotation in field.annotations:
            self._copy_validation_annotation(validation, annotation)
            self._copy_metadata_annotation(payload, annotation)

        if validation:
            payload["validation"] = validation

    def _copy_validation_annotation(
        self,
        validation: dict[str, Any],
        annotation: AnnotationNode,
    ) -> None:
        target_name = FIELD_VALIDATION_ANNOTATIONS.get(annotation.name)
        if target_name is None:
            return
        validation[target_name] = annotation.args.get("value", True)

    def _copy_metadata_annotation(
        self,
        payload: dict[str, Any],
        annotation: AnnotationNode,
    ) -> None:
        if annotation.name == "unique":
            payload["unique"] = True
        elif annotation.name == "default" and "value" in annotation.args:
            payload["default"] = annotation.args["value"]
        elif annotation.name == "description" and "value" in annotation.args:
            payload["description"] = annotation.args["value"]
        elif annotation.name == "example" and "value" in annotation.args:
            payload["example"] = annotation.args["value"]

    def _emit_relation(self, field: FieldNode) -> dict[str, Any]:
        relation = self._relation_annotation(field)
        payload: dict[str, Any] = {
            "type": relation.name,
            "model": field.type_name,
            "field": field.name,
            "required": self._is_required(field),
        }
        if "inverse" in relation.args:
            payload["inverseField"] = relation.args["inverse"]

        for annotation in field.annotations:
            if annotation.name == "onDelete" and "value" in annotation.args:
                payload["onDelete"] = annotation.args["value"]
            elif annotation.name == "description" and "value" in annotation.args:
                payload["description"] = annotation.args["value"]
        return payload

    def _relation_annotation(self, field: FieldNode) -> AnnotationNode:
        for annotation in field.annotations:
            if annotation.name in RELATION_ANNOTATIONS:
                return annotation
        raise ValueError(f"Field '{field.name}' is not a relation")

    def _is_relation(self, field: FieldNode) -> bool:
        return any(annotation.name in RELATION_ANNOTATIONS for annotation in field.annotations)

    def _is_required(self, field: FieldNode) -> bool:
        if any(annotation.name == "required" for annotation in field.annotations):
            return True
        return field.required


def emit_blueprint(resolved: ResolvedProgram) -> dict[str, Any]:
    """Emit a YAML blueprint dictionary from a resolved textual DSL program."""
    return BlueprintEmitter().emit(resolved)
