---
title: Debug QEMU with GDB
donate: true
date: 2018-12-24 09:59:17
categories: QEMU
tags: QEMU
---

学习Qemu-KVM虚拟机最重要的一步——调试QEMU，我们这里提前帮大家简单的总结归纳一下。
Qemu的调试稍微有点特殊的地方就是，除了Qemu程序自身源代码的调试以外，我们可以通过Qemu+GDB来调试我们虚拟机程序。下面将两个不同方面的调试方法介绍一下。

## 1. 调试QEMU源码 ##

```
gdb --args x86_64-softmmu/qemu-system-x86_64 --enable-kvm -m 1024 -drive file=test.qcow2 -append console=ttyS0 -kernel /boot/vmlinuz -initrd /boot/initrd.gz
```

当然以上参数中从--enable-kvm开始之后的参数因人而异，不尽相同。执行过之后，就会进入gdb界面，就可以跟其他普通应用程序一样，进行单步调试、设置断点、查看栈、寄存器内容等

## 2. 调试虚拟机 ##

这部分是本文的重点。跟调试应用程序不同，调试虚拟机时gdb和qemu分开执行，似乎并不能用gdb来调用qemu。长话短说，先来看如何启动qemu：
```
./x86_64-softmmu/qemu-system-x86_64 -s -S --enable-kvm -m 1024 -hda test.qcow2
```

同样，参数从--enable-kvm开始之后的参数也都不是必须的。着重了解下两个必须的参数：
```
-s shorthand for -gdb tcp::1234
-S freeze CPU at startup (use 'c' to start execution)
```

然后新开一个终端执行gdb，这样就跟调试应用程序一样，会看到同样的'(gdb)' 提示符。
在提示符中输入
```
target remote localhost:1234
```
1234是默认用于远程调试连接的端口号。
然后设置断点"break *0x7c00"，这样就将一个断点设置在了bootloader被加载到的内存地址，接下来就任你玩了。
<pre>
[root@ccd-sdv6 ~]# gdb
GNU gdb (GDB) Red Hat Enterprise Linux 7.6.1-100.el7
Copyright (C) 2013 Free Software Foundation, Inc.
License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
This is free software: you are free to change and redistribute it.
There is NO WARRANTY, to the extent permitted by law.  Type "show copying"
and "show warranty" for details.
This GDB was configured as "x86_64-redhat-linux-gnu".
For bug reporting instructions, please see:
<http://www.gnu.org/software/gdb/bugs/>.
<font color=#0099ff face="黑体">(gdb) target remote localhost:1234</font>
Remote debugging using localhost:1234
0x0000fff0 in ?? ()
(gdb) c
Continuing.

Program received signal SIGINT, Interrupt.
0x00002bcb in ?? ()
<font color=#0099ff face="黑体">(gdb) b *0x7c00</font>
Breakpoint 1 at 0x7c00.

<font color=#0099ff face="黑体">(gdb) info breakpoints</font>
Num     Type           Disp Enb Address    What
1       breakpoint     keep y   0x00007c00
(gdb)
</pre>

## 顺便附上一些用到的gdb的快捷键以及命令 ##
### TUI 窗口
```
Ctrl + x, Ctrl + a
好像等效
Ctrl + x, a
```
一般也就按着Ctrl键，依次按下字母x 和a就可以再TUI和非TUI间切换

### TUI 窗口概述
在TUI模式中，可以显示以下几个窗口：

- 命令窗口
用于GDB调试时的命令输入和命令结果输出显示，与普通GDB窗口无异。
-  源代码窗口
用于显示程序源代码，包括当前运行行、中断以中断标识等。
- 汇编窗口
显示当前程序的汇编代码。
- 寄存器窗口
显示处理器的寄存器内容，当寄存器内容发生改变时会高亮显示。
源代码窗口和汇编窗口会高亮显示程序运行位置并以'>'符号标记。有两个特殊标记用于标识断点，第一个标记用于标识断点类型：
    - B : 程序至少有一次运行到了该断点
    - b : 程序没有运行到过该断点
    - H : 程序至少有一次运行到了该硬件断点
    - h : 程序没有运行到过该硬件断点
第二个标记用于标识断点使能与否:
    - \+ : 断点使能Breakpointis enabled. 
    - \- : 断点被禁用Breakpointis disabled. 

### 三窗口模式
```
Ctrl + 2
```
使TUI的上半部分分割成两个窗口，连接按此快捷键可在三种组合中切换。
寄存器窗口、代码窗口、汇编窗口 三个窗口只能同时显示两个，共3种组合。

### 更换激活窗口
```
Ctrl + o
```
之所以需要切换激活窗口，是因为有些快捷键，比如箭头上下左右，page up/down只有在当前窗口起作用

### GDB command
` c ` : continue
` r ` : run
` n ` : next
` s ` : step

### TUI 特有命令
`info win` ：显示正在显示的窗口大小信息
`layout next` ：显示下一个窗口
`layout prev` ：显示上一个窗口
`layout src` ：显示源代码窗口
`layout asm` ：显示汇编窗口
`layout split` ：显示源代码和汇编窗口
`layout regs` ：显示寄存器窗口
`focus next` ： 将一个窗口置为激活状态
`focus prev` ：将上一个窗口置为激活状态
`focus src` : 将源代码窗口置为激活状态
`focus asm` ：将汇编窗口置为激活状态
`focus regs` ： 将寄存器窗口置为激活状态
`focus cmd` ：将命令行窗口置为激活状态
`refresh` ： 更新窗口，与C-L快捷键同

`tuireg float` ：寄存器窗口显示内容为浮点寄存器
`tuireg general` ：寄存器窗口显示内容为普通寄存器
`tuireg next` ：显示下一组寄存器，预定义的寄存器组: general, float,system, vector,all, save,restore. 
`tuireg system` ：显示上一组寄存器
`update` ：更新源代码窗口到当前运行点
`winname + count` ：增加指定窗口的高度
`winname + count` ：减小指定窗口的高度
`tabset nchars ` : Set the width of tab stops to be nchars characters

### 条件断点：
在gdb中可以watch一个寄存器，命令：

```
watch $eax == 0x0000ffaa
```
另外，当我们想有条件的设置某一个断点的时候，命令如下：
```
break test.c:120 if $eax == 0x0000ffaa
```

![](gdb_tui.png)
