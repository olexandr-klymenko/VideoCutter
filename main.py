import ctypes
import tkinter as tk

from src.ui import PureFFmpegTrimmer


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except:
            pass


if __name__ == "__main__":
    set_dpi_awareness()
    root = tk.Tk()
    app = PureFFmpegTrimmer(root)
    if root.winfo_exists():
        root.mainloop()
