import os
import re
import sys

REQUIREMENTS_TXT = "requirements.txt"
VERSION_TXT = "version.txt"


def check_file_exists(filepath):
    """Helper to verify file presence."""
    exists = os.path.exists(filepath)
    status = "✅ Знайдено" if exists else "❌ ПОМИЛКА"
    print(f"{status}: {filepath}")
    return exists


def validate_version_format():
    """Checks version.txt format."""
    if not check_file_exists(VERSION_TXT):
        return False
    with open(VERSION_TXT, "r", encoding='utf-8') as f:
        version = f.read().strip()
    if not re.match(r"^\d+\.\d+\.\d+$", version):
        print(f"⚠️  УВАГА: Формат версії '{version}' має бути x.x.x")
    return True


def validate_pyinstaller_spec():
    """Checks main.spec content."""
    if not check_file_exists("main.spec"):
        return True  # Not strictly required for success? Adjust if needed.

    with open("main.spec", "r", encoding='utf-8') as f:
        content = f.read()

    checks = {
        VERSION_TXT: "❌ ПОМИЛКА: version.txt не додано в 'datas' у main.spec!",
        "ffmpeg.exe": "❌ ПОМИЛКА: ffmpeg.exe не знайдено в конфігу main.spec!"
    }

    success = True
    for key, error_msg in checks.items():
        if key not in content:
            print(error_msg)
            success = False
    return success


def validate_inno_setup():
    """Checks setup_script.iss content."""
    if not check_file_exists("setup_script.iss"):
        return True

    with open("setup_script.iss", "r", encoding='utf-8', errors='ignore') as f:
        content = f.read()

    if VERSION_TXT not in content and "AppVersionStr" not in content:
        print("❌ ПОМИЛКА: setup_script.iss не підтягує версію з файлу!")
        return False
    return True


def validate_requirements():
    """Checks requirements.txt dependencies with encoding fallback."""
    if not check_file_exists(REQUIREMENTS_TXT):
        return False

    libs = ""
    for enc in ['utf-8-sig', 'utf-16']:
        try:
            with open(REQUIREMENTS_TXT, "r", encoding=enc) as f:
                libs = f.read().lower()
                break
        except UnicodeError:
            continue

    required = ["requests", "pillow", "pyinstaller"]
    missing = [lib for lib in required if lib not in libs]

    for lib in missing:
        print(f"❌ ПОМИЛКА: Бібліотека '{lib}' відсутня в requirements.txt!")

    return len(missing) == 0


def validate_configs():
    """Main orchestrator with significantly reduced complexity."""
    print("--- Перевірка конфігурації перед релізом ---")

    # List of validation steps
    results = [
        validate_version_format(),
        validate_pyinstaller_spec(),
        validate_inno_setup(),
        validate_requirements()
    ]

    print("---------------------------------------")
    if all(results):
        print("🚀 Конфіги перевірено. Все готово до релізу!")
        sys.exit(0)

    print("🛑 Помилка! Виправте конфігураційні файли.")
    sys.exit(1)


if __name__ == "__main__":
    validate_configs()