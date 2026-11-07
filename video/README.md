# 《抗日民族统一战线》5分钟视频 · 制作脚本与说明

课堂展示配套视频（1280×720，约5分钟），画面沿用 PPT 的老照片与 AI 上色版，
旁白 4 号深沉男声，字幕全中文，背景音乐 Sascha Ende《Echoes in the Archive》
（CC BY 4.0，片尾已署名）。

## 文件
- `render_clips_v2.py`：把照片渲染成带运镜（推近/拉远/平移/斜移）、题注（宋体左上角）、
  章节标题淡入淡出的视频片段，输出到 `clips2/`。
- `assemble_v2.py`：把 20 个片段用 0.8 秒淡入淡出接起来，混入 5 段旁白与循环背景音乐，
  再用 ASS 字幕把中文字幕压进画面（字幕用 `\pos` 钉死在底部，不跳动）。
- `build_subtitles.py`：按旁白时长比例生成 SRT 字幕（每句强制两行，防跳动）。
- `build_ass.py`：把 SRT 转成 ASS，给每条字幕加 `\pos(640,690)` 钉死底部。
- `narration.md`：旁白全文（美化稿，史实不变）。
- `narration/sec_A.txt` … `sec_E.txt`：五段旁白分段文本（供 TTS）。
- `subtitles.srt` / `subtitles.ass`：字幕文件。

## 旁白
- 声音：4 号深沉男声（avocado_v2:vd2_r8_rep1k_0104_v068_28k_g5k），语速 90。
- 生成命令示例：`/opt/hatch/bin/tts speak --voice avocado_v2:vd2_r8_rep1k_0104_v068_28k_g5k --language zh --speed 90 --output narration/sec_A.mp3 --text-stdin < narration/sec_A.txt`

## 注意
- 成片视频（MP4，约 42MB）是二进制文件，无法通过 GitHub 连接器推送，
  请从 Muse 的下载链接获取后自行上传。
- 背景音乐 `music/echoes_in_the_archive.mp3` 未包含在内（版权文件请自行下载，
  来源 ende.app，CC BY 4.0）。
