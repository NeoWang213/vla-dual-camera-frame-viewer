"""Synchronized two-camera video viewer with frame counts.

Run with Python 3.10+ after installing opencv-python and Pillow.
Choose a folder containing episode_*.mp4 files. The viewer pairs files whose
path contains "front" and "handeye" (or "wrist").
"""

from __future__ import annotations

import re
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import cv2
from PIL import Image, ImageTk


EPISODE_RE = re.compile(r"episode[_-]?(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class Pair:
    episode: int
    front: Path
    handeye: Path


def camera_kind(path: Path) -> str | None:
    text = str(path).lower().replace("_", " ").replace("-", " ")
    if "front" in text:
        return "front"
    if "handeye" in text or "hand eye" in text or "wrist" in text:
        return "handeye"
    return None


def discover_pairs(root: Path) -> list[Pair]:
    groups: dict[int, dict[str, Path]] = {}
    for path in sorted(root.rglob("*.mp4")):
        match = EPISODE_RE.search(path.name)
        kind = camera_kind(path)
        if not match or kind is None:
            continue
        groups.setdefault(int(match.group(1)), {})[kind] = path
    return [Pair(ep, values["front"], values["handeye"])
            for ep, values in sorted(groups.items())
            if "front" in values and "handeye" in values]


class SyncViewer:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("同步双相机视频帧查看器")
        self.root.minsize(980, 720)
        self.pairs: list[Pair] = []
        self.captures: list[cv2.VideoCapture] = []
        self.current_frame = 0
        self.shared_frames = 0
        self.front_frames = 0
        self.handeye_frames = 0
        self.playing = False
        self.after_id: str | None = None
        self.photos: list[ImageTk.PhotoImage | None] = [None, None]

        top = ttk.Frame(root, padding=8)
        top.pack(fill="x")
        ttk.Button(top, text="选择视频文件夹", command=self.choose_folder).pack(side="left")
        self.folder_text = tk.StringVar(value="尚未选择文件夹")
        ttk.Label(top, textvariable=self.folder_text).pack(side="left", padx=10)

        controls = ttk.Frame(root, padding=(8, 0, 8, 4))
        controls.pack(fill="x")
        ttk.Label(controls, text="Episode").pack(side="left")
        self.episode_box = ttk.Combobox(controls, state="readonly", width=10)
        self.episode_box.pack(side="left", padx=5)
        self.episode_box.bind("<<ComboboxSelected>>", lambda _event: self.load_episode())
        ttk.Button(controls, text="加载", command=self.load_episode).pack(side="left")
        ttk.Button(controls, text="−30帧", command=lambda: self.move(-30)).pack(side="left", padx=(18, 2))
        ttk.Button(controls, text="−1帧", command=lambda: self.move(-1)).pack(side="left")
        ttk.Button(controls, text="+1帧", command=lambda: self.move(1)).pack(side="left", padx=2)
        ttk.Button(controls, text="+30帧", command=lambda: self.move(30)).pack(side="left")
        ttk.Button(controls, text="播放/暂停", command=self.toggle_play).pack(side="left", padx=(18, 2))
        self.info_text = tk.StringVar(value="请选择包含两路视频的文件夹")
        ttk.Label(controls, textvariable=self.info_text, font=("Arial", 11, "bold")).pack(side="right")

        self.slider = tk.Scale(root, from_=0, to=1, orient="horizontal", showvalue=False,
                               command=self.slider_changed)
        self.slider.pack(fill="x", padx=8)

        image_row = ttk.Frame(root, padding=8)
        image_row.pack(fill="both", expand=True)
        self.image_labels: list[ttk.Label] = []
        for title in ("Front", "Handeye"):
            panel = ttk.Frame(image_row)
            panel.pack(side="left", fill="both", expand=True, padx=4)
            ttk.Label(panel, text=title, font=("Arial", 12, "bold")).pack()
            label = ttk.Label(panel, anchor="center")
            label.pack(fill="both", expand=True)
            self.image_labels.append(label)

        ttk.Label(root, text="左右方向键：移动1帧；Shift+左右：移动30帧。总帧数以两个视频中较短者为同步范围。",
                  padding=(8, 0, 8, 8)).pack(anchor="w")
        root.bind("<Left>", lambda _event: self.move(-1))
        root.bind("<Right>", lambda _event: self.move(1))
        root.bind("<Shift-Left>", lambda _event: self.move(-30))
        root.bind("<Shift-Right>", lambda _event: self.move(30))
        root.protocol("WM_DELETE_WINDOW", self.close)

    def choose_folder(self) -> None:
        selected = filedialog.askdirectory(title="选择包含视频的文件夹")
        if not selected:
            return
        self.stop_play()
        root = Path(selected)
        self.pairs = discover_pairs(root)
        self.folder_text.set(str(root))
        self.episode_box["values"] = [str(pair.episode) for pair in self.pairs]
        if not self.pairs:
            messagebox.showerror("没有找到配对视频",
                                 "需要找到同一 episode 的 front 和 handeye 两个 MP4 文件。\n"
                                 "文件路径或文件名中应包含 front、handeye 或 wrist。")
            return
        self.episode_box.current(0)
        self.load_episode()

    def load_episode(self) -> None:
        if not self.pairs or self.episode_box.current() < 0:
            return
        self.stop_play()
        pair = self.pairs[self.episode_box.current()]
        for capture in self.captures:
            capture.release()
        self.captures = [cv2.VideoCapture(str(pair.front)), cv2.VideoCapture(str(pair.handeye))]
        if not all(capture.isOpened() for capture in self.captures):
            self.close_captures()
            messagebox.showerror("视频打开失败", f"{pair.front}\n{pair.handeye}")
            return
        self.front_frames = int(self.captures[0].get(cv2.CAP_PROP_FRAME_COUNT))
        self.handeye_frames = int(self.captures[1].get(cv2.CAP_PROP_FRAME_COUNT))
        self.shared_frames = min(self.front_frames, self.handeye_frames)
        self.slider.configure(from_=0, to=max(0, self.shared_frames - 1))
        self.show_frame(0)

    def show_frame(self, frame: int) -> None:
        if not self.captures or self.shared_frames <= 0:
            return
        frame = max(0, min(int(frame), self.shared_frames - 1))
        for index, capture in enumerate(self.captures):
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
            okay, image = capture.read()
            if not okay:
                messagebox.showerror("读取视频帧失败", f"frame {frame}")
                return
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(image)
            pil_image.thumbnail((680, 510))
            self.photos[index] = ImageTk.PhotoImage(pil_image)
            self.image_labels[index].configure(image=self.photos[index])
        self.current_frame = frame
        self.slider.set(frame)
        mismatch = "" if self.front_frames == self.handeye_frames else "（两路总帧数不同，按较短视频同步）"
        self.info_text.set(
            f"Episode {self.pairs[self.episode_box.current()].episode}  |  当前帧 {frame}  |  "
            f"Front总帧数 {self.front_frames}  |  Handeye总帧数 {self.handeye_frames} {mismatch}"
        )

    def slider_changed(self, value: str) -> None:
        if self.captures:
            self.show_frame(int(float(value)))

    def move(self, offset: int) -> None:
        if self.captures:
            self.show_frame(self.current_frame + offset)

    def toggle_play(self) -> None:
        if self.playing:
            self.stop_play()
        else:
            self.playing = True
            self.play_next()

    def play_next(self) -> None:
        if not self.playing:
            return
        if self.current_frame + 1 >= self.shared_frames:
            self.stop_play()
            return
        self.show_frame(self.current_frame + 1)
        self.after_id = self.root.after(33, self.play_next)

    def stop_play(self) -> None:
        self.playing = False
        if self.after_id is not None:
            self.root.after_cancel(self.after_id)
            self.after_id = None

    def close_captures(self) -> None:
        for capture in self.captures:
            capture.release()
        self.captures = []

    def close(self) -> None:
        self.stop_play()
        self.close_captures()
        self.root.destroy()


if __name__ == "__main__":
    app = tk.Tk()
    SyncViewer(app)
    app.mainloop()
