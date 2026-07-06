"""Recursive descent parser for the textual DSL."""

from collections.abc import Callable
from typing import Any

from .ast import (
    AnnotationNode,
    AppNode,
    EntityNode,
    EnumNode,
    FieldNode,
    ModuleNode,
    ProgramNode,
)
from .errors import ParseError, SourceLocation
from .lexer import Token, TokenType, tokenize

TOP_LEVEL_TOKENS = {
    TokenType.APP,
    TokenType.ENTITY,
    TokenType.MODULE,
    TokenType.ENUM,
}
NAME_TOKENS = (
    TokenType.IDENT,
    TokenType.APP,
    TokenType.MODULE,
    TokenType.ENTITY,
    TokenType.DTO,
    TokenType.ENUM,
    TokenType.TYPE,
    TokenType.FOR,
    TokenType.ROUTE,
    TokenType.DATABASE,
    TokenType.FEATURES,
    TokenType.GET,
    TokenType.POST,
    TokenType.PATCH,
    TokenType.PUT,
    TokenType.DELETE,
)


class Parser:
    """Parse textual DSL tokens into a direct AST."""

    def __init__(self, tokens: list[Token]) -> None:
        """Initialize parser state."""
        self.tokens = tokens
        self.current = 0
        self._declarations: dict[TokenType, Callable[[Token], object]] = {
            TokenType.APP: self._parse_app,
            TokenType.ENTITY: self._parse_entity,
            TokenType.MODULE: self._parse_module,
            TokenType.ENUM: self._parse_enum,
        }

    def parse(self) -> ProgramNode:
        """Parse a complete program."""
        location = self._peek().location
        app: AppNode | None = None
        entities: list[EntityNode] = []
        modules: list[ModuleNode] = []
        enums: list[EnumNode] = []

        while not self._at(TokenType.EOF):
            declaration = self._parse_declaration()
            if isinstance(declaration, AppNode):
                app = declaration
            elif isinstance(declaration, EntityNode):
                entities.append(declaration)
            elif isinstance(declaration, ModuleNode):
                modules.append(declaration)
            elif isinstance(declaration, EnumNode):
                enums.append(declaration)

        return ProgramNode(app, entities, modules, enums, location)

    def _parse_declaration(self) -> object:
        token = self._advance()
        parser = self._declarations.get(token.type)
        if parser is None:
            raise self._error(token, "Expected top-level declaration")
        return parser(token)

    def _parse_app(self, keyword: Token) -> AppNode:
        name = self._consume_identifier("Expected application name")
        self._consume(TokenType.LBRACE, "Expected '{' after application name")

        database_type = "sqlite"
        database_path = "./data/app.db"
        features = ["cors", "swagger"]

        while not self._at(TokenType.RBRACE):
            self._reject_nested_declaration()
            if self._match(TokenType.DATABASE):
                database_type, database_path = self._parse_database_entry()
            elif self._match(TokenType.FEATURES):
                features = self._parse_features_entry()
            else:
                raise self._error(self._peek(), "Expected app configuration entry")

        self._consume(TokenType.RBRACE, "Expected '}' after app block")
        return AppNode(name, database_type, database_path, features, keyword.location)

    def _parse_database_entry(self) -> tuple[str, str]:
        self._consume(TokenType.COLON, "Expected ':' after database")
        database_type = self._consume_identifier("Expected database type")
        database_path = "./data/app.db"

        for annotation in self._parse_annotations():
            if annotation.name == "path" and "value" in annotation.args:
                database_path = str(annotation.args["value"])
        return database_type, database_path

    def _parse_features_entry(self) -> list[str]:
        self._consume(TokenType.COLON, "Expected ':' after features")
        return self._parse_identifier_list()

    def _parse_entity(self, keyword: Token) -> EntityNode:
        name = self._consume_identifier("Expected entity name")
        return EntityNode(name, self._parse_field_block("entity"), keyword.location)

    def _parse_enum(self, keyword: Token) -> EnumNode:
        name = self._consume_identifier("Expected enum name")
        self._consume(TokenType.LBRACE, "Expected '{' after enum name")

        values = []
        while not self._at(TokenType.RBRACE):
            self._reject_nested_declaration()
            values.append(self._consume_identifier("Expected enum value"))
            self._match(TokenType.COMMA)

        self._consume(TokenType.RBRACE, "Expected '}' after enum block")
        return EnumNode(name, values, keyword.location)

    def _parse_module(self, keyword: Token) -> ModuleNode:
        name = self._consume_identifier("Expected module name")
        self._consume(TokenType.FOR, "Expected 'for' after module name")
        entity_name = self._consume_identifier("Expected module entity name")
        if self._match(TokenType.LBRACE):
            self._consume(TokenType.RBRACE, "Routes are generated by convention; module block must be empty")
        return ModuleNode(name, entity_name, keyword.location)

    def _parse_field_block(self, block_name: str) -> list[FieldNode]:
        self._consume(TokenType.LBRACE, f"Expected '{{' after {block_name} name")

        fields = []
        while not self._at(TokenType.RBRACE):
            fields.append(self._parse_field())

        self._consume(TokenType.RBRACE, f"Expected '}}' after {block_name} block")
        return fields

    def _parse_field(self) -> FieldNode:
        name = self._consume_name("Expected field name")
        required = not self._match(TokenType.QUESTION)

        self._consume(TokenType.COLON, "Expected ':' after field name")
        type_name = self._consume_identifier("Expected field type")
        is_array = self._parse_optional_array_suffix()
        annotations = self._parse_annotations()

        return FieldNode(
            name.value,
            type_name,
            required,
            is_array,
            annotations,
            name.location,
        )

    def _parse_optional_array_suffix(self) -> bool:
        if not self._match(TokenType.LBRACKET):
            return False
        self._consume(TokenType.RBRACKET, "Expected ']' after array type")
        return True

    def _parse_annotations(self) -> list[AnnotationNode]:
        annotations = []
        while self._match(TokenType.AT):
            name = self._consume_name("Expected annotation name")
            args = self._parse_annotation_arguments()
            annotations.append(AnnotationNode(name.value, args, name.location))
        return annotations

    def _parse_annotation_arguments(self) -> dict[str, Any]:
        if not self._match(TokenType.LPAREN):
            return {}

        if self._at(TokenType.RPAREN):
            self._advance()
            return {}

        args = self._parse_annotation_argument_values()
        self._consume(TokenType.RPAREN, "Expected ')' after annotation arguments")
        return args

    def _parse_annotation_argument_values(self) -> dict[str, Any]:
        first = self._parse_annotation_value()
        if not self._match(TokenType.COLON):
            return {"value": first}

        args = {str(first): self._parse_annotation_value()}
        while self._match(TokenType.COMMA):
            key = self._consume_identifier("Expected annotation argument name")
            self._consume(TokenType.COLON, "Expected ':' after annotation argument name")
            args[key] = self._parse_annotation_value()
        return args

    def _parse_annotation_value(self) -> Any:
        if self._at(TokenType.STRING):
            self._advance()
            return self._previous().value
        if self._at_any(NAME_TOKENS):
            return self._consume_name("Expected annotation value").value
        if self._match(TokenType.NUMBER):
            value = self._previous().value
            return float(value) if "." in value else int(value)
        raise self._error(self._peek(), "Expected annotation value")

    def _parse_identifier_list(self) -> list[str]:
        self._consume(TokenType.LBRACKET, "Expected '[' before list")

        values = []
        while not self._at(TokenType.RBRACKET):
            values.append(self._consume_identifier("Expected list value"))
            if not self._match(TokenType.COMMA) and not self._at(TokenType.RBRACKET):
                raise self._error(self._peek(), "Expected ',' between list values")

        self._consume(TokenType.RBRACKET, "Expected ']' after list")
        return values

    def _reject_nested_declaration(self, block_name: str = "block") -> None:
        if self._peek().type not in TOP_LEVEL_TOKENS:
            return
        raise self._error(
            self._peek(),
            f"Declaration '{self._peek().value}' is not allowed inside {block_name}",
        )

    def _consume_identifier(self, message: str) -> str:
        return self._consume(TokenType.IDENT, message).value

    def _consume_name(self, message: str) -> Token:
        token = self._peek()
        if token.type in NAME_TOKENS:
            return self._advance()
        raise self._error(token, message)

    def _match(self, *types: TokenType) -> bool:
        if not self._at_any(types):
            return False
        self._advance()
        return True

    def _consume(self, token_type: TokenType, message: str) -> Token:
        if self._at(token_type):
            return self._advance()
        raise self._error(self._peek(), message)

    def _consume_any(self, types: list[TokenType], message: str) -> Token:
        if self._at_any(types):
            return self._advance()
        raise self._error(self._peek(), message)

    def _at(self, token_type: TokenType) -> bool:
        return self._peek().type == token_type

    def _at_any(self, types: tuple[TokenType, ...] | list[TokenType]) -> bool:
        return self._peek().type in types

    def _advance(self) -> Token:
        token = self._peek()
        if token.type != TokenType.EOF:
            self.current += 1
        return token

    def _peek(self) -> Token:
        return self.tokens[self.current]

    def _previous(self) -> Token:
        return self.tokens[self.current - 1]

    def _error(self, token: Token, message: str) -> ParseError:
        return ParseError(message, SourceLocation(token.line, token.column))


def parse(source: str) -> ProgramNode:
    """Parse textual DSL source into a program AST."""
    return Parser(tokenize(source)).parse()
