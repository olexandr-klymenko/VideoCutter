#!/bin/bash

# Зупинити скрипт при будь-якій помилці
set -e

# Перевірка на параметр dry-run
DRY_RUN=false
if [[ "$1" == "--dry-run" ]]; then
    DRY_RUN=true
    echo "🧪 RUNNING IN DRY-RUN MODE (No Git changes will be made)"
fi

# 1. Валідація конфігурації
echo "--- Step 1: Validating configurations ---"
python check_configs.py

# 2. Запуск юніт-тестів
echo "--- Step 2: Running Unit Tests ---"
python -m unittest test_logic.py
echo "✅ All tests passed!"

# 3. Зчитування версії
VERSION=$(sed -e 's/[[:space:]]//g' version.txt)
TAG="v$VERSION"
echo "--- Step 3: Preparing release $TAG ---"

# 4. Перевірка Git (тільки якщо не dry-run)
if [ "$DRY_RUN" = false ]; then
    git fetch --tags
    if git rev-parse "$TAG" >/dev/null 2>&1; then
        echo "❌ Error: Tag $TAG already exists in Git. Update version.txt first."
        exit 1
    fi
fi

# 5. Локальна збірка (PyInstaller + Inno Setup)
echo "--- Step 4: Local Build Process ---"
rm -rf build dist Output

echo "Running PyInstaller..."
pyinstaller --noconfirm main.spec

# Шлях до компилятора Inno Setup (перевірте, чи він збігається з вашим)
ISCC_PATH="/c/Program Files (x86)/Inno Setup 6/ISCC.exe"
if [ -f "$ISCC_PATH" ]; then
    echo "Running Inno Setup..."
    "$ISCC_PATH" setup_script.iss
    echo "✅ Installer created successfully in Output/ folder."
else
    echo "⚠️ Warning: ISCC.exe not found at $ISCC_PATH. Local installer skipped."
fi

# 6. Очищення тимчасових файлів
echo "Cleaning up build artifacts..."
rm -rf build dist

# 7. Пуш у GitHub (Тільки якщо НЕ dry-run)
if [ "$DRY_RUN" = false ]; then
    echo "--- Step 5: Pushing to GitHub ---"
    git add .
    git commit -m "release: $TAG (automated build with tests)"
    git tag -a "$TAG" -m "Release $TAG"

    echo "Pushing master and tags..."
    git push origin master
    git push origin "$TAG"
    echo "--- ✅ COMPLETE! Version $TAG is released and pushed. ---"
else
    echo "--- ✨ DRY-RUN COMPLETE! ---"
    echo "Local installer is ready in 'Output/' folder."
    echo "Tests passed, configuration is valid. No Git changes made."
fi