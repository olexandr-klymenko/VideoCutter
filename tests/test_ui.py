# -*- mode: python ; coding: utf-8 -*-
import sys
import tkinter as tk
import unittest
from pathlib import Path
from unittest.mock import patch

# Додаємо корінь проєкту до sys.path, щоб імпорти src. працювали
project_root = Path(__file__).parent
if (project_root / "src").exists():
    sys.path.insert(0, str(project_root))

# Імпортуємо з оновленої структури
from src.ui import PureFFmpegTrimmer


class TestVideoCutter(unittest.TestCase):
    def setUp(self):
        """Ініціалізація перед кожним тестом"""
        self.root = tk.Tk()
        self.root.withdraw()

        # Патчимо ініціалізацію, щоб не залежати від наявності ffmpeg.exe
        # та не запускати перевірку оновлень через мережу
        with patch('src.ui.PureFFmpegTrimmer.check_for_updates'):
            self.app = PureFFmpegTrimmer(self.root)
            self.app.duration = 3661.0

    def tearDown(self):
        """Очищення після тесту"""
        self.root.destroy()

    ## --- Тести логіки парсингу ---

    def test_parse_time_seconds(self):
        """Тест парсингу звичайних секунд"""
        self.assertEqual(self.app.parse_time("90"), 90.0)
        self.assertEqual(self.app.parse_time("120.5"), 120.5)
        self.assertEqual(self.app.parse_time(" 10,5 "), 10.5)

    def test_parse_time_minutes(self):
        """Тест парсингу формату MM:SS"""
        self.assertEqual(self.app.parse_time("01:30"), 90.0)
        self.assertEqual(self.app.parse_time("10:00"), 600.0)
        self.assertEqual(self.app.parse_time("00:05.50"), 5.5)

    def test_format_time_simple(self):
        """Тест форматування в режимі секунд"""
        self.app.is_minutes_mode.set(False)
        self.assertEqual(self.app.format_time(90.5), "90.50")

    def test_format_time_minutes(self):
        """Тест форматування в режимі MM:SS"""
        self.app.is_minutes_mode.set(True)
        self.assertEqual(self.app.format_time(90.5), "01:30.50")
        self.assertEqual(self.app.format_time(3661), "61:01.00")

    ## --- Тести UI синхронізації ---

    def test_update_entries_sync(self):
        """Перевірка, чи оновлюються текстові поля при зміні слайдерів"""
        self.app.set_ui_state(tk.NORMAL)
        self.app.start_scale.set(45.0)
        self.app.update_entries()
        self.assertEqual(self.app.start_entry.get(), "45.00")

    ## --- Тести команд FFmpeg ---

    @patch('subprocess.run')
    def test_trim_command_logic(self, mock_run):
        self.app.video_path = Path("test.mp4")
        save_path = Path("output.mp4")

        # Передаємо значення прямо в метод
        self.app.run_trim(save_path, start_s=10.5, end_s=25.0)

        args, _ = mock_run.call_args
        cmd = [str(arg) for arg in args[0]]

        actual_start = float(cmd[cmd.index('-ss') + 1])
        self.assertEqual(actual_start, 10.5)


if __name__ == '__main__':
    unittest.main()
