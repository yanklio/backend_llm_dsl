#!/bin/bash

# regenerate.sh
# Script to delete src directory and regenerate NestJS code from blueprint

set -e  

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

BLUEPRINT_FILE="${1:-blueprint.yaml}"

BLUEPRINT_NAME=$(basename "$BLUEPRINT_FILE" .yaml)

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NestJS Project Regeneration Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ ! -f "$BLUEPRINT_FILE" ]; then
    echo -e "${RED}Error: Blueprint file '$BLUEPRINT_FILE' not found!${NC}"
    echo -e "${YELLOW}Usage: $0 [blueprint_file.yaml]${NC}"
    exit 1
fi

echo -e "${BLUE}Blueprint:${NC} $BLUEPRINT_FILE"
echo -e "${BLUE}Blueprint name:${NC} $BLUEPRINT_NAME"
echo ""


if [ ! -d "nest_project" ]; then
    echo -e "${RED}Error: nest_project directory not found!${NC}"
    exit 1
fi

if [ -d "nest_project/src" ]; then
    echo -e "${YELLOW}Deleting nest_project/src directory...${NC}"
    rm -rf nest_project/src
    echo -e "${GREEN}✓ Deleted nest_project/src${NC}"
else
    echo -e "${YELLOW}⚠ nest_project/src directory not found, skipping deletion${NC}"
fi

echo ""