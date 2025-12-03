# 网易云音乐下载器

基于Python3.X编写的网易云音乐命令行下载器，自动下载专辑封面，记录歌手名、音乐标题、专辑名等元数据，并写入[ID3 Tags][1] metadata容器。在github上试了几个高星的下载器都没有写入专辑封面，对于强迫症患者简直不能忍，于是一怒之下决定自己写。

## Preview

![Preview](preview.gif)

## Installation

本项目使用现代化的 Python 包管理工具 [uv](https://docs.astral.sh/uv/)。

### 前置要求

- Python 3.10 或更高版本
- [uv](https://docs.astral.sh/uv/) 包管理工具

### 安装 uv

**macOS / Linux:**

```bash
brew install uv
```

或者使用官方安装脚本：

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Windows:**

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 安装项目

首先克隆源码：

```bash
git clone https://github.com/codezjx/netease-cloud-music-dl.git
cd netease-cloud-music-dl
```

创建虚拟环境并安装项目：

```bash
uv venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
uv pip install -e .
```

安装成功后，可以通过 `ncm` 命令使用本工具。

## Feature

- 支持下载专辑封面并嵌入音乐文件
- 支持写入歌手名、音乐标题、专辑名、专辑艺人、作曲、曲序/碟号、别名、公司等信息至[ID3 Tags][1]
- 支持写入歌词/翻译歌词（ID3 USLT/TXXX，FLAC Vorbis Comment），并为 FLAC 写入对应标签与封面
- 多碟专辑自动打上碟号/每碟曲序，并在文件名加前缀（示例：`1-01 SongName.flac`）；单碟不加前缀
- 歌单下载会按曲目所属专辑抓取碟信息，保持碟号/曲序准确
- 自动探测实际音频格式，如果请求 FLAC 但返回 MP3 会重命名为 .mp3 再写标签
- 支持跳过已下载的音频文件
- 支持常见设置选项，如：保存路径、音乐命名格式、文件智能分类等
- 支持多种音质选择：FLAC无损、320k、192k、128k（默认FLAC，若无损不可用则自动降级至320k）
- 支持使用账号Cookie下载VIP/付费音乐
- 支持下载单首/多首歌曲
- 支持下载歌手热门单曲（可配置最大下载数）
- 支持下载专辑所有歌曲
- 支持下载公开歌单所有歌曲

**（注意：已下架的音乐暂时无法下载）**

### 关于请求频率 / 限速

- 当前实现是串行逐首下载，且每首之间随机 `0.6~1.6s` 延迟，没有并发；通常不会瞬时打太多请求。
- 如果短时间批量下大量歌曲，建议自行控制频率（如分批执行或加代理），以降低被限流/封禁风险。
- 遇到 FLAC 不可用会自动降级到 320k 再下载；若返回 MP3 但扩展名为 .flac，会自动识别并重命名后写标签。

通过`ncm -h`即可查看所支持的参数列表：

```bash
$ ncm -h
usage: ncm [-h] [-s song_id] [-ss song_ids [song_ids ...]] [-hot artist_id]
           [-a album_id] [-p playlist_id]

optional arguments:
  -h, --help            show this help message and exit
  -s song_id            Download a song by song_id
  -ss song_ids [song_ids ...]
                        Download a song list, song_id split by space
  -hot artist_id        Download an artist hot 50 songs by artist_id
  -a album_id           Download an album all songs by album_id
  -p playlist_id        Download a playlist all songs by playlist_id
```

## Usage

### 下载单曲

使用参数`-s`，后加歌曲id或者歌曲完整url，如：

```bash
$ ncm -s 123123
or
$ ncm -s http://music.163.com/#/song?id=123123
```

### 下载多首歌曲

使用参数`-ss`，后加歌曲ids或者歌曲完整urls(id或url之间通过空格隔开)，如：

```bash
$ ncm -ss 123123 456456 789789
or
$ ncm -ss url1 url2 url3
```

### 下载某歌手的热门单曲(默认下50首，可配置)

使用参数`-hot`，后加歌手id或者完整url，如：

```bash
$ ncm -hot 123123
or
$ ncm -hot http://music.163.com/#/artist?id=123123
```

### 下载某张专辑的所有歌曲

使用参数`-a`，后加专辑id或者完整url，使用方法同上。

### 下载某个公开的歌单

使用参数`-p`，后加歌单id或者完整url，使用方法同上，必须确认是**公开**的歌单才能下载哦。

## Settings

配置文件在在用户目录下自动生成，路径如下：

```
/Users/yourUserName/.ncm/ncm.ini
```

目前支持以下几项设置：

```
[settings]

#--------------------------------------
# 热门音乐的最大下载数，默认50
# Range: 0 < hot_max <= 50
#--------------------------------------
download.hot_max = 50

#--------------------------------------
# 音乐文件的下载路径，默认在用户目录.ncm/download目录下
#--------------------------------------
download.dir = /Users/yourUserName/.ncm/download

#--------------------------------------
# 音频质量，可选值：
# flac  - 无损FLAC格式（最佳音质，文件较大）
# 320k  - 高品质MP3 320kbps
# 192k  - 中等品质MP3 192kbps
# 128k  - 标准品质MP3 128kbps
# 默认值：flac
#--------------------------------------
download.audio_quality = flac

#--------------------------------------
# 音乐命名格式，默认1
# 1: 歌曲名
# 2: 歌手 - 歌曲名
# 3: 歌曲名 - 歌手
#--------------------------------------
song.name_type = 1

#--------------------------------------
# 文件智能分类，默认1
# 1: 不分文件夹
# 2: 按歌手分文件夹
# 3: 按歌手/专辑分文件夹
#--------------------------------------
song.folder_type = 1

[auth]

#--------------------------------------
# 网易云音乐账号Cookie（可选）
# 用于下载VIP/付费音乐
# 获取方法：
# 1. 在浏览器中登录 music.163.com
# 2. 打开开发者工具（F12）-> Network（网络）标签
# 3. 刷新页面，找到任意请求
# 4. 复制请求头中的 Cookie 值
#--------------------------------------
auth.cookie =
```

**Warning:** 智能分类设置目前只针对`-s`和`-ss`参数有效，`-hot/-a/-p`分别会存于后缀为：`-hot50/-album/-playlist`的文件夹中，方便管理本地音乐。

## Feedback

如果遇到Bugs，欢迎提issue或者PR，谢谢各位支持~

## License

MIT License

Copyright (c) 2017 codezjx <code.zjx@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

[1]: https://zh.wikipedia.org/wiki/ID3
