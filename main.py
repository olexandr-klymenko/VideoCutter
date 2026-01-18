import ctypes
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox
from PIL import Image, ImageTk
import configparser
import io
import re

# --- DPI Awareness ---
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except:
        pass

config = configparser.ConfigParser()
config.read('config.ini')
FFMPEG_PATH = config.get('Paths', 'ffmpeg_path', fallback=r"C:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe")


class PureFFmpegTrimmer:
    def __init__(self, root):
        self.root = root
        self.root.title("FFmpeg Video Trimmer (Locked UI Edition)")
        self.video_path = ""
        self.duration = 0.0
        self.zoom_factor = 0.5
        self.last_img = None
        self.current_t = 0.0
        self.is_minutes_mode = tk.BooleanVar(value=False)

        # Список елементів, які треба розблокувати після завантаження
        self.interactive_widgets = []

        self.setup_ui()

    def setup_ui(self):
        self.root.option_add("*Font", ("Segoe UI", 9))

        controls = tk.Frame(self.root, pady=10, padx=10)
        controls.pack(side="top", fill="x")

        # Рядок кнопок
        btn_frame = tk.Frame(controls)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="📁 Відкрити відео", command=self.load_video).pack(side="left", padx=5)

        # Тоглер формату
        self.mode_check = tk.Checkbutton(btn_frame, text="Хвилини (MM:SS)", variable=self.is_minutes_mode,
                                         command=self.toggle_format, state=tk.DISABLED)
        self.mode_check.pack(side="left", padx=15)
        self.interactive_widgets.append(self.mode_check)

        tk.Label(btn_frame, text="🔍 Zoom:").pack(side="left", padx=(5, 2))
        self.zoom_scale = tk.Scale(btn_frame, from_=0.1, to=1.5, resolution=0.1, orient="horizontal", length=80,
                                   command=self.update_zoom)
        self.zoom_scale.set(self.zoom_factor)
        self.zoom_scale.pack(side="left")

        self.btn_trim = tk.Button(btn_frame, text="✂️ ОБРІЗАТИ", bg="#28a745", fg="white",
                                  font=("Segoe UI", 9, "bold"), command=self.start_trim_thread, state=tk.DISABLED)
        self.btn_trim.pack(side="right", padx=5)
        self.interactive_widgets.append(self.btn_trim)

        # Таймлайни
        self.start_scale, self.start_entry = self.create_time_control(controls, "ПОЧАТОК")
        self.end_scale, self.end_entry = self.create_time_control(controls, "КІНЕЦЬ")

        self.status_label = tk.Label(controls, text="Будь ласка, спочатку відкрийте відео файл", font=("Consolas", 10),
                                     fg="gray")
        self.status_label.pack(pady=5)

        self.canvas = tk.Label(self.root, bg="#1a1a1a")
        self.canvas.pack(expand=True, fill="both")

    def create_time_control(self, parent, label_text):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)

        # Збільшено width з 8 до 10, щоб довгі слова (ПОЧАТОК) влізали повністю
        tk.Label(frame, text=label_text, width=10, anchor="w").pack(side="left")

        scale = tk.Scale(frame, orient="horizontal", from_=0, to=100, resolution=0.01, showvalue=False,
                         state=tk.DISABLED)
        scale.pack(side="left", fill="x", expand=True, padx=5)

        scale.bind("<Button-1>", lambda e: self.jump_to_click(e, scale) if scale['state'] != tk.DISABLED else None)
        scale.bind("<ButtonRelease-1>",
                   lambda e: self.update_preview(scale.get()) if scale['state'] != tk.DISABLED else None)

        entry = tk.Entry(frame, width=12, justify='center', state=tk.DISABLED)
        entry.pack(side="right")
        entry.bind('<Return>', lambda e: self.on_entry_change(scale, entry))

        self.interactive_widgets.extend([scale, entry])
        return scale, entry

    def set_ui_state(self, state):
        """Вмикає або вимикає всі інтерактивні елементи."""
        for widget in self.interactive_widgets:
            widget.config(state=state)

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if not path: return

        self.video_path = path

        # Отримання тривалості
        cmd = [FFMPEG_PATH, "-i", path]
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, creationflags=0x08000000)
        _, err = p.communicate()
        match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", err)

        if match:
            h, m, s = map(float, match.groups())
            self.duration = h * 3600 + m * 60 + s

            # Активуємо UI
            self.set_ui_state(tk.NORMAL)

            for s in [self.start_scale, self.end_scale]:
                s.config(to=self.duration)
            self.start_scale.set(0)
            self.end_scale.set(self.duration)
            self.current_t = 0
            self.update_entries()
            self.update_preview(0)
        else:
            messagebox.showerror("Помилка", "Не вдалося визначити тривалість відео. Можливо, файл пошкоджений.")

    # --- Решта методів залишаються без змін ---

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
        if entry['state'] == tk.DISABLED: return
        try:
            val = self.parse_time(entry.get())
            val = max(0, min(val, self.duration))
            scale.set(val)
            self.update_preview(val)
        except:
            self.update_entries()

    def update_entries(self):
        for entry, scale in [(self.start_entry, self.start_scale), (self.end_entry, self.end_scale)]:
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, self.format_time(scale.get()))

    def update_preview(self, t):
        if not self.video_path: return
        self.current_t = t
        self.update_entries()
        self.status_label.config(text="⌛ Рендеринг...", fg="blue")
        threading.Thread(target=self._render_task, args=(t,), daemon=True).start()

    def _render_task(self, t):
        cmd = [FFMPEG_PATH, '-ss', str(round(t, 3)), '-i', self.video_path, '-frames:v', '1',
               '-q:v', '3', '-f', 'image2pipe', '-vcodec', 'mjpeg', '-loglevel', 'error', '-']
        try:
            p = subprocess.Popen(cmd, stdout=subprocess.PIPE, creationflags=0x08000000)
            data, _ = p.communicate(timeout=2.0)
            if data and len(data) > 500:
                image = Image.open(io.BytesIO(data))
                self.root.after(0, lambda: self.display_image(image, t))
            else:
                self.root.after(0, lambda: self.status_label.config(text="❌ Помилка рендерингу", fg="red"))
        except:
            self.root.after(0, lambda: self.status_label.config(text="⏱️ Таймаут", fg="red"))

    def display_image(self, img, t):
        self.last_img = img
        self.current_t = t
        w, h = img.size
        nw, nh = int(w * self.zoom_factor), int(h * self.zoom_factor)
        img_res = img.resize((nw, nh), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img_res)
        self.canvas.config(image=img_tk)
        self.canvas.image = img_tk
        self.status_label.config(text=f"Позиція: {self.format_time(t)} / {self.format_time(self.duration)}", fg="black")

    def update_zoom(self, v):
        self.zoom_factor = float(v)
        if self.last_img: self.display_image(self.last_img, self.current_t)

    def start_trim_thread(self):
        if not self.video_path: return
        save_path = filedialog.asksaveasfilename(initialfile=f"trimmed_{Path(self.video_path).name}",
                                                 defaultextension=".mp4")
        if save_path:
            self.set_ui_state(tk.DISABLED)  # Блокуємо на час обробки
            self.btn_trim.config(text="⏳ ОБРОБКА...")
            threading.Thread(target=self.run_trim, args=(save_path,), daemon=True).start()

    def run_trim(self, save_path):
        s, e = self.start_scale.get(), self.end_scale.get()
        cmd = [FFMPEG_PATH, '-y', '-ss', str(round(s, 3)), '-t', str(round(e - s, 3)),
               '-i', self.video_path, '-c', 'copy', '-avoid_negative_ts', 'make_zero', save_path]
        try:
            subprocess.run(cmd, creationflags=0x08000000, check=True)
            self.root.after(0, lambda: messagebox.showinfo("Успіх", "Готово!"))
        finally:
            self.root.after(0, lambda: [self.set_ui_state(tk.NORMAL), self.btn_trim.config(text="✂️ ОБРІЗАТИ")])


if __name__ == "__main__":
    root = tk.Tk()
    app = PureFFmpegTrimmer(root)
    root.mainloop()