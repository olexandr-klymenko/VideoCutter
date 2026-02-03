# -*- coding: utf-8 -*-
import os
import sys
import re
import shutil
from pathlib import Path
from invoke import task

# --- Конфігурація шляхів ---
BASE_DIR = Path(__file__).parent.absolute()
VERSION_FILE = BASE_DIR / "version.txt"
# Переконайся, що шлях до ISCC правильний
ISCC = Path("C:/Program Files (x86)/Inno Setup 6/ISCC.exe")


def get_version():
    """Зчитує чисту версію з файлу."""
    if VERSION_FILE.exists():
        return VERSION_FILE.read_text(encoding="utf-8").strip()
    return "1.0.0"


def _save_version(version_str):
    """Зберігає версію у файл."""
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(version_str)


# --- Задачі тестування ---

@task
def test(c):
    """Запуск тестів з примусовою англійською локаллю та виправленням шляхів"""
    import os, sys
    from pathlib import Path

    print("--- Running Unit Tests (Locale: EN) ---")

    # 1. Знаходимо шлях до оригінального Python (не venv)
    base_python_path = Path(sys._base_executable).parent

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BASE_DIR)

    # 3. Налаштовуємо шляхи Tcl/Tk
    tcl_path = base_python_path / "tcl" / "tcl8.6"
    tk_path = base_python_path / "tcl" / "tk8.6"
    if tcl_path.exists():
        env["TCL_LIBRARY"] = str(tcl_path)
        env["TK_LIBRARY"] = str(tk_path)

    # Запуск з примусовим режимом UTF-8
    cmd = f'"{sys.executable}" -X utf8 -m unittest discover -v -s . -p "test_*.py"'

    c.run(cmd, env=env)
# --- Задачі керування версіями ---

@task
def start_new_release(c):
    """Початок нової версії: інкремент + додавання -beta."""
    current_version = get_version()
    print(f"Поточна версія: {current_version}")

    # Логіка: 1.0.10 -> 1.0.11
    clean_version = current_version.split('-')[0]
    parts = clean_version.split('.')
    if len(parts) >= 1:
        try:
            parts[-1] = str(int(parts[-1]) + 1)
            base_version = ".".join(parts)
        except ValueError:
            base_version = clean_version + ".1"
    else:
        base_version = "1.0.1"

    suggested = f"{base_version}-beta"
    user_input = input(f"Введіть нову версію [{suggested}]: ").strip()
    new_version = user_input if user_input else suggested

    if "-" not in new_version:
        new_version += "-beta"

    _save_version(new_version)
    print(f"✅ Нова версія для розробки: {new_version}")

    if input("Створити коміт 'start release'? [y/N]: ").lower() == 'y':
        c.run("git add version.txt")
        c.run(f'git commit -m "build: start version {new_version}"')


@task
def finish_release(c):
    """Фіналізація релізу: прибирає суфікс -beta."""
    current_version = get_version()
    if "-" not in current_version:
        print(f"⚠️ Версія {current_version} вже фінальна.")
        return

    final_version = current_version.split('-')[0]
    if input(f"Зробити {final_version} фінальним релізом? [Y/n]: ").lower() != 'n':
        _save_version(final_version)
        if input("Зробити коміт 'finish release'? [y/N]: ").lower() == 'y':
            c.run("git add version.txt")
            c.run(f'git commit -m "build: finalize release {final_version}"')
        print(f"🚀 Готово до публікації: {final_version}")


# --- Задачі збірки та публікації ---

@task(pre=[test])
def build(c):
    """Очищення, збірка PyInstaller та Inno Setup з відкриттям результату."""
    print("--- Cleaning build artifacts ---")
    for folder in ['build', 'dist', 'Output']:
        path = BASE_DIR / folder
        if path.exists():
            shutil.rmtree(path)

    version = get_version()
    print(f"--- Building version {version} ---")

    # Запуск PyInstaller
    c.run("pyinstaller --noconfirm main.spec")

    # Запуск Inno Setup
    if ISCC.exists():
        print("--- Running Inno Setup ---")
        result = c.run(f'"{ISCC}" setup_script.iss', warn=True)

        if result.ok:
            output_dir = BASE_DIR / "Output"
            print(f"✅ Installer created in: {output_dir}")

            # Відкриваємо папку з готовим інсталятором
            if os.name == 'nt':  # Тільки для Windows
                os.startfile(output_dir)
        else:
            print("❌ Inno Setup failed!")
    else:
        print(f"⚠️ ISCC not found at {ISCC}. Installer build skipped.")


@task(pre=[test])
def release(c, dry_run=False):
    """Повний цикл: Тести -> Commit -> Tag -> Push."""
    version = get_version()
    tag = f"v{version}"

    if dry_run:
        print(f"🧪 DRY-RUN: Releasing {tag} (build only)")
        build(c)
        return

    print(f"--- Releasing {tag} ---")
    c.run("git add .")
    # Дозволяємо порожній коміт, щоб не переривати скрипт
    c.run(f'git commit -m "feat: release {tag}" || echo "No changes to commit"')

    c.run(f'git tag -a {tag} -m "Release {tag}"')
    c.run("git push origin master --tags")
    print(f"✅ {tag} released and pushed to GitHub!")
