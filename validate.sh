#!/bin/bash
# Pre-push validation script for Nissan NA Home Assistant Integration

set -e

echo "🔍 Running pre-push validation..."
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track errors
ERRORS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
        ERRORS=$((ERRORS + 1))
    fi
}

# 1. Check JSON files
echo "📄 Validating JSON files..."
python3 << 'EOF'
import json
import sys

files = [
    'custom_components/nissan_na/manifest.json',
    'custom_components/nissan_na/strings.json',
    'hacs.json'
]

errors = 0
for file in files:
    try:
        with open(file) as f:
            json.load(f)
        print(f"  ✓ {file}")
    except Exception as e:
        print(f"  ✗ {file}: {e}")
        errors += 1

sys.exit(errors)
EOF
print_status $? "JSON files valid"
echo ""

# 2. Check manifest version
echo "📦 Checking manifest version..."
VERSION=$(python3 -c "import json; print(json.load(open('custom_components/nissan_na/manifest.json'))['version'])")
echo "  Version: $VERSION"
print_status $? "Manifest version: $VERSION"
echo ""

# 3. Run linting
echo "🔧 Running linting..."
pipenv run lint > /dev/null 2>&1
print_status $? "Linting passed"
echo ""

# 4. Run formatting check
echo "📝 Checking code formatting..."
pipenv run format --check > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}  ⚠ Code needs formatting. Run: pipenv run format${NC}"
    ERRORS=$((ERRORS + 1))
else
    print_status 0 "Code formatting correct"
fi
echo ""

# 5. Run tests
echo "🧪 Running tests..."
pipenv run pytest tests/ -q --tb=no > /dev/null 2>&1
TEST_RESULT=$?
if [ $TEST_RESULT -eq 0 ]; then
    TEST_COUNT=$(pipenv run pytest tests/ --co -q 2>/dev/null | tail -1)
    print_status 0 "All tests passed ($TEST_COUNT)"
else
    print_status 1 "Tests failed - run: pipenv run pytest tests/ -v"
fi
echo ""

# 6. Check for common issues
echo "🔍 Checking for common issues..."

# Check for TODO/FIXME comments
if grep -r "TODO\|FIXME" custom_components/nissan_na/*.py > /dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ Found TODO/FIXME comments${NC}"
fi

# Check for debug prints
if grep -r "print(" custom_components/nissan_na/*.py > /dev/null 2>&1; then
    echo -e "${YELLOW}  ⚠ Found print() statements (use _LOGGER instead)${NC}"
fi

# Check manifest dependencies
python3 << 'EOF'
import json
manifest = json.load(open('custom_components/nissan_na/manifest.json'))
required_deps = ['application_credentials', 'http', 'webhook']
deps = manifest.get('dependencies', [])
missing = [d for d in required_deps if d not in deps]
if missing:
    print(f"  ✗ Missing dependencies: {', '.join(missing)}")
    exit(1)
EOF
print_status $? "Required dependencies present"
echo ""

# 7. Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready to push.${NC}"
    exit 0
else
    echo -e "${RED}✗ $ERRORS check(s) failed. Please fix before pushing.${NC}"
    exit 1
fi
