import ctypes
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import cv2
from PIL import Image, ImageTk

# Прямий шлях до вашого FFmpeg
FFMPEG_PATH = r"C:\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"


# Покращення чіткості тексту (DPI Awareness) для Windows 10/11
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception as e:
    print(f"DPI Awareness error: {e}")


class VideoVisualTrimmer:
    def __init__(self, root, debug=True):
        self.root = root
        self.root.title("H.264 Pro Trimmer (Win11)")
        self.debug = debug
        self.cap = None
        self.video_path = ""
        self.original_frame = None
        self.zoom_factor = 0.6
        self.fps = 0
        self.total_frames = 0

        # --- КЕРУВАННЯ ---
        self.top_controls = tk.Frame(root, pady=10, padx=10)
        self.top_controls.pack(side="top", fill="x")

        # Рядок 1: Системні кнопки
        self.row1 = tk.Frame(self.top_controls)
        self.row1.pack(fill="x", pady=2)

        self.btn_select = tk.Button(self.row1, text="📁 Відкрити відео", command=self.load_video)
        self.btn_select.pack(side="left", padx=5)

        tk.Label(self.row1, text="🔍 Zoom:").pack(side="left", padx=(15, 2))
        self.zoom_scale = tk.Scale(self.row1, from_=0.1, to=2.0, resolution=0.1, orient="horizontal", length=100,
                                   command=self.update_zoom)
        self.zoom_scale.set(self.zoom_factor)
        self.zoom_scale.pack(side="left")

        self.btn_trim = tk.Button(self.row1, text="✂️ ОБРІЗАТИ (Enter)", bg="#28a745", fg="white",
                                  font=("Arial", 9, "bold"), command=self.start_trim_thread)
        self.btn_trim.pack(side="right", padx=5)

        # Рядок 2: Таймлайн (Кадри + Стрілки)
        self.group_b = tk.LabelFrame(self.top_controls, text="Налаштування фрагменту (Точне коригування стрілками)",
                                     pady=5)
        self.group_b.pack(fill="x", pady=5)

        self.controls_list = []  # Список для блокування

        # START Frame
        self.create_frame_control(self.group_b, "START", "start")
        # STOP Frame
        self.create_frame_control(self.group_b, "STOP", "stop")

        # Статус-бар
        self.status_label = tk.Label(self.top_controls, text="Оберіть файл...", font=("Consolas", 9), fg="blue")
        self.status_label.pack()

        # --- ВІДЕО ---
        self.video_container = tk.Frame(root, bg="#1a1a1a")
        self.video_container.pack(expand=True, fill="both")
        self.canvas = tk.Label(self.video_container, bg="#1a1a1a")
        self.canvas.pack(expand=True)

        self.root.bind('<Return>', lambda e: self.start_trim_thread())

    def create_frame_control(self, parent, label_text, mode):
        frame = tk.Frame(parent)
        frame.pack(fill="x", padx=5, pady=2)

        scale = tk.Scale(frame, orient="horizontal", label=label_text, command=lambda v: self.on_scale_move(mode))
        scale.pack(side="left", fill="x", expand=True)

        # Блок кнопок-стрілок та інпута
        nav_frame = tk.Frame(frame)
        nav_frame.pack(side="right", padx=5, pady=(15, 0))

        btn_prev = tk.Button(nav_frame, text="<", width=2, command=lambda: self.step_frame(mode, -1))
        btn_prev.pack(side="left")

        entry = tk.Entry(nav_frame, width=8, justify='center')
        entry.pack(side="left", padx=2)
        entry.bind('<Return>', lambda e: self.on_entry_change(mode))

        btn_next = tk.Button(nav_frame, text=">", width=2, command=lambda: self.step_frame(mode, 1))
        btn_next.pack(side="left")

        if mode == "start":
            self.start_scale, self.start_entry = scale, entry
        else:
            self.end_scale, self.end_entry = scale, entry

        self.controls_list.extend([scale, entry, btn_prev, btn_next])

    def log(self, msg):
        if self.debug: print(f"[DEBUG] {msg}")

    def step_frame(self, mode, delta):
        scale = self.start_scale if mode == "start" else self.end_scale
        new_val = scale.get() + delta
        if 0 <= new_val < self.total_frames:
            scale.set(new_val)
            self.on_scale_move(mode)

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video", "*.mp4 *.mkv *.mov *.avi")])
        if not path: return
        self.video_path = path
        self.cap = cv2.VideoCapture(path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)

        self.start_scale.config(from_=0, to=self.total_frames - 1)
        self.end_scale.config(from_=0, to=self.total_frames - 1)
        self.start_scale.set(0)
        self.end_scale.set(self.total_frames - 1)
        self.update_entries()
        self.update_preview("start")
        self.status_label.config(text=f"Файл завантажено. FPS: {round(self.fps, 2)}", fg="black")

    def on_scale_move(self, mode):
        self.update_entries()
        self.update_preview(mode)

    def on_entry_change(self, mode):
        try:
            entry = self.start_entry if mode == "start" else self.end_entry
            scale = self.start_scale if mode == "start" else self.end_scale
            val = int(entry.get())
            if 0 <= val < self.total_frames:
                scale.set(val)
                self.update_preview(mode)
        except ValueError:
            pass

    def update_entries(self):
        self.start_entry.delete(0, tk.END)
        self.start_entry.insert(0, str(self.start_scale.get()))
        self.end_entry.delete(0, tk.END)
        self.end_entry.insert(0, str(self.end_scale.get()))

    def update_preview(self, mode):
        if not self.cap: return
        idx = self.start_scale.get() if mode == "start" else self.end_scale.get()
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ret, frame = self.cap.read()
        if ret:
            self.original_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.refresh_display()
            self.update_status_time()

    def update_status_time(self):
        s_s, e_s = self.start_scale.get() / self.fps, self.end_scale.get() / self.fps
        fmt = lambda s: f"{int(s // 3600):02}:{int((s % 3600) // 60):02}:{s % 60:05.2f}"
        self.status_label.config(text=f"Діапазон: {fmt(s_s)} — {fmt(e_s)}", fg="black")

    def update_zoom(self, v):
        self.zoom_factor = float(v)
        self.refresh_display()

    def refresh_display(self):
        if self.original_frame is None: return
        img = Image.fromarray(self.original_frame)
        img = img.resize((int(img.width * self.zoom_factor), int(img.height * self.zoom_factor)),
                         Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(img)
        self.canvas.config(image=img_tk)
        self.canvas.image = img_tk

    def set_gui_state(self, state):
        """Блокування/розблокування інтерфейсу"""
        new_st = "disabled" if state == "busy" else "normal"
        for ctrl in self.controls_list:
            ctrl.config(state=new_st)
        self.btn_select.config(state=new_st)
        self.zoom_scale.config(state=new_st)
        if state == "busy":
            self.btn_trim.config(text="⏳ ОБРОБКА...", state="disabled", bg="#95a5a6")
            self.status_label.config(text="FFmpeg працює... Будь ласка, зачекайте", fg="red")
        else:
            self.btn_trim.config(text="✂️ ОБРІЗАТИ (Enter)", state="normal", bg="#28a745")

    def start_trim_thread(self):
        if not self.video_path: return

        save_path = filedialog.asksaveasfilename(initialfile=f"trimmed_{Path(self.video_path).name}",
                                                 defaultextension=".mp4", filetypes=[("MP4", "*.mp4")])
        if not save_path: return

        self.set_gui_state("busy")
        threading.Thread(target=self.run_trim, args=(save_path,), daemon=True).start()

    def run_trim(self, save_path):
        s_s = self.start_scale.get() / self.fps
        dur = (self.end_scale.get() / self.fps) - s_s

        cmd = [FFMPEG_PATH, '-y', '-i', str(Path(self.video_path).absolute()),
               '-ss', str(round(s_s, 3)), '-t', str(round(dur, 3)),
               '-c', 'copy', '-avoid_negative_ts', 'make_zero', str(Path(save_path).absolute())]

        try:
            # Використовуємо правильне кодування та ігнорування помилок
            result = subprocess.run(cmd, capture_output=True, text=True, shell=False, encoding='utf-8', errors='ignore')

            # Повертаємось у головний потік для оновлення GUI
            self.root.after(0, lambda: self.finish_trim(result))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            self.root.after(0, lambda: self.set_gui_state("ready"))

    def finish_trim(self, result):
        self.set_gui_state("ready")
        if result.returncode == 0:
            messagebox.showinfo("Успіх", "Відео обрізано успішно!")
        else:
            messagebox.showerror("FFmpeg Error", result.stderr)
        self.update_status_time()


if __name__ == "__main__":
    root = tk.Tk()
    app = VideoVisualTrimmer(root)
    root.mainloop()
