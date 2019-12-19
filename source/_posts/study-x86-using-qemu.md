---
title: 利用虚拟机(QEMU)学习X86指令集0
donate: true
date: 2019-07-12 13:22:15
categories: X86
tags: X86 KVM QEMU
---

## 引言
接下来的几个日志，我会写几篇关于如何学习X86指令集，也是帮助自己梳理和记忆知识点。
下面是我大概总结了一下，一个操作系统需要掌握的知识点，仅供参考欢迎斧正！

## 学习内容

``` flow
blk_userspace=>parallel: 用户态应用程序
blk_kernel=>parallel: Linux内核/模块 
blk_64bit=>parallel: IA32e指令|invalid
blk_bios=>parallel: BIOS/UEFI 部分设计的指令|approved
blk_hardware=>parallel: 系统硬件

blk_kernel_study=>parallel: linux-kernel-module-cheat:>https://github.com/cirosantilli/linux-kernel-module-cheat
blk_64bit_study=>parallel: KVM Unit Test|future:>http://www.linux-kvm.org/page/KVM-unit-tests
blk_bios_study=>parallel: x86-bare-metal-examples:>https://github.com/cirosantilli/x86-bare-metal-examples

blk_userspace(path1, bottom)->blk_kernel(path1, bottom)->blk_64bit(path1,bottom)->blk_bios(path1,bottom)->blk_hardware
blk_64bit(path2,right)->blk_64bit_study
blk_bios(path2,right)->blk_bios_study
blk_kernel(path2, right)->blk_kernel_study
```

上图用户层应用程序以及硬件部分暂不是本文考虑范围，中间的三个软件部分“Linux内核/模块”、“IA32e指令”以及“BIOS/UEFI部分指令”都可以通过本文的方法学习。需要说明的是，虽然这里划分了三个部分，并不是操作系统上的划分，只是一个建议的学习的阶段划分。

### BIOS/UEFI 部分设计的指令
是指硬件上电后CPU执行的最早期的指令。通常包括BIOS、boot loader等。
这部分可以通过[x86-bare-metal-examples](https://github.com/cirosantilli/x86-bare-metal-examples)来学习

### IA32e指令
是指操作系统已经经过一些初始化操作，例如开启页表、开启32bit或者32e模式、段寄存器初始化、开启中断（APIC/X2APIC)、开启SMP支持等。
在这样的环境中，我们可以更专注于X86指令集的研究。上述初始化过程可以等日后展开讲述。

### Linux内核/模块
基本上Linux 内核开发涵盖之前两个方面，只是上来就学习Linux内核有点复杂，代码量太大。并且，本系教程的重点在于学习X86指令，并不在Linux中复杂的功能实现。

## 如何利用QEMU学习
首先确保系统里安装了qemu，步骤略。大概有两种形式使用QEMU

### 编译
随便举个例子，来自kvm-unit-test:
```
gcc -m64 -g -Wall -fno-pic -no-pie -std=gnu99 -ffreestanding \
	-I /home/works/kvm-unit-tests/lib -I /home/works/kvm-unit-tests/lib/x86 -I ./lib \
	-c -o x86/tsc.o x86/tsc.c

gcc -I /home/works/kvm-unit-tests/lib -I /home/works/kvm-unit-tests/lib/x86 \
	-I lib -T /home/works/kvm-unit-tests/x86/flat.lds  -fno-pic -no-pie -nostdlib \
	x86/tsc.c x86/cstart64.o lib/libcflat.a /usr/lib/gcc/x86_64-linux-gnu/5/libgcc.a \
	-o x86/tsc.elf 

objcopy -O elf32-i386 x86/tsc.elf x86/tsc.flat  ##&& ./x86-run x86/tsc.flat
```
编译一个test case，代码如下：
```
int main(void)
{
        u64 t1, t2;
        asm volatile ("rdtsc" : "=a"(a), "=d"(d));
        t1 = a | ((long long)d << 32);

        asm volatile ("rdtsc" : "=a"(a), "=d"(d));
        t2 = a | ((long long)d << 32);

        printf("rdtsc latency %u\n", (unsigned)(t2 - t1));

        return 0;
}
```
这样得到一个测试两次rdtsc指令执行的时间差的测试`tsc.flat`。当然上面辣么麻烦的编译啊、链接啊都是为了得到最终的测试的binary，或者叫可执行文件？！我们后面有很多种方法以及机会得到这样的测试代码，如果读者一时没有成功，不要终止于此，不要气馁。

### 在虚拟机中作为内核直接运行(-kernel)
```
qemu-system-x86_64 -vnc none -serial stdio -machine accel=kvm -kernel x86/tsc.flat
```
这样运行的虚拟机，看上去并不真的像是一个“虚拟机”，因为没有窗口，仅仅是console端文字输出。但这样足够我们验证和尝试CPU 指令，而且非常的轻量。个人比较喜欢这样的运行方式。

### 制作一个镜像文件，并且使用QEMU启动
我们可以手动制作一个镜像，步骤如下。但最后一步安装grub的时候，需要的条件有点苛刻，需要本地装有较新版本的grub-x86_64-efi。如果本地没有环境的同学，可以直接跳过制作镜像，直接下载文末的制作好的镜像文件raw.img。

```
$  dd if=/dev/zero of=raw.img bs=512 count=1048576
1048576+0 records in
1048576+0 records out
536870912 bytes (537 MB, 512 MiB) copied, 1.22641 s, 438 MB/s

$ losetup /dev/loop0 raw.img
$ fdisk /dev/loop0
Welcome to fdisk (util-linux 2.27.1).
Changes will remain in memory only, until you decide to write them.
Be careful before using the write command.
Device does not contain a recognized partition table.
Created a new DOS disklabel with disk identifier 0xe68d8ac0.

Command (m for help): g
Created a new GPT disklabel (GUID: 93A91033-E421-48DD-88E9-662C17E83136).

Command (m for help): n
Partition number (1-128, default 1):
First sector (2048-999966, default 2048):
Last sector, +sectors or +size{K,M,G,T,P} (2048-999966, default 999966):
Created a new partition 1 of type 'Linux filesystem' and of size 487.3 MiB.

Command (m for help): t
Selected partition 1
Hex code (type L to list all codes): 1
Changed type of partition 'Linux filesystem' to 'EFI System'.
 
 
Command (m for help): w
  
#then to ensure the disk status
$ sudo fdisk -l /dev/loop0


#注意：
#1.the disk type must be gpt
#2.disk identifier should have sha id
#3.the type must be EFI System
Disklabel type: gpt
Disk identifier: 93A91033-E421-48DD-88E9-662C17E83136
Device       Start    End Sectors   Size Type
/dev/loop0p1  2048 999966  997919 487.3M EFI System
 
$ partprobe /dev/loop0
$ lsblk
loop0                   7:0    0 488.3M  0 loop
└─loop0p1             259:4    0 487.3M  0 loop
 
$ sudo mkfs.vfat -F 32 /dev/loop0p1
mkfs.fat 3.0.28 (2015-05-16)
$ mkdir /virtfs
$ mount -o rw,umask=000 /dev/loop0p1 /virtfs
$ grub-install --removable --root-directory=/virtfs --target=x86_64-efi  /dev/loop0p1
Installing for x86_64-efi platform.
Installation finished. No error reported.
 
$ cp /boot/grub/grub.cfg /virtfs/boot/grub/grub.cfg
```
同样，这里附上UEFI/OVMF的build 方法，但同样可以直接下载文末的binary，毕竟这不是本文的主要内容。
```
$ git clone git://github.com/tianocore/edk2.git
$ cd edk2
# Because the latest version is missing a file, switch to an older version
$ git checkout 984ba6a467
$ cd edk2
$ make -C BaseTools
$ . edksetup.sh
 
  
  $ vi Conf/target.txt
  #Find
  # ACTIVE_PLATFORM       = Nt32Pkg/Nt32Pkg.dsc
  # and replace it with
  # ACTIVE_PLATFORM       = OvmfPkg/OvmfPkgX64.dsc
  # Find
  #  TOOL_CHAIN_TAG        = MYTOOLS
  # and replace it with your version on GCC here for example GCC 4.6 will be used.
  # TOOL_CHAIN_TAG        = GCC5  //this is your gcc version
  # Find
  # TARGET_ARCH           = IA32
  # and replace it with 'X64' for 64bit or 'IA32 X64' to build both architectures.
  # TARGET_ARCH           = X64
  #mode detail:https://wiki.ubuntu.com/UEFI/EDK2
  $ build
  $ find -name "OVMF.fd"
  #./Build/OvmfX64/DEBUG_GCC5/FV/OVMF.fd
  $ vim ~/.bashrc
  # add this to bashrc "export OVMF_PATH=/home/huihuang/git/edk2/Build/OvmfX64/DEBUG_GCC5/FV/OVMF.fd"
  $ source ~/.bashrc
```

```
#!/bin/bash
        mkdir -p virt_fs
        sudo losetup /dev/loop7 raw.img
        partprobe /dev/loop7
        sudo cp x86/tsc.elf virt_fs/tsx.elf
#        sudo umount $(virt_fs_path)
```
上面这个脚本是将之前生成的tsx.flat文件copy到预先准备好的镜像里面。同时，需要确保镜像中的grub.cfg文件中有正确的entry：
```
menuentry 'acrn_unit_test' {
                recordfail
                load_video
                insmod gzio
                if [ x$grub_platform = xxen ]; then insmod xzio; insmod lzopio; fi
                insmod part_gpt
                insmod ext2
                set root='hd0,gpt0'
                search --no-floppy --fs-uuid --set=root --hint-bios=hd0,gpt0 --hint-efi=hd0,gpt0 --hint-baremetal=ahci0,gpt4  A807-B387
                multiboot /tsx.elf
}
```
要启动这个镜像需要使用OVMF（EDK2项目中的软件模拟的UEFI）。下面是QEMU的启动参数

```
        DISPLAY=:0 qemu-system-x86_64 --bios OVMF_CODE.fd \
	-drive file=raw.img,index=0,media=disk,format=raw \
	-serial mon:stdio -m 1024M -smp cpus=4 \
	-cpu  Nehalem,+sse,+avx,+xsave,+sse2,+sse3,+mpx,+fpu,level=13 #-vnc :0
```
这里所需的所有文件都放在文末以备下载。
这样启动的虚拟机，就有种仪式感了，QEMU会创建一个窗口，同时因为有UEFI/OVMF，所以可以看到一个虚拟的BIOS画面，然后还有GRUB的选择菜单，选择刚刚创建的tsx.elf的入口。

OVMF 点击下载：[OVMF](OVMF_CODE.fd)
raw.img 点击下载： [raw.img](raw.img)

### 调试虚拟机代码
请参考 {% post_link qemu-debug Debug QEMU with GDB %}

## 小结
自此如何利用虚拟机学习底层编程的准备工作都已经搞定，我们会在后面的文章里陆续介绍X86的指令。可能不一定系统，甚至可以说的是零碎。因为Intel SDM实在是太长了，能吃透个一章半节的就挺开心的了。仅仅是为想学相关技术的同学们一点点思路，有不对的地方请留言指正！
