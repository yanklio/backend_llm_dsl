# Textual DSL Achieved Result

## Result

The project now contains a textual DSL compiler frontend that feeds the existing
YAML blueprint and Jinja2 generator pipeline.

```text
Textual DSL -> Lexer -> Parser -> AST -> Resolver -> YAML blueprint -> Jinja2 generator
```

The deterministic Jinja2 generator remains the final code generation phase. The
new compiler does not replace the existing YAML generator and does not introduce
new NestJS template behavior.

## Supported Syntax

The implemented syntax intentionally covers only constructs that can be mapped to
the current blueprint schema:

- `app` root configuration
- `entity` declarations
- scalar and enum fields
- structural `type` declarations
- `dto` declarations validated against entities
- `module ... for ...` declarations
- HTTP route declarations used for semantic validation
- core TypeORM relation annotations
- field annotations for validation and metadata

## Grammar Sketch

```bnf
program      ::= declaration* EOF
declaration  ::= app | entity | enum | type | dto | module
app          ::= "app" IDENT "{" appEntry* "}"
appEntry     ::= "database" ":" IDENT annotation*
               | "features" ":" "[" IDENT ("," IDENT)* "]"
entity       ::= "entity" IDENT "{" field* "}"
type         ::= "type" IDENT "{" field* "}"
enum         ::= "enum" IDENT "{" IDENT* "}"
dto          ::= "dto" IDENT "for" IDENT "{" IDENT* "}"
module       ::= "module" IDENT "for" IDENT "{" route* "}"
field        ::= IDENT "?"? ":" IDENT arraySuffix? annotation*
arraySuffix  ::= "[" "]"
route        ::= "route" httpMethod path "->" IDENT arraySuffix?
httpMethod   ::= "GET" | "POST" | "PATCH" | "DELETE"
annotation   ::= "@" IDENT ("(" annotationArgs? ")")?
```

## Example Input

```text
app UserManagement {
  database: sqlite @path("./data/users.db")
  features: [cors, swagger]
}

entity User {
  email: string @required @email @unique @minLength(5) @maxLength(255)
  name: string @required @minLength(1) @maxLength(100)
}

dto CreateUser for User {
  email
  name
}

module Users for User {
  route GET /users -> User[]
  route POST /users -> User
  route PATCH /users/:id -> User
  route DELETE /users/:id -> void
}
```

## Example Output Shape

```yaml
root:
  name: UserManagement
  database:
    type: sqlite
    database: ./data/users.db
    synchronize: true
    logging: false
  features:
    cors: true
    swagger: true
modules:
  - name: User
    generate: [controller, service, module, entity, dto]
    entity:
      fields:
        - name: email
          type: string
          required: true
          unique: true
          validation:
            isEmail: true
            minLength: 5
            maxLength: 255
      relations: []
```

## Compiler Stages

- Lexer: converts source text into tokens with `line` and `column` locations.
- Parser: builds a direct AST without a separate parse tree.
- AST: represents applications, entities, fields, modules, routes, DTOs, enums,
  and types.
- Resolver: validates semantic correctness before generation.
- Emitter: converts the resolved AST into the existing YAML blueprint shape.

## Resolver Error Codes

- `RESOLVE_E001`: duplicate symbol or duplicate field
- `RESOLVE_E002`: unknown field type or relation target
- `RESOLVE_E003`: module or DTO references an unknown entity
- `RESOLVE_E004`: DTO field does not exist on its target entity
- `RESOLVE_E005`: route returns an unknown type

## Scope Boundary

HTTP route declarations are parsed and semantically validated, but they do not
customize generated controllers yet. This preserves the existing generator as a
deterministic CRUD backend generator and avoids changing the thesis experiment's
generation surface.
