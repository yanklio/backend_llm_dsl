#!/bin/bash
# Demo Automation Script
# Runs complete metrics collection and visualization for thesis demo

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  DSL-Based Code Generation: Metrics Collection & Visualization ║"
echo "╔════════════════════════════════════════════════════════════════╗"
echo ""

# Configuration
OUTPUT_DIR="./metrics_output"
RUNS_PER_TEST=5

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Setup
echo -e "${BLUE}[1/4] Setting up environment...${NC}"
mkdir -p "$OUTPUT_DIR"
echo "✓ Output directory created: $OUTPUT_DIR"
echo ""

# Step 2: Collect Metrics
echo -e "${BLUE}[2/4] Collecting metrics (this may take a few minutes)...${NC}"
echo "      Running $RUNS_PER_TEST iterations per test case"
echo ""

python3 metrics_collector.py \
    --output "$OUTPUT_DIR" \
    --runs "$RUNS_PER_TEST"

echo ""
echo -e "${GREEN}✓ Metrics collection complete${NC}"
echo ""

# Step 3: Generate Visualizations
echo -e "${BLUE}[3/4] Generating visualizations...${NC}"
echo ""

python3 visualize_metrics.py \
    --input "$OUTPUT_DIR/metrics_results.json" \
    --output "$OUTPUT_DIR"

echo ""
echo -e "${GREEN}✓ Visualizations generated${NC}"
echo ""

# Step 4: Display Summary
echo -e "${BLUE}[4/4] Summary Report${NC}"
echo "════════════════════════════════════════════════════════════════"
cat "$OUTPUT_DIR/metrics_summary.txt"
echo "════════════════════════════════════════════════════════════════"
echo ""

# List generated files
echo -e "${YELLOW}Generated Files:${NC}"
echo ""
echo "📊 Metrics Data:"
echo "   - $OUTPUT_DIR/metrics_results.json"
echo "   - $OUTPUT_DIR/metrics_summary.txt"
echo ""
echo "📈 Visualizations:"
for img in "$OUTPUT_DIR"/*.png; do
    if [ -f "$img" ]; then
        echo "   - $(basename "$img")"
    fi
done
echo ""

# Final instructions
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Demo Ready!                                 ║${NC}"
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo ""
echo "Next steps for your demo:"
echo ""
echo "1. View graphs:"
echo "   Open the PNG files in $OUTPUT_DIR/"
echo ""
echo "2. Review metrics:"
echo "   cat $OUTPUT_DIR/metrics_summary.txt"
echo ""
echo "3. Show raw data:"
echo "   cat $OUTPUT_DIR/metrics_results.json | jq"
echo ""
echo "4. Include in presentation:"
echo "   - Use the graphs to show consistency improvements"
echo "   - Reference the metrics in your talking points"
echo "   - Show the comparison chart (dsl_comparison.png)"
echo ""
echo "Good luck with your demo! 🚀"
