import ctypes
import io
import re
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import requests
from PIL import Image, ImageTk

BUTTON_RELEASE_ = "<ButtonRelease-1>"
SEGOE_UI = "Segoe UI"
ERROR_STR = "Помилка"


# Функція для отримання шляху до файлів (враховує PyInstaller onedir)
def get_resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


# Читаємо версію з файлу
def get_current_version():
    try:
        with open(get_resource_path("version.txt"), "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0-dev"


VERSION = f"v{get_current_version()}"
REPO_OWNER = "olexandr-klymenko"
REPO_NAME = "VideoCutter"


def check_for_updates():
    """Функція для перевірки оновлень через GitHub API"""
    try:
        api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
        response = requests.get(api_url, timeout=5)
        if response.status_code == 200:
            data = response.json()
            latest_version = data.get("tag_name", "")

            if latest_version and latest_version != VERSION:
                root.after(0, lambda: show_update_dialog(latest_version))
    except Exception as e:
        print(f"Update check failed: {e}")


def show_update_dialog(new_version):
    download_url = f"https://github.com/{REPO_OWNER}/{REPO_NAME}/releases/latest"
    msg = f"Доступна нова версія: {new_version}\nПоточна версія: {VERSION}\n\nБажаєте перейти до завантаження?"
    if messagebox.askyesno("Знайдено оновлення", msg):
        webbrowser.open(download_url)


def set_dpi_awareness():
    """ Sets DPI awareness using the best available Windows API. """
    # Define the calls in order of preference (Modern -> Legacy)
    dpi_calls = [
        lambda: ctypes.windll.shcore.SetProcessDpiAwareness(1),  # Win 8.1+
        lambda: ctypes.windll.user32.SetProcessDPIAware()  # Win Vista+
    ]

    for call in dpi_calls:
        try:
            call()
            return  # Exit once a method succeeds
        except (AttributeError, OSError):
            continue  # Try the next method if this one isn't available


if hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

FFMPEG_BIN = BASE_DIR / "bin" / "ffmpeg.exe"


def get_resource_path(relative_path: str) -> Path:
    """Отримує абсолютний шлях до ресурсу, працює для dev та для PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller створює тимчасову папку і зберігає шлях у _MEIPASS
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent

    return base_path / relative_path


class PureFFmpegTrimmer:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Pro Video Trimmer 🎬 {VERSION}")

        self.ffmpeg_version = "Невідомо"

        if not self.check_ffmpeg():
            self.root.withdraw()
            messagebox.showerror(
                ERROR_STR,
                f"Не знайдено або пошкоджено файл ffmpeg.exe за шляхом:\n{FFMPEG_BIN.absolute()}"
            )
            self.root.destroy()
            return

        self.video_path = None
        self.duration = 0.0
        self.last_img = None
        self.current_t = 0.0
        self.is_minutes_mode = tk.BooleanVar(value=False)

        self.after_id = None
        self.repeat_delay = 100

        self.interactive_widgets = []
        self.setup_ui()
        self.canvas.bind("<Configure>", self.on_resize)

        self.version_label = tk.Label(root, text=f"Версія: {VERSION}", fg="gray")
        self.version_label.pack(side="bottom", anchor="e", padx=10, pady=5)

        icon_path = get_resource_path("icon.ico")
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

        update_thread = threading.Thread(target=check_for_updates, daemon=True)
        update_thread.start()

    def check_ffmpeg(self) -> bool:
        """Перевірка та отримання версії ffmpeg."""
        if not FFMPEG_BIN.exists():
            return False
        try:
            # Отримуємо перший рядок виводу ffmpeg -version
            result = subprocess.run(
                [str(FFMPEG_BIN), "-version"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,
                check=True
            )
            first_line = result.stdout.splitlines()[0]
            # Витягуємо версію (наприклад, "ffmpeg version 7.0.1...")
            match = re.search(r"version\s+([^\s,]+)", first_line)
            self.ffmpeg_version = match.group(1) if match else "Виявлено"
            return True
        except (subprocess.CalledProcessError, OSError, IndexError):
            return False

    def setup_ui(self):
        self.root.option_add("*Font", (SEGOE_UI, 9))
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)  # Додаємо мінімальний розмір вікна

        controls = tk.Frame(self.root, pady=10, padx=10)
        controls.pack(side="top", fill="x")

        # --- Верхня панель ---
        btn_frame = tk.Frame(controls)
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text="📁 Відкрити відео", command=self.load_video).pack(side="left", padx=5)

        self.mode_check = tk.Checkbutton(btn_frame, text="Хвилини (MM:SS)", variable=self.is_minutes_mode,
                                         command=self.toggle_format, state=tk.DISABLED)
        self.mode_check.pack(side="left", padx=15)
        self.interactive_widgets.append(self.mode_check)

        # Інфо-панель (Версія програми та FFmpeg)
        info_frame = tk.Frame(btn_frame)
        info_frame.pack(side="left", padx=10)

        tk.Label(info_frame, text=f"App: {VERSION}", fg="#888888", font=(SEGOE_UI, 8)).pack(side="top", anchor="w")
        tk.Label(info_frame, text=f"FFmpeg: {self.ffmpeg_version}", fg="#888888", font=(SEGOE_UI, 8)).pack(side="top",
                                                                                                           anchor="w")

        self.btn_trim = tk.Button(btn_frame, text="✂️ ОБРІЗАТИ", bg="#28a745", fg="white",
                                  font=(SEGOE_UI, 9, "bold"), command=self.start_trim_thread, state=tk.DISABLED)
        self.btn_trim.pack(side="right", padx=5)
        self.interactive_widgets.append(self.btn_trim)

        # --- Слайдери ---
        self.start_scale, self.start_entry = self.create_time_control(controls, "ПОЧАТОК")
        self.end_scale, self.end_entry = self.create_time_control(controls, "КІНЕЦЬ")

        # --- Новий рядок: Інформація про результат ---
        self.result_info_label = tk.Label(controls, text="Тривалість фрагмента: 0.00 сек",
                                          font=(SEGOE_UI, 9, "bold"), fg="#0056b3")
        self.result_info_label.pack(pady=2)

        # Статус
        self.status_label = tk.Label(controls, text="Очікування файлу...", font=("Consolas", 10), fg="gray")
        self.status_label.pack(pady=5)

        # Полотно для відео
        self.canvas = tk.Label(self.root, bg="#1a1a1a")
        self.canvas.pack(expand=True, fill="both")

    def create_time_control(self, parent, label_text):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=label_text, width=10, anchor="w").pack(side="left")

        scale = tk.Scale(frame, orient="horizontal", from_=0, to=100, resolution=0.01, showvalue=False,
                         state=tk.DISABLED,
                         command=lambda _: self.update_entries())  # Додано автоматичне оновлення
        scale.pack(side="left", fill="x", expand=True, padx=5)

        scale.bind("<Button-1>", lambda e: self.jump_to_click(e, scale) if scale['state'] != tk.DISABLED else None)
        scale.bind(BUTTON_RELEASE_,
                   lambda e: self.update_preview(scale.get()) if scale['state'] != tk.DISABLED else None)

        entry = tk.Entry(frame, width=10, justify='center', state=tk.DISABLED)
        entry.pack(side="left", padx=5)
        entry.bind('<Return>', lambda e: self.on_entry_change(scale, entry))

        fine_frame = tk.Frame(frame)
        fine_frame.pack(side="right")

        btn_minus = tk.Button(fine_frame, text="-0.1", width=4, state=tk.DISABLED)
        btn_minus.pack(side="left", padx=1)
        btn_plus = tk.Button(fine_frame, text="+0.1", width=4, state=tk.DISABLED)
        btn_plus.pack(side="left", padx=1)

        btn_minus.bind("<ButtonPress-1>", lambda e: self.start_auto_adjust(scale, -0.1))
        btn_minus.bind(BUTTON_RELEASE_, lambda e: self.stop_auto_adjust())
        btn_plus.bind("<ButtonPress-1>", lambda e: self.start_auto_adjust(scale, 0.1))
        btn_plus.bind(BUTTON_RELEASE_, lambda e: self.stop_auto_adjust())

        self.interactive_widgets.extend([scale, entry, btn_minus, btn_plus])
        return scale, entry

    def start_auto_adjust(self, scale, delta):
        self.adjust_time(scale, delta)
        self.after_id = self.root.after(400, lambda: self.repeat_adjust(scale, delta))

    def repeat_adjust(self, scale, delta):
        self.adjust_time(scale, delta)
        self.after_id = self.root.after(self.repeat_delay, lambda: self.repeat_adjust(scale, delta))

    def stop_auto_adjust(self):
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def adjust_time(self, scale, delta):
        new_val = max(0, min(scale.get() + delta, self.duration))
        scale.set(new_val)
        self.update_entries()
        self.update_preview(new_val)

    def set_ui_state(self, state):
        for widget in self.interactive_widgets:
            widget.config(state=state)

    def load_video(self):
        if not FFMPEG_BIN.exists():
            messagebox.showerror(ERROR_STR, "FFmpeg не знайдено!")
            return

        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if not file_path: return

        self.video_path = Path(file_path).resolve()
        cmd = [str(FFMPEG_BIN), "-hide_banner", "-i", str(self.video_path)]
        try:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore',
                                 creationflags=0x08000000)
            _, err = p.communicate()
            match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", err)
            if match:
                h, m, s = map(float, match.groups())
                self.duration = h * 3600 + m * 60 + s
                self.set_ui_state(tk.NORMAL)
                for scale in [self.start_scale, self.end_scale]:
                    scale.config(to=self.duration)
                self.start_scale.set(0)
                self.end_scale.set(self.duration)
                self.update_entries()
                self.update_preview(0)
                self.update_entries()
        except Exception as e:
            messagebox.showerror(ERROR_STR, f"Не вдалося прочитати файл: {e}")

    def format_time(self, seconds):
        if not self.is_minutes_mode.get(): return f"{seconds:.2f}"
        m, s = int(seconds // 60), seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def parse_time(self, string):
        string = string.replace(',', '.').strip()
        if ":" in string:
            parts = string.split(":")
            if len(parts) == 2: return int(parts[0]) * 60 + float(parts[1])
        return float(string)

    def toggle_format(self):
        self.update_entries()
        self.status_label.config(
            text=f"Позиція: {self.format_time(self.current_t)} / {self.format_time(self.duration)}", fg="black")

    def jump_to_click(self, event, scale):
        length = scale.winfo_width() - 16
        val = (max(0, min(1, (event.x - 8) / length))) * scale.cget("to")
        scale.set(val)
        self.update_preview(val)

    def on_entry_change(self, scale, entry):
        # 1. Early return (Guard Clause) to reduce nesting
        if entry['state'] == tk.DISABLED:
            return

        try:
            # 2. Specific logic extraction
            raw_value = entry.get()
            time_val = self.parse_time(raw_value)

            # Clamp value within bounds
            clamped_val = max(0, min(time_val, self.duration))

            scale.set(clamped_val)
            self.update_preview(clamped_val)

        except (ValueError, TypeError, KeyError) as err:
            print(err)
            # 3. Catch specific exceptions instead of a bare 'except:'
            # This prevents masking system exits or memory errors
            self.update_entries()

    def update_entries(self):
        for entry, scale in [(self.start_entry, self.start_scale), (self.end_entry, self.end_scale)]:
            if entry['state'] != tk.DISABLED:
                entry.delete(0, tk.END)
                entry.insert(0, self.format_time(scale.get()))

        # Викликаємо оновлення тривалості
        self.refresh_duration_info()

    def refresh_duration_info(self):
        """Окремий метод для оновлення інфо-лейбла тривалості фрагмента"""
        diff = self.end_scale.get() - self.start_scale.get()
        mode_suffix = "хв:сек" if self.is_minutes_mode.get() else "сек."

        if diff < 0:
            self.result_info_label.config(text="⚠️ Помилка: Початок більший за кінець!", fg="red")
            self.btn_trim.config(state=tk.DISABLED)  # Блокуємо кнопку обрізки
        else:
            # Використовуємо format_time для чисел, але додаємо пояснення одиниць
            self.result_info_label.config(
                text=f"Тривалість фрагмента: {self.format_time(diff)} {mode_suffix}",
                fg="#0056b3"
            )
            if self.video_path:  # Повертаємо кнопку в робочий стан
                self.btn_trim.config(state=tk.NORMAL)

    def update_preview(self, t):
        if not self.video_path or not FFMPEG_BIN.exists(): return
        self.current_t = t
        self.status_label.config(text="⌛ Рендеринг...", fg="blue")
        threading.Thread(target=self._render_task, args=(t,), daemon=True).start()

    def _render_task(self, t):
        # Додаємо унікальний маркер для поточного завдання
        cmd = [
            str(FFMPEG_BIN),
            '-ss', str(round(t, 3)),
            '-i', str(self.video_path),
            '-vframes', '1',  # Отримати рівно один кадр
            '-q:v', '4',  # Трохи знизимо якість MJPEG для швидкості
            '-f', 'image2pipe',
            '-vcodec', 'mjpeg',
            '-loglevel', 'quiet',
            '-'
        ]

        p = None
        try:
            p = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                creationflags=0x08000000
            )

            # Встановлюємо жорсткий таймаут
            data, _ = p.communicate(timeout=1.0)

            # Specific check for data presence and size
            if not data or len(data) <= 500:
                raise ValueError(f"Received insufficient data from subprocess: {len(data) if data else 0} bytes")

            image = Image.open(io.BytesIO(data))
            self.root.after(0, lambda: self.display_image(image, t))

        except subprocess.TimeoutExpired:
            if p:
                p.kill()
                p.wait()
            # Повертаємо червоний напис про таймаут
            self.root.after(0, lambda: self.status_label.config(
                text=f"🛑 ТАЙМАУТ: Кадр на {self.format_time(t)} заважкий",
                fg="red"
            ))

        except Exception as err:
            print(err)
            if p:
                p.kill()
            self.root.after(0, lambda: self.status_label.config(
                text="❌ Помилка рендеру кадру",
                fg="red"
            ))

    def display_image(self, img, t):
        self.last_img = img
        canvas_w, canvas_h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if canvas_w > 10 and canvas_h > 10:
            img_w, img_h = img.size
            ratio = min(canvas_w / img_w, canvas_h / img_h)
            nw, nh = int(img_w * ratio), int(img_h * ratio)
            img_res = img.resize((nw, nh), Image.Resampling.LANCZOS)
            img_tk = ImageTk.PhotoImage(img_res)
            self.canvas.config(image=img_tk)
            self.canvas.image = img_tk
        self.status_label.config(text=f"Позиція: {self.format_time(t)} / {self.format_time(self.duration)}", fg="black")

    def on_resize(self, event):
        if self.last_img: self.display_image(self.last_img, self.current_t)

    def start_trim_thread(self):
        default_name = f"trimmed_{self.video_path.name}"
        save_path = filedialog.asksaveasfilename(initialfile=default_name, defaultextension=".mp4")
        if save_path:
            self.set_ui_state(tk.DISABLED)
            self.btn_trim.config(text="⏳ ОБРОБКА...")
            threading.Thread(target=self.run_trim, args=(Path(save_path),), daemon=True).start()

    def run_trim(self, save_path: Path, start_s=None, end_s=None):
        s = start_s if start_s is not None else self.start_scale.get()
        e = end_s if end_s is not None else self.end_scale.get()
        cmd = [
            str(FFMPEG_BIN), '-y', '-ss', str(round(s, 3)), '-t', str(round(e - s, 3)),
            '-i', str(self.video_path), '-c', 'copy', '-avoid_negative_ts', 'make_zero', str(save_path)
        ]
        try:
            subprocess.run(cmd, creationflags=0x08000000, check=True)
            self.root.after(0, lambda: messagebox.showinfo("Успіх", f"Готово!\nЗбережено: {save_path.name}"))
        except Exception as err:
            self.root.after(0, lambda: messagebox.showerror(ERROR_STR, str(err)))
        finally:
            self.root.after(0, lambda: [self.set_ui_state(tk.NORMAL), self.btn_trim.config(text="✂️ ОБРІЗАТИ")])


if __name__ == "__main__":
    # 1. Set DPI Awareness FIRST
    if sys.platform == "win32":
        set_dpi_awareness()

    root = tk.Tk()
    app = PureFFmpegTrimmer(root)
    if root.winfo_exists():
        root.mainloop()
