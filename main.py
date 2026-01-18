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
        self.root.title("FFmpeg Video Trimmer")
        self.video_path = ""
        self.duration = 0.0
        self.last_img = None
        self.current_t = 0.0
        self.is_minutes_mode = tk.BooleanVar(value=False)

        # Для автоповтору
        self.after_id = None
        self.repeat_delay = 100  # мілісекунди між кроками

        self.interactive_widgets = []
        self.setup_ui()
        self.canvas.bind("<Configure>", self.on_resize)

    def setup_ui(self):
        self.root.option_add("*Font", ("Segoe UI", 9))
        self.root.geometry("1000x650")

        controls = tk.Frame(self.root, pady=10, padx=10)
        controls.pack(side="top", fill="x")

        btn_frame = tk.Frame(controls)
        btn_frame.pack(fill="x")
        tk.Button(btn_frame, text="📁 Відкрити відео", command=self.load_video).pack(side="left", padx=5)

        self.mode_check = tk.Checkbutton(btn_frame, text="Хвилини (MM:SS)", variable=self.is_minutes_mode,
                                         command=self.toggle_format, state=tk.DISABLED)
        self.mode_check.pack(side="left", padx=15)
        self.interactive_widgets.append(self.mode_check)

        self.btn_trim = tk.Button(btn_frame, text="✂️ ОБРІЗАТИ", bg="#28a745", fg="white",
                                  font=("Segoe UI", 9, "bold"), command=self.start_trim_thread, state=tk.DISABLED)
        self.btn_trim.pack(side="right", padx=5)
        self.interactive_widgets.append(self.btn_trim)

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

        tk.Label(frame, text=label_text, width=10, anchor="w").pack(side="left")

        scale = tk.Scale(frame, orient="horizontal", from_=0, to=100, resolution=0.01, showvalue=False,
                         state=tk.DISABLED)
        scale.pack(side="left", fill="x", expand=True, padx=5)

        scale.bind("<Button-1>", lambda e: self.jump_to_click(e, scale) if scale['state'] != tk.DISABLED else None)
        scale.bind("<ButtonRelease-1>",
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

        # Прив'язка подій для утримання
        btn_minus.bind("<ButtonPress-1>", lambda e: self.start_auto_adjust(scale, -0.1))
        btn_minus.bind("<ButtonRelease-1>", lambda e: self.stop_auto_adjust())

        btn_plus.bind("<ButtonPress-1>", lambda e: self.start_auto_adjust(scale, 0.1))
        btn_plus.bind("<ButtonRelease-1>", lambda e: self.stop_auto_adjust())

        self.interactive_widgets.extend([scale, entry, btn_minus, btn_plus])
        return scale, entry

    def start_auto_adjust(self, scale, delta):
        """Починає процес зміни часу."""
        self.adjust_time(scale, delta)
        # Перша затримка трохи довша, щоб одиночний клік не сприймався як серія
        self.after_id = self.root.after(400, lambda: self.repeat_adjust(scale, delta))

    def repeat_adjust(self, scale, delta):
        """Циклічно змінює час, поки кнопка натиснута."""
        self.adjust_time(scale, delta)
        self.after_id = self.root.after(self.repeat_delay, lambda: self.repeat_adjust(scale, delta))

    def stop_auto_adjust(self):
        """Зупиняє автоповтор."""
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None
        # Після зупинки утримання оновлюємо прев'ю (для економії ресурсів під час затискання)
        # Або можна оновлювати в adjust_time для реального часу

    def adjust_time(self, scale, delta):
        new_val = max(0, min(scale.get() + delta, self.duration))
        scale.set(new_val)
        self.update_entries()
        # Для дуже швидкого відгуку можна викликати update_preview тут,
        # але на слабких ПК це може "фрізити" інтерфейс.
        self.update_preview(new_val)

    def set_ui_state(self, state):
        for widget in self.interactive_widgets:
            widget.config(state=state)

    def load_video(self):
        path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov *.ts")])
        if not path: return
        self.video_path = str(Path(path).resolve())
        cmd = [FFMPEG_PATH, "-hide_banner", "-i", self.video_path]
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
        except Exception as e:
            messagebox.showerror("Помилка", f"Критична помилка: {str(e)}")

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
            if entry['state'] != tk.DISABLED:
                entry.delete(0, tk.END)
                entry.insert(0, self.format_time(scale.get()))

    def update_preview(self, t):
        if not self.video_path: return
        self.current_t = t
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
        except:
            pass

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
        save_path = filedialog.asksaveasfilename(initialfile=f"trimmed_{Path(self.video_path).name}",
                                                 defaultextension=".mp4")
        if save_path:
            self.set_ui_state(tk.DISABLED)
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
