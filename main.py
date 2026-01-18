import configparser
import ctypes
import io
import re
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

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
        self.root.title("FFmpeg Video Trimmer (Pro Time Format)")
        self.video_path = ""
        self.duration = 0.0
        self.zoom_factor = 0.5
        self.last_img = None
        self.current_t = 0.0  # Зберігаємо поточний час для оновлення статусу
        self.is_minutes_mode = tk.BooleanVar(value=False)

        self.setup_ui()

    def format_time(self, seconds):
        if not self.is_minutes_mode.get():
            return f"{seconds:.2f}"
        m = int(seconds // 60)
        s = seconds % 60
        return f"{m:02d}:{s:05.2f}"

    def parse_time(self, string):
        string = string.replace(',', '.').strip()
        if ":" in string:
            parts = string.split(":")
            if len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
        return float(string)

    def setup_ui(self):
        self.root.option_add("*Font", ("Segoe UI", 9))

        controls = tk.Frame(self.root, pady=10, padx=10)
        controls.pack(side="top", fill="x")

        btn_frame = tk.Frame(controls)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="📁 Відкрити", command=self.load_video).pack(side="left", padx=5)

        # Тоглер формату (тепер з викликом повного оновлення)
        tk.Checkbutton(btn_frame, text="Хвилини (MM:SS)", variable=self.is_minutes_mode,
                       command=self.toggle_format).pack(side="left", padx=15)

        tk.Label(btn_frame, text="🔍 Zoom:").pack(side="left", padx=(5, 2))
        self.zoom_scale = tk.Scale(btn_frame, from_=0.1, to=1.5, resolution=0.1, orient="horizontal", length=80,
                                   command=self.update_zoom)
        self.zoom_scale.set(self.zoom_factor)
        self.zoom_scale.pack(side="left")

        self.btn_trim = tk.Button(btn_frame, text="✂️ ОБРІЗАТИ", bg="#28a745", fg="white", font=("Segoe UI", 9, "bold"),
                                  command=self.start_trim_thread)
        self.btn_trim.pack(side="right", padx=5)

        self.start_scale, self.start_entry = self.create_time_control(controls, "ПОЧАТОК")
        self.end_scale, self.end_entry = self.create_time_control(controls, "КІНЕЦЬ")

        self.status_label = tk.Label(controls, text="Очікування файлу...", font=("Consolas", 10))
        self.status_label.pack(pady=5)

        self.canvas = tk.Label(self.root, bg="#1a1a1a")
        self.canvas.pack(expand=True, fill="both")

    def create_time_control(self, parent, label_text):
        frame = tk.Frame(parent)
        frame.pack(fill="x", pady=2)
        tk.Label(frame, text=label_text, width=8, anchor="w").pack(side="left")

        scale = tk.Scale(frame, orient="horizontal", from_=0, to=100, resolution=0.01, showvalue=False)
        scale.pack(side="left", fill="x", expand=True, padx=5)

        scale.bind("<Button-1>", lambda e: self.jump_to_click(e, scale))
        scale.bind("<ButtonRelease-1>", lambda e: self.update_preview(scale.get()))

        entry = tk.Entry(frame, width=12, justify='center')
        entry.pack(side="right")
        entry.bind('<Return>', lambda e: self.on_entry_change(scale, entry))

        return scale, entry

    def toggle_format(self):
        """Оновлює всі текстові поля та статус-бар при зміні формату."""
        self.update_entries()
        # Оновлюємо статус-бар, використовуючи останній відомий час
        self.status_label.config(
            text=f"Позиція: {self.format_time(self.current_t)} / {self.format_time(self.duration)}",
            fg="black"
        )

    def jump_to_click(self, event, scale):
        length = scale.winfo_width() - 16
        val = (max(0, min(1, (event.x - 8) / length))) * scale.cget("to")
        scale.set(val)
        self.update_preview(val)

    def on_entry_change(self, scale, entry):
        try:
            val = self.parse_time(entry.get())
            val = max(0, min(val, self.duration))
            scale.set(val)
            self.update_preview(val)
        except:
            self.update_entries()

    def update_entries(self):
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, self.format_time(self.start_scale.get()))
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, self.format_time(self.end_scale.get()))

    def update_preview(self, t):
        if not self.video_path: return
        self.current_t = t  # Запам'ятовуємо час
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
            self.root.after(0, lambda: self.status_label.config(text="⏱️ Таймаут (бита ділянка)", fg="red"))

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

    def load_video(self):
        path = filedialog.askopenfilename()
        if not path: return
        self.video_path = path

        cmd = [FFMPEG_PATH, "-i", path]
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, creationflags=0x08000000)
        _, err = p.communicate()
        match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", err)
        if match:
            h, m, s = map(float, match.groups())
            self.duration = h * 3600 + m * 60 + s

        for s in [self.start_scale, self.end_scale]:
            s.config(to=self.duration)
        self.start_scale.set(0)
        self.end_scale.set(self.duration)
        self.current_t = 0
        self.update_entries()
        self.update_preview(0)

    def update_zoom(self, v):
        self.zoom_factor = float(v)
        if self.last_img: self.display_image(self.last_img, self.current_t)

    def start_trim_thread(self):
        if not self.video_path: return
        save_path = filedialog.asksaveasfilename(initialfile=f"trimmed_{Path(self.video_path).name}",
                                                 defaultextension=".mp4")
        if save_path:
            self.btn_trim.config(text="⏳ ОБРОБКА...", state="disabled")
            threading.Thread(target=self.run_trim, args=(save_path,), daemon=True).start()

    def run_trim(self, save_path):
        s, e = self.start_scale.get(), self.end_scale.get()
        cmd = [FFMPEG_PATH, '-y', '-ss', str(round(s, 3)), '-t', str(round(e - s, 3)),
               '-i', self.video_path, '-c', 'copy', '-avoid_negative_ts', 'make_zero', save_path]
        try:
            subprocess.run(cmd, creationflags=0x08000000, check=True)
            self.root.after(0, lambda: messagebox.showinfo("Успіх", "Готово!"))
        except:
            self.root.after(0, lambda: messagebox.showerror("Помилка", "Не вдалося обрізати."))
        finally:
            self.root.after(0, lambda: self.btn_trim.config(text="✂️ ОБРІЗАТИ", state="normal"))


if __name__ == "__main__":
    root = tk.Tk()
    app = PureFFmpegTrimmer(root)
    root.mainloop()
