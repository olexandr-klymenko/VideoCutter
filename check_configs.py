import os
import re
import sys

REQUIREMENTS_TXT = "requirements.txt"
VERSION_TXT = "version.txt"


def check_file_exists(filepath):
    if os.path.exists(filepath):
        print(f"✅ Знайдено: {filepath}")
        return True
    print(f"❌ ПОМИЛКА: {filepath} не знайдено!")
    return False


def validate_configs():
    success = True
    print("--- Перевірка конфігурації перед релізом ---")

    # 1. Перевірка version.txt
    if check_file_exists(VERSION_TXT):
        # Додано encoding='utf-8'
        with open(VERSION_TXT, "r", encoding='utf-8') as f:
            version = f.read().strip()
            if not re.match(r"^\d+\.\d+\.\d+$", version):
                print(f"⚠️  УВАГА: Формат версії '{version}' має бути x.x.x")
    else:
        success = False

    # 2. Перевірка main.spec (PyInstaller)
    if check_file_exists("main.spec"):
        # Додано encoding='utf-8' для уникнення UnicodeDecodeError
        with open("main.spec", "r", encoding='utf-8') as f:
            content = f.read()
            if VERSION_TXT not in content:
                print("❌ ПОМИЛКА: version.txt не додано в 'datas' у main.spec!")
                success = False
            if "ffmpeg.exe" not in content:
                print("❌ ПОМИЛКА: ffmpeg.exe не знайдено в конфігу main.spec!")
                success = False

    # 3. Перевірка setup_script.iss (Inno Setup)
    if check_file_exists("setup_script.iss"):
        # Inno Setup часто використовує UTF-8 або ANSI з BOM
        with open("setup_script.iss", "r", encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if VERSION_TXT not in content and "AppVersionStr" not in content:
                print("❌ ПОМИЛКА: setup_script.iss не підтягує версію з файлу!")
                success = False

    # 4. Перевірка бібліотек у requirements.txt
    if check_file_exists(REQUIREMENTS_TXT):
        # utf-8-sig допомагає, якщо файл у UTF-8 з BOM або UTF-16
        try:
            with open(REQUIREMENTS_TXT, "r", encoding='utf-8-sig') as f:
                libs = f.read().lower()
        except UnicodeDecodeError:
            # Якщо все ж таки UTF-16 (PowerShell default)
            with open(REQUIREMENTS_TXT, "r", encoding='utf-16') as f:
                libs = f.read().lower()

        for lib in ["requests", "pillow", "pyinstaller"]:
            if lib not in libs:
                print(f"❌ ПОМИЛКА: Бібліотека '{lib}' відсутня в requirements.txt!")
                success = False

    print("---------------------------------------")
    if success:
        print("🚀 Конфіги перевірено. Все готово до релізу!")
        sys.exit(0)
    else:
        print("🛑 Помилка! Виправте конфігураційні файли.")
        sys.exit(1)


if __name__ == "__main__":
    validate_configs()
