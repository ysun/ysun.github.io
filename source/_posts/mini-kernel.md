---
title: 创建一个mini内核
donate: true
date: 2021-05-09 11:20:28
categories:
tags:
---

本文我们来解释下怎样创建一个mini x86操作系统。当然这个操作系统小到并不具备一个操作系统应该具有的功能，而仅仅是打印一个字符串到显示器上。


## 概述
当打开的电脑的时候，处理器首先会从某个特别的闪存(ROM)中加载BIOS。BIOS会自检以及初始化硬件，然后会寻找可以启动的设备。如果找到，就把控制权交给bootloader。所谓bootloader，就是储存在设备开头并且可以执行的一小段程序代码。bootloader决定内核镜像在存储设备上的位置，并且把他们加载到内存中。bootloader还需要把CPU从实模式(real mode)切换到保护模式(protected mode)。为了向前兼容(real mode产生于1987年)，x86 CPU启动的时候是实模式，功能非常有限。

本文不涉及bootloader的实现，的确有些复杂，可能后面的博客在更新吧，如果有兴趣可以参考[Rolling Your Own Bootloader](https://wiki.osdev.org/Rolling_Your_Own_Bootloader)。但众多的bootloader，我们如何选择呢？

## Multiboot
对于bootloader，有一个现成的标准[Multiboot Specification](https://nongnu.askapache.com/grub/phcoder/multiboot.pdf)。内核只需要遵从这个标准，就可以启动了。下面我们就来从Multiboot 2 specification 和用的最为广泛的bootloader GRUB2开始着手。

为了遵从Multiboot2 bootloader的标准，内核必须以Multiboot Header开头，格式如下:

|Field|Type|Value|
|------|------|------|
|magic number	|u32	|0xE85250D6|
|architecture	|u32	|0 for i386, 4 for MIPS|
|header length	|u32	|total header size, including tags|
|checksum	|u32	|-(magic + architecture + header_length)|
|tags		|variable|	|
|end tag	|(u16, u16, u32)|	(0, 0, 8)|

改写成x86汇编语言，长这样(Intel syntax):

```
section .multiboot_header
header_start:
    dd 0xe85250d6                ; magic number (multiboot 2)
    dd 0                         ; architecture 0 (protected mode i386)
    dd header_end - header_start ; header length
    ; checksum
    dd 0x100000000 - (0xe85250d6 + 0 + (header_end - header_start))

    ; insert optional multiboot tags here

    ; required end tag
    dw 0    ; type
    dw 0    ; flags
    dd 8    ; size
header_end:
```
* Multiboot header存在名为.multiboot_header的section中，我们稍后会用到这个名字
* header_start 和 header_end是标签，用来标记内存位置/地址，用来计算方便的计算这个header的长度。
* `dd`表示define double(32bit), `dw`代表define word(word 64bit)。他们只会输出给定的32bit/16bit常量。
* Header中的checksum最后这样计算是为了防止出现警告。如果使用前面表格里的公式`-(magic + architecture + header_length)`需要'带符号的32bit' sign 32，而文档中使用无符号整型`u32`。所以如果使用负号不满足u32这个类型，引入编译时一个警告。所以从0x100000000 (= 2^(32))减掉，并且保持u32，而不会被截断，也没有引入负号，尽管计算结果跟有符号位是会一样的。:) 

然后可以很方便的使用工具`nasm`来把这个文件汇编，multiboot_header.asm。 using nasm. It produces a flat binary by default, so the resulting file just contains our 24 bytes (in little endian if you work on a x86 machine):

```
> nasm multiboot_header.asm
> hexdump -x multiboot_header
0000000    50d6    e852    0000    0000    0018    0000    af12    17ad
0000010    0000    0000    0008    0000
0000018
```

## 启动代码
为了启动内核，我们需要加入一些能被bootloader调用的代码。创建一个文件，叫做boot.asm

```
global start

section .text
bits 32
start:
    ; print `OK` to screen
    mov dword [0xb8000], 0x2f4b2f4f
    hlt
```
* 全局label， start，作为内核的入口。
* 代码段 .text 是默认的可执行的代码。
* bits 32 说明后面的代码都是32-bit指令。在这里是有必要的，因为当GRUB开始执行内核的时候，CPU还住在保护模式(protected mode)。当我们后面切换到长模式(long mode)之后，才可以使用64-bit指令。
* mov dword 指令是把32bit常量0x2f4b2f4f赋值给内存地址0xb8000。(打印字符 OK 到显示器)。起始地址0xb8000是所谓的“VGA text buffer”. 是一个数组，显卡可以自动读取并且显示buffer里的字符到屏幕上。 每个屏幕上的字符是由一个8bit颜色代码和一个8bit的ASCII字符组成。这里用0x2f颜色，意思是白字绿色背景。0x4b表示ASCII的字符K，0x4f代码ASCII的字符O。
* 最后一个hlt是CPU停止指令。

然后再来些函数调用。`函数`可以理解为普通的标签，再加上结尾的返回指令(ret)。并且使用指令call来调用函数。相比较指令jmp，jmp仅仅是跳转到指定的内存地址，而call指令会使用push指令，在栈(stack)中保存一个返回的地址，然后ret指令会跳转到这个地址，返回到函数调用前。

但目前为止，系统还没有栈(stack)。栈指针(esp)目前可能指向了任意数据或者内存地址。所以，我们需要更新栈指针，让它指向有效的内存地址。

观察反汇编后的可执行文件:
```
> nasm boot.asm
> hexdump -x boot
0000000    05c7    8000    000b    2f4b    2f4f    00f4
000000b


> ndisasm -b 32 boot
00000000  C70500800B004B2F  mov dword [dword 0xb8000],0x2f4b2f4f
         -4F2F
0000000A  F4                hlt
```

## 编译可执行文件
要让GRUB执行boot文件，需要boot是一个ELF可执行文件。所以需要利用`nasm`创建ELF目标文件。为此，我们可以传参数`-f elf64`给nasm来实现。

同时，为了创建ELF可执行文件，需要把这些目标文件链接到一起。这就需要一个自定义的链接脚本 linker.ld:

```
ENTRY(start)

SECTIONS {
    . = 1M;

    .boot :
    {
        /* ensure that the multiboot header is at the beginning */
        *(.multiboot_header)
    }

    .text :
    {
        *(.text)
    }
}
```
来理解一下这段脚本:
* `start`是入口点，bootloader加载完内核之后，会跳转到这里开始执行。
* `. = 1M;`设置第一个section的加载地址到1MB, 这是一个习惯性的内核加载地址。通常不希望把内核从0x0地址开始加载，因为1M地址一下，有很多特殊的内存区域，例如前面用到的VGA text buffer 0xb8000。
* 这个可执行文件有两个section: 文件开头的`.boot`，和紧跟着的`.text`段。
* 生成二进制中的`.boot`段，包含了所有code中名为'.multiboot_header'的段。并且确保是在生成二进制文件的开头。这对于GRUB来说是必须的，需要在可执行文件的开头处，查找multiboot header。
* 生成二进制中的`.text`段，包含了所有code中名为'.text'的段。

现在可以生成ELF目标文件并且使用连接脚本生成最终的可执行二进制:

```
> nasm -f elf64 multiboot_header.asm
> nasm -f elf64 boot.asm
> ld -n -o kernel.bin -T linker.ld multiboot_header.o boot.o
```
参数`-n`或者`--nmagic`很重要，这样会禁止段的自动重排列。否则链接器可能会自作主张的改变.boot段在可执行文件中的位置，导致GRUB无法找到Multiboot header。

得到ELF文件之后，可以使用工具objdump查看生成的代码段，以及.boot段

```
> objdump -h kernel.bin
kernel.bin:     file format elf64-x86-64

Sections:
Idx Name      Size      VMA               LMA               File off  Algn
  0 .boot     00000018  0000000000100000  0000000000100000  00000080  2**0
              CONTENTS, ALLOC, LOAD, READONLY, DATA
  1 .text     0000000b  0000000000100020  0000000000100020  000000a0  2**4
              CONTENTS, ALLOC, LOAD, READONLY, CODE
```

## 创建ISO
所有的BIOS都可以启动CD-ROM，所以这里创建一个开启动的CD-ROM镜像，包含上面创建的最小的内核以及GRUB bootloader。镜像内部的文件结构如下:

```
isofiles
└── boot
    ├── grub
    │   └── grub.cfg
    └── kernel.bin
```
* grub.cfg 指定了内核的名字，以及满足Multiboot2协议标准。内容如下:

```
set timeout=0
set default=0

menuentry "my os" {
    multiboot2 /boot/kernel.bin
    boot
}
```
完事具备了，现在可以生成ISO镜像了:
```
grub-mkrescue -o os.iso isofiles
```
如果grub-mkrescue不工作，尝试先的步骤，网上搜来的，笔者没有试过这个方法L:

```
make sure xorriso is installed (xorriso or libisoburn package)
If you're using an EFI-system, grub-mkrescue tries to create an EFI image by default. You can either pass -d /usr/lib/grub/i386-pc to avoid EFI or install the mtools package to get a working EFI image
on some system the command is named grub2-mkrescue
```
## 启动
可以启动了，还是借助QEMU在虚拟机中试下:

```
qemu-system-x86_64 -cdrom os.iso
```
在seaBIOS之后，虚拟机屏幕的左上角，有一个绿色的OK，说明前面的code都是工作了的。

## 总结
BIOS 从ISO镜像中加载bootloader(GRUB)。
Bootloader读内核ELF，并且找到Multiboot header。
Bootloader复制.boot和.text 段到内存中，分别为0x100000 和 0x100020的内存地址。
然后跳转到entry point (0x100020)，前面`objdump -f`可以获取这个入口地址。

内核打印绿色的OK到屏幕左上角，然后CPU HLT。当然也可以在物理机上测试镜像，只需要把ISO烧录到U盘上，然后从U盘启动即可。

## 自动创建
以上为了讲解，分布执行操作，现在可以用Makefile来自动化这个过程。但第一步还是需要创建一个文件夹，其中文件结构如下:

```
…
├── Makefile
└── src
    └── arch
        └── x86_64
            ├── multiboot_header.asm
            ├── boot.asm
            ├── linker.ld
            └── grub.cfg
```
Makefile 内如如下:

```
arch ?= x86_64
kernel := build/kernel-$(arch).bin
iso := build/os-$(arch).iso

linker_script := src/arch/$(arch)/linker.ld
grub_cfg := src/arch/$(arch)/grub.cfg
assembly_source_files := $(wildcard src/arch/$(arch)/*.asm)
assembly_object_files := $(patsubst src/arch/$(arch)/%.asm, \
	build/arch/$(arch)/%.o, $(assembly_source_files))

.PHONY: all clean run iso

all: $(kernel)

clean:
	@rm -r build

run: $(iso)
	@qemu-system-x86_64 -cdrom $(iso)

iso: $(iso)

$(iso): $(kernel) $(grub_cfg)
	@mkdir -p build/isofiles/boot/grub
	@cp $(kernel) build/isofiles/boot/kernel.bin
	@cp $(grub_cfg) build/isofiles/boot/grub
	@grub-mkrescue -o $(iso) build/isofiles 2> /dev/null
	@rm -r build/isofiles

$(kernel): $(assembly_object_files) $(linker_script)
	@ld -n -T $(linker_script) -o $(kernel) $(assembly_object_files)

# compile assembly files
build/arch/$(arch)/%.o: src/arch/$(arch)/%.asm
	@mkdir -p $(shell dirname $@)
	@nasm -felf64 $< -o $@
```

* $(wildcard src/arch/$(arch)/*.asm) 包含了所有文件夹src/arch/$(arch)中的汇编文件，所以，如果有增加文件的话，不需要修改MAkefile文件。
* patsubst 操作是将src/arch/$(arch)/XYZ.asm 转变为 build/arch/$(arch)/XYZ.o
* $< 和 $@ 是两个自动变量，分别代表输入文件和输出文件。
命令`make iso` 会生成ISO，`make run`会直接启动QEMU虚拟机。
