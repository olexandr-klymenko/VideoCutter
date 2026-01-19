import unittest
from unittest.mock import patch
from pathlib import Path
import tkinter as tk

# Імпортуємо ваш клас
from main import PureFFmpegTrimmer


class TestVideoCutter(unittest.TestCase):
    def setUp(self):
        """Ініціалізація перед кожним тестом"""
        self.root = tk.Tk()
        self.root.withdraw()  # Ховаємо вікно

        # Патчимо check_ffmpeg, щоб тест не впав, якщо ffmpeg.exe не знайдено
        with patch.object(PureFFmpegTrimmer, 'check_ffmpeg', return_value=True):
            self.app = PureFFmpegTrimmer(self.root)
            self.app.duration = 3661.0  # 1 година, 1 хвилина, 1 секунда

    def tearDown(self):
        """Очищення після тесту"""
        self.root.destroy()

    def test_parse_time_seconds(self):
        """Тест парсингу звичайних секунд"""
        self.assertEqual(self.app.parse_time("90"), 90.0)
        self.assertEqual(self.app.parse_time("120.5"), 120.5)
        self.assertEqual(self.app.parse_time(" 10,5 "), 10.5)  # Перевірка заміни коми

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
        # 90.5 секунд -> 01:30.50
        self.assertEqual(self.app.format_time(90.5), "01:30.50")
        # 3661 секунд -> 61:01.00
        self.assertEqual(self.app.format_time(3661), "61:01.00")

    @patch('subprocess.run')
    def test_trim_command_logic(self, mock_run):
        """Тестуємо формування команди FFmpeg, передаючи значення напряму"""
        # 1. Підготовка
        self.app.video_path = Path("test.mp4")
        save_path = Path("output.mp4")

        # Значення, які ми хочемо протестувати
        start_val = 10.5
        end_val = 25.0

        # 2. Виконання: передаємо значення в іменовані аргументи,
        # які ви додали в run_trim в main.py
        self.app.run_trim(save_path, start_s=start_val, end_s=end_val)

        # 3. Перевірка
        # Дістаємо список аргументів з першого виклику subprocess.run
        args, _ = mock_run.call_args
        cmd = [str(arg) for arg in args[0]]

        # Знаходимо значення в команді
        actual_start = float(cmd[cmd.index('-ss') + 1])
        actual_duration = float(cmd[cmd.index('-t') + 1])

        # Перевіряємо математику (Duration = End - Start)
        self.assertEqual(actual_start, 10.5)
        self.assertEqual(actual_duration, 14.5)  # 25.0 - 10.5 = 14.5

        # Перевіряємо кодек
        self.assertIn('copy', cmd)

    def test_update_entries_sync(self):
        """Перевірка, чи оновлюються текстові поля при зміні слайдерів"""
        self.app.set_ui_state(tk.NORMAL)
        self.app.start_scale.set(45.0)
        self.app.update_entries()

        # В режимі секунд (за замовчуванням) має бути "45.00"
        self.assertEqual(self.app.start_entry.get(), "45.00")


if __name__ == '__main__':
    unittest.main()