import ctypes
import io
import json
import locale
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

# --- Константи та налаштування ---
BUTTON_RELEASE_ = "<ButtonRelease-1>"
SEGOE_UI = "Segoe UI"
REPO_OWNER = "olexandr-klymenko"
REPO_NAME = "VideoCutter"


def get_resource_path(relative_path: str) -> Path:
    """Отримує абсолютний шлях до ресурсу для dev та PyInstaller"""
    if hasattr(sys, '_MEIPASS'):
        return Path(sys._MEIPASS) / relative_path
    return Path(__file__).parent / relative_path


def get_current_version():
    try:
        return get_resource_path("version.txt").read_text().strip()
    except FileNotFoundError:
        return "1.0.0-dev"


VERSION = f"v{get_current_version()}"
FFMPEG_BIN = get_resource_path("bin/ffmpeg.exe")


# --- Локалізація ---

class LanguageManager:
    def __init__(self):
        self.translations = {}
        lang_code = self.detect_language()
        self.load_language(lang_code)

    def detect_language(self):
        try:
            # 1. Спробуємо отримати поточну локаль (може повернути 'Ukrainian_Ukraine' або 'uk_UA')
            # Використовуємо LC_CTYPE, бо на Windows LC_MESSAGES часто не ініціалізовано
            current_locale, _ = locale.getlocale()

            # 2. Якщо порожньо, спробуємо отримати системну локаль за замовчуванням
            if not current_locale:
                # Використовуємо getencoding як непрямий метод або повертаємося до базових налаштувань
                current_locale = ctypes.windll.kernel32.GetUserDefaultUILanguage()
                # Код 1058 — це українська в Windows (LCID)
                if current_locale == 1058:
                    return 'uk'

            if current_locale:
                current_locale = str(current_locale).lower()
                # Перевірка за ключовими словами (охоплює 'uk_ua', 'ukrainian', 'ukraine')
                if any(word in current_locale for word in ['uk', 'ua', 'ukrainian']):
                    return 'uk'

        except Exception as e:
            print(f"Language detection error: {e}")

        return "en"  # Англійська як стандарт для всього іншого

    def load_language(self, lang_code):
        lang_file = get_resource_path(f"locales/{lang_code}.json")
        if not lang_file.exists():
            lang_file = get_resource_path("locales/en.json")
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self.translations = json.load(f)
        except:
            self.translations = {}

    def get(self, key, **kwargs):
        text = self.translations.get(key, key)
        try:
            return text.format(**kwargs) if kwargs else text
        except KeyError:
            return text


# --- Системні функції ---

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


# --- Основний клас програми ---

class PureFFmpegTrimmer:
    def __init__(self, root):
        self.root = root
        self.lang_mgr = LanguageManager()

        # Назва програми
        self.app_name = "Pro Video Trimmer"
        self.root.title(f"{self.app_name} {VERSION}")

        self.ffmpeg_version = "Unknown"
        if not self.check_ffmpeg():
            self.root.withdraw()
            messagebox.showerror(
                self.lang_mgr.get("error_title"),
                f"{self.lang_mgr.get('error_ffmpeg')}\n{FFMPEG_BIN.absolute()}"
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

        icon_path = get_resource_path("icon.ico")
        if icon_path.exists():
            self.root.iconbitmap(str(icon_path))

        threading.Thread(target=self.check_for_updates, daemon=True).start()
        self.current_render_proc = None
        self.render_lock = threading.Lock()
        self.debounce_timer = None

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

    def check_for_updates(self):
        try:
            api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/releases/latest"
            response = requests.get(api_url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data.get("tag_name", "")
                if latest_version and latest_version != VERSION:
                    self.root.after(0, lambda: self.show_update_dialog(latest_version))
        except:
            pass

    def show_update_dialog(self, new_version):
        if messagebox.askyesno(
                self.lang_mgr.get("update_found_title"),
                self.lang_mgr.get("update_message", new_version=new_version, version=VERSION)
        ):
            webbrowser.open("https://olexandr-klymenko.github.io/VideoCutter/")

    def setup_ui(self):
        self.root.option_add("*Font", (SEGOE_UI, 9))
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)

        controls = tk.Frame(self.root, pady=10, padx=10)
        controls.pack(side="top", fill="x")

        btn_frame = tk.Frame(controls)
        btn_frame.pack(fill="x")

        tk.Button(btn_frame, text=self.lang_mgr.get("open_btn"), command=self.load_video).pack(side="left", padx=5)

        self.mode_check = tk.Checkbutton(btn_frame, text=self.lang_mgr.get("minutes_mode"),
                                         variable=self.is_minutes_mode, command=self.toggle_format, state=tk.DISABLED)
        self.mode_check.pack(side="left", padx=15)
        self.interactive_widgets.append(self.mode_check)

        info_frame = tk.Frame(btn_frame)
        info_frame.pack(side="left", padx=10)
        tk.Label(info_frame, text=f"App: {VERSION}", fg="#888888", font=(SEGOE_UI, 8)).pack(side="top", anchor="w")
        tk.Label(info_frame, text=f"FFmpeg: {self.ffmpeg_version}", fg="#888888", font=(SEGOE_UI, 8)).pack(side="top",
                                                                                                           anchor="w")

        self.btn_trim = tk.Button(btn_frame, text=self.lang_mgr.get("trim_btn"), bg="#28a745", fg="white",
                                  font=(SEGOE_UI, 9, "bold"), command=self.start_trim_thread, state=tk.DISABLED)
        self.btn_trim.pack(side="right", padx=5)
        self.interactive_widgets.append(self.btn_trim)

        self.start_scale, self.start_entry = self.create_time_control(controls, self.lang_mgr.get("start_label"))
        self.end_scale, self.end_entry = self.create_time_control(controls, self.lang_mgr.get("end_label"))

        self.result_info_label = tk.Label(controls, text="", font=(SEGOE_UI, 9, "bold"), fg="#0056b3")
        self.result_info_label.pack(pady=2)

        self.status_label = tk.Label(controls, text=self.lang_mgr.get("status_waiting"), font=("Consolas", 10),
                                     fg="gray")
        self.status_label.pack(pady=5)

        self.canvas = tk.Label(self.root, bg="#1a1a1a")
        self.canvas.pack(expand=True, fill="both")
        self.canvas.bind("<Configure>", self.on_resize)

        version_footer = tk.Label(self.root, text=self.lang_mgr.get("version_label", version=VERSION), fg="gray")
        version_footer.pack(side="bottom", anchor="e", padx=10, pady=5)
        # У методі setup_ui додайте:
        self.file_info_label = tk.Label(controls, text="", fg="#555555", font=(SEGOE_UI, 9, "italic"))
        self.file_info_label.pack(side="top", anchor="w", padx=5, pady=(5, 0))

        self.create_tooltip(self.file_info_label, lambda: str(self.video_path) if self.video_path else "")

    def create_time_control(self, parent, label_text):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=label_text, width=12, anchor="w").pack(side="left")

        scale = tk.Scale(frame, orient="horizontal", from_=0, to=100, resolution=0.01, showvalue=False,
                         state=tk.DISABLED,
                         command=lambda _: self.update_entries())
        scale.pack(side="left", fill="x", expand=True, padx=5)
        scale.bind("<Button-1>", lambda e: self.jump_to_click(e, scale) if scale['state'] != tk.DISABLED else None)
        scale.bind(BUTTON_RELEASE_,
                   lambda e: self.update_preview(scale.get()) if scale['state'] != tk.DISABLED else None)

        entry = tk.Entry(frame, width=10, justify='center', state=tk.DISABLED)
        entry.pack(side="left", padx=5)
        entry.bind('<Return>', lambda e: self.on_entry_change(scale, entry))

        fine_frame = tk.Frame(frame)
        fine_frame.pack(side="right")
        for d in [-0.1, 0.1]:
            btn = tk.Button(fine_frame, text=f"{d:+.1f}", width=4, state=tk.DISABLED)
            btn.pack(side="left", padx=1)
            btn.bind("<ButtonPress-1>", lambda e, s=scale, delta=d: self.start_auto_adjust(s, delta))
            btn.bind(BUTTON_RELEASE_, lambda e: self.stop_auto_adjust())
            self.interactive_widgets.append(btn)

        self.interactive_widgets.extend([scale, entry])
        return scale, entry

    def toggle_format(self):
        self.update_entries()
        self.update_status_pos(self.current_t)

    def update_status_pos(self, t):
        self.status_label.config(
            text=self.lang_mgr.get("status_position", current=self.format_time(t),
                                   total=self.format_time(self.duration)),
            fg="black"
        )

    def refresh_duration_info(self):
        diff = self.end_scale.get() - self.start_scale.get()
        if diff < 0:
            self.result_info_label.config(text=self.lang_mgr.get("error_range"), fg="red")
            self.btn_trim.config(state=tk.DISABLED)
        else:
            unit = self.lang_mgr.get("unit_min_sec" if self.is_minutes_mode.get() else "unit_sec")
            self.result_info_label.config(
                text=self.lang_mgr.get("duration_info", time=self.format_time(diff), unit=unit), fg="#0056b3"
            )
            if self.video_path: self.btn_trim.config(state=tk.NORMAL)

    def load_video(self):
        file_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if not file_path:
            return

        self.video_path = Path(file_path).resolve()

        # Витягуємо дані через FFmpeg
        cmd = [str(FFMPEG_BIN), "-hide_banner", "-i", str(self.video_path)]
        try:
            p = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore',
                                 creationflags=0x08000000)
            _, err = p.communicate()

            # 1. Тривалість
            dur_match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", err)
            # 2. Роздільна здатність (напр. 1920x1080)
            res_match = re.search(r",\s(\d{3,5})x(\d{3,5})", err)
            # 3. Відео кодек (напр. h264)
            codec_match = re.search(r"Video:\s([a-z0-9]+)", err)

            if dur_match:
                h, m, s = map(float, dur_match.groups())
                self.duration = h * 3600 + m * 60 + s

                # Формуємо рядок властивостей
                res_str = f"{res_match.group(1)}x{res_match.group(2)}" if res_match else "??x??"
                codec_str = codec_match.group(1).upper() if codec_match else "Unknown"
                file_size = f"{self.video_path.stat().st_size / (1024 * 1024):.1f} MB"

                # Оновлюємо лейбл: Ім'я файлу | Роздільна здатність | Кодек | Розмір
                info_text = f"📄 {self.video_path.name}  |  🎬 {res_str}  |  🎞️ {codec_str}  |  ⚖️ {file_size}"
                self.file_info_label.config(text=info_text)

                # Решта логіки (оновлення слайдерів і т.д.)
                self.set_ui_state(tk.NORMAL)
                for scale in [self.start_scale, self.end_scale]:
                    scale.config(to=self.duration)
                self.start_scale.set(0)
                self.end_scale.set(self.duration)
                self.update_preview(0)
                self.update_entries()

        except Exception as e:
            messagebox.showerror(self.lang_mgr.get("error_title"), f"{self.lang_mgr.get('error_read')} {e}")

    def create_tooltip(self, widget, text_func):
        """Створює спливаючу підказку для віджета."""
        tooltip_window = [None]

        def show_tooltip(event):
            text = text_func()
            if not text: return

            # Створюємо вікно без рамки (Toplevel)
            x, y, _, _ = widget.bbox("insert")
            x += widget.winfo_rootx() + 25
            y += widget.winfo_rooty() + 25

            tw = tk.Toplevel(widget)
            tw.wm_overrideredirect(True)  # Прибрати заголовок вікна
            tw.wm_geometry(f"+{x}+{y}")

            label = tk.Label(tw, text=text, justify='left',
                             background="#ffffe1", relief='solid', borderwidth=1,
                             font=(SEGOE_UI, "9", "normal"), padx=5, pady=2)
            label.pack()
            tooltip_window[0] = tw

        def hide_tooltip(event):
            if tooltip_window[0]:
                tooltip_window[0].destroy()
                tooltip_window[0] = None

        widget.bind("<Enter>", show_tooltip)
        widget.bind("<Leave>", hide_tooltip)

    def update_preview(self, t):
        """Ініціює процес прев'ю з використанням debounce-таймера."""
        if not self.video_path or not FFMPEG_BIN.exists():
            return

        self.current_t = t
        self.status_label.config(text=self.lang_mgr.get("status_rendering"), fg="blue")

        if self.debounce_timer:
            self.debounce_timer.cancel()

        self.debounce_timer = threading.Timer(0.15, self._trigger_render, args=(t,))
        self.debounce_timer.start()

    def _trigger_render(self, t):
        """Запускає задачу рендерингу в демонічному потоці."""
        threading.Thread(target=self._render_task, args=(t,), daemon=True).start()

    def _stop_current_proc(self):
        """Безпечно зупиняє поточний процес FFmpeg."""
        with self.render_lock:
            if not self.current_render_proc:
                return
            try:
                self.current_render_proc.kill()
                self.current_render_proc.wait()
            except OSError:
                pass  # Процес уже міг бути закритий ОС
            finally:
                self.current_render_proc = None

    def _render_task(self, t):
        """Виконує рендеринг кадру через FFmpeg PIPE."""
        self._stop_current_proc()

        safe_t = max(0.0, min(float(t), self.duration - 0.1))
        cmd = [
            str(FFMPEG_BIN), '-ss', str(round(safe_t, 3)), '-i', str(self.video_path),
            '-vframes', '1', '-q:v', '4', '-f', 'image2pipe', '-vcodec', 'mjpeg',
            '-loglevel', 'quiet', '-'
        ]

        p = None
        try:
            p = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=0x08000000
            )

            with self.render_lock:
                self.current_render_proc = p

            data, _ = p.communicate(timeout=1.0)

            # Перевірка актуальності запиту та наявності даних
            if self.current_t != t:
                return

            if not data or len(data) <= 500:
                raise ValueError("Incomplete image data received")

            image = Image.open(io.BytesIO(data))
            self.root.after(0, lambda: self.display_image(image, t))

        except subprocess.TimeoutExpired:
            self._handle_render_error("error_timeout", t, p)
        except (subprocess.SubprocessError, OSError, ValueError) as e:
            print(f"Render error: {e}")
            self._handle_render_error("error_render", t, p)
        finally:
            self._cleanup_proc(p)

    def _handle_render_error(self, lang_key, t, proc):
        """Централізована обробка помилок рендерингу."""
        if proc:
            try:
                proc.kill()
            except OSError:
                pass

        if self.current_t == t:
            error_text = self.lang_mgr.get(lang_key, time=self.format_time(
                t)) if lang_key == "error_timeout" else self.lang_mgr.get(lang_key)
            self.root.after(0, lambda: self.status_label.config(text=error_text, fg="red"))

    def _cleanup_proc(self, proc):
        """Очищення ресурсів після завершення або помилки."""
        with self.render_lock:
            if self.current_render_proc == proc:
                self.current_render_proc = None
        if proc and proc.stdout:
            proc.stdout.close()

    def display_image(self, img, t):
        self.last_img = img
        cw, ch = self.canvas.winfo_width(), self.canvas.winfo_height()
        if cw > 10 and ch > 10:
            iw, ih = img.size
            ratio = min(cw / iw, ch / ih)
            img_res = img.resize((int(iw * ratio), int(ih * ratio)), Image.Resampling.LANCZOS)
            tk_img = ImageTk.PhotoImage(img_res)
            self.canvas.config(image=tk_img)
            self.canvas.image = tk_img
        self.update_status_pos(t)

    def start_trim_thread(self):
        save_path = filedialog.asksaveasfilename(initialfile=f"trimmed_{self.video_path.name}", defaultextension=".mp4")
        if save_path:
            self.set_ui_state(tk.DISABLED)
            self.btn_trim.config(text=self.lang_mgr.get("trimming_process"))
            threading.Thread(target=self.run_trim, args=(Path(save_path),), daemon=True).start()

    def run_trim(self, save_path: Path, start_s=None, end_s=None):
        # Якщо аргументи не передані (звичайний клік у програмі), беремо значення зі слайдерів
        s = start_s if start_s is not None else self.start_scale.get()
        e = end_s if end_s is not None else self.end_scale.get()

        cmd = [
            str(FFMPEG_BIN), '-y',
            '-ss', str(round(s, 3)),
            '-t', str(round(e - s, 3)),
            '-i', str(self.video_path),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            str(save_path)
        ]
        try:
            subprocess.run(cmd, creationflags=0x08000000, check=True)
            # Використовуємо self.lang_mgr.get тільки якщо ми не в тесті (немає вікон)
            if not start_s:
                self.root.after(0, lambda: messagebox.showinfo(
                    self.lang_mgr.get("success_title"),
                    self.lang_mgr.get("success_message", name=save_path.name)
                ))
        except Exception as err:
            if not start_s:
                self.root.after(0, lambda: messagebox.showerror(self.lang_mgr.get("error_title"), str(err)))
            else:
                raise err  # Для тестів важливо "прокинути" помилку далі
        finally:
            if not start_s:
                self.root.after(0, lambda: [self.set_ui_state(tk.NORMAL),
                                            self.btn_trim.config(text=self.lang_mgr.get("trim_btn"))])

    # --- Допоміжні методи (без змін логіки) ---
    def set_ui_state(self, state):
        for w in self.interactive_widgets: w.config(state=state)

    def format_time(self, seconds):
        if not self.is_minutes_mode.get(): return f"{seconds:.2f}"
        return f"{int(seconds // 60):02d}:{seconds % 60:05.2f}"

    def parse_time(self, s):
        s = s.replace(',', '.').strip()
        if ":" in s:
            p = s.split(":")
            return int(p[0]) * 60 + float(p[1]) if len(p) == 2 else 0.0
        return float(s)

    def update_entries(self):
        for e, s in [(self.start_entry, self.start_scale), (self.end_entry, self.end_scale)]:
            if e['state'] != tk.DISABLED:
                e.delete(0, tk.END)
                e.insert(0, self.format_time(s.get()))
        self.refresh_duration_info()

    def on_entry_change(self, scale, entry):
        try:
            val = max(0, min(self.parse_time(entry.get()), self.duration))
            scale.set(val)
            self.update_preview(val)
        except:
            self.update_entries()

    def jump_to_click(self, e, s):
        val = (max(0, min(1, (e.x - 8) / (s.winfo_width() - 16)))) * s.cget("to")
        s.set(val)
        self.update_preview(val)

    def start_auto_adjust(self, s, d):
        self.adjust_time(s, d)
        self.after_id = self.root.after(400, lambda: self.repeat_adjust(s, d))

    def repeat_adjust(self, s, d):
        self.adjust_time(s, d)
        self.after_id = self.root.after(self.repeat_delay, lambda: self.repeat_adjust(s, d))

    def stop_auto_adjust(self):
        if self.after_id: self.root.after_cancel(self.after_id); self.after_id = None

    def adjust_time(self, s, d):
        nv = max(0, min(s.get() + d, self.duration))
        s.set(nv)
        self.update_entries()
        self.update_preview(nv)

    def on_resize(self, e):
        if self.last_img: self.display_image(self.last_img, self.current_t)


if __name__ == "__main__":
    set_dpi_awareness()
    root = tk.Tk()
    app = PureFFmpegTrimmer(root)
    if root.winfo_exists(): root.mainloop()
