# NestJS Code Generator

A template-based code generator for NestJS applications using Jinja2 templates and YAML blueprints.

## Overview

This project provides a flexible code generation system that creates complete NestJS applications with TypeORM integration based on YAML configuration files. It uses Jinja2 templates to generate controllers, services, modules, DTOs, and entities.

## Features

- 🚀 **Automated Code Generation** - Generate complete NestJS modules from YAML blueprints
- 📝 **Template-Based** - Customizable Jinja2 templates for all generated files
- 🗄️ **TypeORM Integration** - Automatic entity generation with database support
- 🔄 **DTO Generation** - Auto-generated DTOs with validation decorators
- 📚 **Swagger Support** - Built-in API documentation with @ApiProperty decorators
- 🎯 **Type-Safe** - TypeScript types and validation out of the box

## Project Structure

```
Practice/
├── templates/              # Jinja2 templates
│   ├── dto/               # DTO templates
│   │   ├── create-dto.ts.j2
│   │   └── update-dto.ts.j2
│   ├── root/              # Root module templates
│   │   ├── app.module.ts.j2
│   │   ├── app.controller.ts.j2
│   │   ├── app.service.ts.j2
│   │   ├── main.ts.j2
│   │   └── database.config.ts.j2
│   ├── entity.ts.j2       # Entity template
│   ├── controller.ts.j2   # Controller template
│   ├── service.ts.j2      # Service template
│   └── module.ts.j2       # Module template
├── nest_project/          # Generated NestJS application
│   └── src/               # Generated source code
├── blueprint.yaml         # YAML configuration file
├── generate.py            # Code generator script
└── regenerate.sh          # Regeneration helper script
```

## Usage

### 1. Define Your Blueprint

Create or edit `blueprint.yaml` to define your application structure:

```yaml
root:
  name: MyApp
  database:
    type: sqlite
    database: ./data/app.db
    synchronize: true
    logging: false

modules:
  - name: Product
    entity:
      fields:
        - name: name
          type: string
          required: true
          validation:
            minLength: 3
            maxLength: 100
        - name: price
          type: number
          required: true
    generate:
      - entity
      - dto
      - service
      - controller
      - module
```

### 2. Generate Code

Run the generator script:

```bash
python3 generate.py blueprint.yaml
```

Or use the regeneration script (deletes existing src and regenerates):

```bash
./regenerate.sh blueprint.yaml
```

### 3. Run the Application

```bash
cd nest_project
npm install
npm run start:dev
```

## Generated Code Features

### Entities
- TypeORM decorators (@Entity, @Column, etc.)
- Automatic timestamps (createdAt, updatedAt)
- Type-safe field definitions

### DTOs
- class-validator decorators (@IsString, @IsNotEmpty, etc.)
- Swagger/OpenAPI decorators (@ApiProperty)
- Validation rules from blueprint

### Controllers
- CRUD endpoints (GET, POST, PATCH, DELETE)
- Swagger documentation
- Proper HTTP status codes

### Services
- Repository pattern with TypeORM
- CRUD operations
- Type-safe methods

## Requirements

- Python 3.x
- Jinja2
- PyYAML
- Node.js & npm (for running the generated NestJS app)

## Installation

```bash
# Install Python dependencies
pip install jinja2 pyyaml

# Make regeneration script executable
chmod +x regenerate.sh
```

## Blueprint Configuration

### Root Configuration
- `name`: Application name
- `database`: Database configuration (type, path, options)

### Module Configuration
- `name`: Module name (e.g., Product, User, Category)
- `entity.fields`: Array of field definitions
  - `name`: Field name
  - `type`: Field type (string, number, boolean, enum)
  - `required`: Whether field is required
  - `validation`: Validation rules (minLength, maxLength, min, max, etc.)
  - `description`: Field description for Swagger
  - `example`: Example value for Swagger
- `generate`: List of files to generate (entity, dto, service, controller, module)
