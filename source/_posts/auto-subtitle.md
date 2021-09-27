---
title: 利用Google Speech自动视频字幕
donate: true
date: 2021-09-27 15:32:10
categories: Live
tags: Live
---

最近由于需要看一些英文的视频学习材料，其中不乏一些印度同仁的作品，口音着实不是很友好，有时候在github上找到了个挺好的项目，[自动字幕](https://github.com/BingLingGroup/autosub)。

## 使用 Autosub
用发很简单，记在这里主要为了防止遗忘！

### 使用Google Speech V2
```
autosub -i <video.mp4> -S en-us
```
这是默认的方法，不需要加额外的参数。


```
Translation destination language not provided. Only performing speech recognition.
Override "-of"/"--output-files" due to your args too few.
Output source subtitles file only.

Convert source file to "/tmp/tmpavalo8l2.wav" to detect audio regions.
/usr/bin/ffmpeg -hide_banner -y -i "TEST.mp4" -vn -ac 1 -ar 48000 -loglevel error "/tmp/tmpavalo8l2.wav"

Use ffprobe to check conversion result.
/usr/bin/ffprobe "/tmp/tmpavalo8l2.wav" -show_format -pretty -loglevel quiet
[FORMAT]
filename=/tmp/tmpavalo8l2.wav
nb_streams=1
nb_programs=0
format_name=wav
format_long_name=WAV / WAVE (Waveform Audio)
start_time=N/A
duration=0:39:16.416000
size=215.736403 Mibyte
bit_rate=768 Kbit/s
probe_score=99
TAG:encoder=Lavf58.29.100
[/FORMAT]

Conversion completed.
Use Auditok to detect speech regions.

Auditok detection completed.
"/tmp/tmpavalo8l2.wav" has been deleted.

Converting speech regions to short-term fragments.
Converting: 100% |##################################################################################################################################################################| Time:  0:00:02

Sending short-term fragments to Google Speech V2 API and getting result.
Speech-to-Text: 100% |##############################################################################################################################################################| Time:  0:01:03
Speech language subtitles file created at "/home/works/TEST.en-us.srt".

All work done.

```

大概原理就是使用FFmpeg把视频的音轨分离出来，然后调用Google API进行语音识别，最终生成字幕文件 `TEST.en-us.srt`

### 使用Google Cloud Speech-to-Text
```
autosub -i <video.mp4> -S en-us -hsp https://<https_proxy>:<port> -hp http://<http_proxy>:<port> -sapi gcsv1 -skey xxxxxxx

-S 识别的语言
-hsp https 代理
-hp http 代理
-sapi gcsv1    Google Cloud Speech-to-Text
-skey        Google App Key
```
这种方式需要Google App Key，并且是时长付费的，尽管每月有免费的时间。具体操作看到项目ReadMe，并不是很麻烦。

## 安装Autosub
安装方法参考Readme就好，是一个Python脚本，使用pip安装一下就好了。

```
apt install ffmpeg python3 curl git -y
curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
python3 get-pip.py
pip install git+https://github.com/BingLingGroup/autosub.git@dev ffmpeg-normalize langcodes
```

## 参考
https://github.com/BingLingGroup/autosub

最后顺便推荐几个YouTube视频以及字幕相关的网站
字幕在线编辑 https://www.nikse.dk/SubtitleEdit/Online
强烈推荐的Youtube字幕下载，可以直接下载原文和翻译 https://downsub.com/
另一个Youtube字幕下载 https://savesubs.com/
Youtube 视频下载 https://y2mate.is/en8/
Youtube 视频下载，支持多格式 https://btclod.com/

