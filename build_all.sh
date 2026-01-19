#!/bin/bash

# Зупинити скрипт при будь-якій помилці
set -e

echo "--- ЕТАП 1: Валідація конфігів ---"
python check_configs.py

echo "--- ЕТАП 2: Очищення старих збірок ---"
rm -rf build dist Output

echo "--- ЕТАП 3: Запуск PyInstaller ---"
# Використовуємо .spec файл для збереження всіх налаштувань
pyinstaller --noconfirm main.spec

echo "--- ЕТАП 4: Перевірка результату PyInstaller ---"

# Витягуємо назву проекту з .spec файлу
PROJ_NAME=$(grep -m 1 "name=" main.spec | cut -d"'" -f2)

if [ -d "dist/$PROJ_NAME" ]; then
    echo "✅ Підтверджено: Знайдено папку dist/$PROJ_NAME"
else
    echo "❌ Помилка: Папка dist/$PROJ_NAME не знайдена!"
    exit 1
fi

echo "--- ЕТАП 5: Запуск Inno Setup ---"
# Шлях до компилятора Inno Setup (ISCC.exe)
# Зазвичай він знаходиться тут, перевірте свій шлях!
ISCC_PATH="/c/Program Files (x86)/Inno Setup 6/ISCC.exe"

if [ -f "$ISCC_PATH" ]; then
    "$ISCC_PATH" setup_script.iss
else
    echo "⚠️ Попередження: ISCC.exe не знайдено за шляхом $ISCC_PATH"
    echo "Інсталятор не створено, але папка dist/ готовий."
    exit 1
fi

echo "--- ✅ Успішно! Перевірте папку Output/ для отримання інсталятора ---"