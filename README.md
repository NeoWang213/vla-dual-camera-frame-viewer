# 同步双相机视频帧查看器

用于查看两路同步视频的当前帧号和总帧数。支持选择视频根文件夹、选择 episode、同步逐帧查看和播放。

## 文件组织

程序会递归查找名称类似 `episode_000000.mp4` 的文件，并根据路径或文件名中的关键词配对：

- 前视：包含 `front`
- 腕部：包含 `handeye`、`hand eye` 或 `wrist`

例如可以直接选择：

```text
E:\VLA_DATA\lenovo\act_blue_cube_83
```

程序会自动找到 `videos/` 下的两路相机视频。

## 在另一台 Windows 电脑运行

安装 Python 3.10 或更高版本，然后在本目录打开命令行：

```text
py -m pip install -r requirements_sync_video_viewer.txt
run_sync_video_viewer.cmd
```

Python 自带 Tkinter 的安装方式取决于 Python 发行版；标准 Windows Python 通常自带。视频解码由 OpenCV 完成。

## 操作

- 选择视频文件夹：选择包含 `videos` 或 MP4 文件的根目录。
- `−1帧` / `+1帧`：逐帧移动。
- `−30帧` / `+30帧`：快速移动。
- 播放/暂停：同步播放两路视频。
- 左右方向键：移动1帧；Shift+左右方向键：移动30帧。

界面显示当前帧号、Front 总帧数和 Handeye 总帧数。若两路视频长度不同，同步操作范围使用较短视频的长度，并在界面提示。
