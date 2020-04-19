---
title: 由浅入深CrosVM（四）—— 虚拟机的键盘鼠标输入
donate: true
date: 2020-04-19 16:07:41
categories: CrosVM
tags: crosvm
---

接上篇，我们起了图形以及桌面之后，发现没有办法通过虚拟机窗口与其交互。
这篇文章我们简单说下如何跟虚拟机进行交互。

## 模拟鼠标键盘事件
在用CrosVM创建虚拟机的时候，加上下面的参数
`--display-window-keyboard --display-window-mouse`

这样，当鼠标移动到虚拟机窗口范围内的时候，所有的鼠标和键盘事件就会被映射给虚拟机的鼠标和键盘事件。

优点：参数使用方便
缺点：对于Host中已经定义过的全局快捷键，即便在虚拟机中执行，也会被Host系统捕获，比如切换终端Ctrl+Alt+F2

## 键盘和鼠标passthrough给虚拟机
首先查看host OS中键盘鼠标的event:
```
# ls /dev/input/
```
确定需要passthrough的键盘和鼠标使用的是哪两个event。
这里我没有好方法，对input device的研究不是很深入。通过插拔键盘鼠标，确定想要passthrough给虚拟机的键盘和鼠标。
比如键盘和鼠标分别是`event3`和`evnet4`那么就给CrosVM添加参数:
```
--evdev /dev/input/event3 --evdev /dev/input/event4
```

优点：虚拟机拥有全部的键盘和鼠标。
缺点：已经passthrough的键盘和鼠标不再控制Host，如果Host也需要交互的话，需要Host接两道键盘和鼠标。且系统中event不是固定不变的，CrosVM的相对复杂一点。

这篇先写到这里吧，对于code分析，放在日后吧～ :p
