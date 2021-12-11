---
title: 使用 QEMU 调试内核
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
qemu-system-x86_64 \
        --enable-kvm \
        -m 2048 -smp 1 \
        -s -S \
        -cpu host \
        -hda /home/works/kvm/ubuntu20.10_mini.img \
        -kernel /home/works/linux-stable/arch/x86/boot/bzImage \
        -append "root=/dev/sda3 nokaslr console=ttyS0"

#       -bios ovmf/OVMF_CODE.fd \
#       -boot order=c,menu=off \
```
注意，这里有几个小坑：

* -smp 1 建议只要不是为了研究SMP并发，debug的时候就带着吧，gdb可能多线程不太能搞定的样子。
* -enable-kvm 开启了kvm support，添加断点的时候，可能需要使用`hbreak <xxx>`
* -kernel 如果VM镜像是UEFI support的话，那么需要使用这个参数，在vm image之外传递kernel image(bzImage)给QEMU。如果这样做了，还需要注意一点，就是跟内核匹配的模块，还是需要提前copy到vm image的`/lib/modules/`内的，否则kernel是用不了任何模块的。
* -append 给kernel传递参数，使用-kernel时，这个是必需的，比如`root=xxx`
* 需要在vm的kernel的启动参数里面加上`nokaslr`，关闭内核随机位置。By default, Linux® uses KASLR. Specify the nokaslr kernel parameter to disable kernel randomization, that is, cause the kernel to be loaded at its standard location.
* 使用-kernel 时，需要去掉OVMF bios

```
-s shorthand for -gdb tcp::1234
-S freeze CPU at startup (use 'c' to start execution)
```

然后新开一个终端执行gdb，参数如下，传递与上一步bzImage同一个build的vmlinux，作为符号表。
```
 gdb -tui /home/works/linux-stable/vmlinux
```
这样就跟调试应用程序一样，会看到同样的'(gdb)' 提示符，在提示符中输入：
```
target remote localhost:1234
```
1234是默认用于远程调试连接的端口号。
然后设置断点"hbreak *0x7c00"，这样就将一个断点设置在了bootloader被加载到的内存地址，接下来就任你玩了。
或者设置断点到内核入口函数`hb start_kernel`等。

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

<font color=#0099ff face="黑体">(gdb) hbreak start_kernel</font>

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

Reference: 
https://www.starlab.io/blog/using-gdb-to-debug-the-linux-kernel
https://www.kernel.org/doc/html/latest/dev-tools/gdb-kernel-debugging.html


