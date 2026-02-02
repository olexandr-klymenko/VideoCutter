import re
import subprocess

from src.config import FFMPEG_BIN


class VideoEngine:
    @staticmethod
    def check_ffmpeg():
        if not FFMPEG_BIN.exists(): return False, "Missing"
        try:
            result = subprocess.run(
                [str(FFMPEG_BIN), "-version"],
                capture_output=True, text=True, creationflags=0x08000000, check=True
            )
            match = re.search(r"version\s+([^\s,]+)", result.stdout.splitlines()[0])
            return True, match.group(1) if match else "Detected"
        except:
            return False, "Error"

    @staticmethod
    def get_video_info(path):
        cmd = [str(FFMPEG_BIN), "-hide_banner", "-i", str(path)]
        p = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='ignore',
                             creationflags=0x08000000)
        _, err = p.communicate()

        dur_match = re.search(r"Duration:\s(\d+):(\d+):(\d+\.\d+)", err)
        res_match = re.search(r",\s(\d{3,5})x(\d{3,5})", err)
        codec_match = re.search(r"Video:\s([a-z0-9]+)", err)

        duration = 0
        if dur_match:
            h, m, s = map(float, dur_match.groups())
            duration = h * 3600 + m * 60 + s

        return {
            "duration": duration,
            "res": f"{res_match.group(1)}x{res_match.group(2)}" if res_match else "??",
            "codec": codec_match.group(1).upper() if codec_match else "Unknown"
        }
