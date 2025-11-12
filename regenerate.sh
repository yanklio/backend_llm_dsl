#!/bin/bash

# regenerate.sh
# Script to delete src directory and regenerate NestJS code from blueprint

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the blueprint file path from argument or use default
BLUEPRINT_FILE="${1:-blueprint.yaml}"

# Extract the base name without extension (e.g., "blueprint.yaml" -> "blueprint")
BLUEPRINT_NAME=$(basename "$BLUEPRINT_FILE" .yaml)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NestJS Project Regeneration Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if blueprint file exists
if [ ! -f "$BLUEPRINT_FILE" ]; then
    echo -e "${RED}Error: Blueprint file '$BLUEPRINT_FILE' not found!${NC}"
    echo -e "${YELLOW}Usage: $0 [blueprint_file.yaml]${NC}"
    exit 1
fi

echo -e "${BLUE}Blueprint:${NC} $BLUEPRINT_FILE"
echo -e "${BLUE}Blueprint name:${NC} $BLUEPRINT_NAME"
echo ""

# Check if nest_project directory exists
if [ ! -d "nest_project" ]; then
    echo -e "${RED}Error: nest_project directory not found!${NC}"
    exit 1
fi

# Delete src directory
if [ -d "nest_project/src" ]; then
    echo -e "${YELLOW}Deleting nest_project/src directory...${NC}"
    rm -rf nest_project/src
    echo -e "${GREEN}✓ Deleted nest_project/src${NC}"
else
    echo -e "${YELLOW}⚠ nest_project/src directory not found, skipping deletion${NC}"
fi

echo ""

# Run the Python generator script
echo -e "${BLUE}Generating new code from blueprint...${NC}"
echo ""

if [ -f "generate.py" ]; then
    python3 generate.py "$BLUEPRINT_FILE"

    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}✓ Regeneration completed successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
    else
        echo ""
        echo -e "${RED}========================================${NC}"
        echo -e "${RED}✗ Generation failed!${NC}"
        echo -e "${RED}========================================${NC}"
        exit 1
    fi
else
    echo -e "${RED}Error: generate.py not found!${NC}"
    exit 1
fi
