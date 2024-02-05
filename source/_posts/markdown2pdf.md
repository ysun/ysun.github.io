---
title: Markdown文档转为PDF
donate: true
date: 2024-02-05 14:52:50
categories:
tags:
---

## 安装 pandoc 及依赖
安装pandoc 和 LaTeX 引擎
使用 pandoc 转换文档为 pdf，需要安装在操作系统上安装 latex（默认使用 LaTeX 引擎），否则会出现错误 pdflatex not found. Please select a different --pdf-engine or install pdflatex。

```bash
sudo apt install pandoc texlive-latex-base texlive-extra-utils texlive-latex-extra texlive-lang-chinese
```

XeLaTeX 是使用 LaTeX 的排版引擎。对于中文文档，pdflatex 转换会出现字符集不支持的问题，可以使用参数指定 xelatex 引擎来转换中文文档。
```bash
sudo apt install texlive-xetex
```

## 安装字体
### 拷贝字体
将windows的字体拷贝至Ubuntu系统目录/usr/share/fonts下，比如在WSL上

```bash
mkdir -p /usr/share/fonts/truetype/windowsfont
sudo cp -r /mnt/c/Windows/Fonts/* /usr/share/fonts/truetype/windowsfont/
```

### 安装字体
```bash
mkfontscale
mkfontdir
fc-cache -fv
```
注意：如果不存在 fc-cache 命令，需要安装 fontconfig:
```bash
sudo apt install fontconfig。
```

### 查询字体是否安装成功
```bash
fc-list :lang=zh
```

### 指定字体生成pdf
* 编译pandoc默认的latex引擎是pdflatex，是不支持中文的，因此需要手动设置编译时所用的引擎为xelatex，编译命令改为：
```bash
pandoc file_name.md --pdf-engine=xelatex -o file_name.pdf -V mainfont='Microsoft YaHei'
```

```bash
./pandoc --variable papersize=A4 --variable "geometry=margin=1.2in" --variable mainfont='Microsoft YaHei' --variable sansfont='Microsoft YaHei' --variable monofont='Microsoft YaHei' --pdf-engine=xelatex -s test.md -o test.pdflatex
```

* 其中 --variable "geometry=margin=1.2in" 为四周统一边距的设置，或者使用 margin-left、margin-right、margin-top、margin-bottom 逐个设置。

* 变量 --variable 可以使用大写的 -V 来替代，例如 -V monofont='Microsoft YaHei'

### 导出pandoc转换为时的latex默认模板
```bash
pandoc -D latex > template.LaTeX
```

在template.latex里添加中文字体支持:
```configure
\usepackage{fontspec}   % 允許設定字體
  \usepackage{xeCJK}    % 分開設置中英文字型
  \setCJKmainfont{SimSun}   % 設定中文字型
  \setmainfont{Helvetical}  % 設定英文字型
  \setromanfont{Helvetical}   % 字型
  \setmonofont{Courier New}
  \linespread{1.2}\selectfont   % 行距
```

然后把所有*font的地方改成'Microsoft YaHei'


## 基于docker的使用方法
以上内容我们还需要在本地Linux上安装环境，如果使用 pandoc 的 docker镜像 将会使这一切都变的更简单。
示例：
### 设置运行命令的别名
```bash
alias pandock='docker run --rm -v "$(pwd):/data" -u $(id -u):$(id -g) pandoc/latex'
```

### 转换一个 markdown 文档为 word 文件
```bash
pandock -s test.md -o test.docx
```

## 其他
https://miktex.org/download

## 参考文档
[使用pandoc 生成带中文的pdf](https://blog.csdn.net/m0_47696151/article/details/124322754)
[Pandoc with Chinese](https://github.com/jgm/pandoc/wiki/Pandoc-with-Chinese)
[在 Linux 下安装字体](https://github.com/jgm/pandoc/wiki/Pandoc-with-Chinese)
[pandoc/latex docker](https://hub.docker.com/r/pandoc/latex)

