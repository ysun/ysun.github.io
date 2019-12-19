---
title: 利用虚拟机(QEMU)实现宿主机快速重启
donate: true
date: 2019-12-18 21:28:40
categories: QEMU
tags: KVM QEMU
---

## 为什么这么做？
1. 系统完成一次重启的时间太久。
1. 越来越频繁的安全相关的紧急的升级，包括Firmware/microcode/OS/VMM/QEMU。
3. 运行中断给“云”服务提供商带来不好的用户体验。

## 目前已有的类似方案
1. Live patch在线补丁；
2. 虚拟机热迁移；

这里暂且不评价各个方案的优劣，仅仅是想提供一个选择3！ 重点是，简单快捷，包教包会。

## 方案的工作流程

1. 运行QEMU创建VM，在VM中进行任何操作。
2. 将现有的虚拟机（VM）保存（Snapshot）到内存（pmem）中。
3. 退出qemu，并且可以使用kexec软重启系统，同时可以升级内核、QEMU、Microcode 等。
4. 重新运行QEMU，恢复VM使其继续执行。


``` flow
step1=>operation: 创建虚拟机。
step2=>operation: 保存虚拟机到pmem。
step3=>operation: 退出QEMU、更新kernel、Microcode等升级。
step4=>operation: 重新运行QEMU，恢复VM使其继续执行。

step1->step2->step3->step4

```

### 内核准备
#### 编译内核
大概率需要重新编译一个内核，确保所有的所需kernel config都打开。
主要是两类DAX和PMEM相关的都打开吧。

```
	CONFIG_X86_PMEM_LEGACY_DEVICE=y
	CONFIG_X86_PMEM_LEGACY=m
	CONFIG_BLK_DEV_PMEM=m
	CONFIG_DEV_DAX_PMEM=m
	CONFIG_DEV_DAX_PMEM_COMPAT=m
	CONFIG_ARCH_HAS_PMEM_API=y
	
	CONFIG_NVDIMM_DAX=y
	CONFIG_DAX_DRIVER=y
	CONFIG_DAX=y
	CONFIG_DEV_DAX=y
	CONFIG_DEV_DAX_PMEM=m
	CONFIG_DEV_DAX_KMEM=m
	CONFIG_DEV_DAX_PMEM_COMPAT=m
	CONFIG_FS_DAX=y
	CONFIG_FS_DAX_PMD=y

	CONFIG_LIBNVDIMM=m
	CONFIG_NVDIMM_PFN=y
	CONFIG_NVDIMM_DAX=y
	CONFIG_NVDIMM_KEYS=y
```
#### 内核参数
```
	memmap=2G!4G
```
含义是，需要在内存中4G的位置开始，预留2G的内存空间。

### QEMU准备
#### 下载QEMU
这里需要提一下的是QEMU的下载过程，原因是在墙外的网络环境，是可以一条命令搞定：
```
git clone git://git.qemu.org/qemu.git
```
然后其中子模块在编译过程中下载。 但是如果在墙内的网络环境中，这样做会失败，下面是墙内的步骤：
```
git clone git://git.qemu.org/qemu.git
cd qemu
git submodule init
git submodule update --recursive
```

如果在`git submodule update`的过程中出现某个module下载失败，需要手动下载到相应的目录里，路径通常在错误日志中会提到
```
git clone http://git.qemu.org/git/seabios.git/  roms/seabios
git submodule update --recursive
```
知道这样的状态就可以放心编译QEMU了：
```
git submodule status --recursive
65cc4d2748a2c2e6f27f1cf39e07a5dbabd80ebf dtc (v1.4.0)
87eea99e443b389c978cf37efc52788bf03a0ee0 pixman (pixman-0.32.6)
b4c93802a5b2c72f096649c497ec9ff5708e4456 roms/SLOF (qemu-slof-20141202-63-gb4c9380)
4e03af8ec2d497e725566a91fd5c19dd604c18a6 roms/ipxe (v1.0.0-2016-g4e03af8)
3caee1794ac3f742315823d8447d21f33ce019e9 roms/openbios (3caee17)
c559da7c8eec5e45ef1f67978827af6f0b9546f5 roms/openhackware (heads/master)
c87a92639b28ac42bc8f6c67443543b405dc479b roms/qemu-palcode (heads/master)
33fbe13a3e2a01e0ba1087a8feed801a0451db21 roms/seabios (rel-1.8.2)
23d474943dcd55d0550a3d20b3d30e9040a4f15b roms/sgabios (heads/master)
2072e7262965bb48d7fffb1e283101e6ed8b21a8 roms/u-boot (v2014.07-rc1-79-g2072e72)
19ea12c230ded95928ecaef0db47a82231c2e485 roms/vgabios (heads/master)
```

#### 编译QEMU
QEMU的编译并没有什么特别的，参数都可以“顾名思义” :)
```
./configure --target-list=x86_64-softmmu --enable-kvm --enable-libpmem --enable-vnc --enable-gtk --disable-werror

make
```

### 具体步骤
1. 创建虚拟机
```
x86_64-softmmu/qemu-system-x86_64 \
        --enable-kvm \
   	-M q35 \
        -m 2G -smp 1 \
        -hda ubuntu-1904.qcow2 \
        -object memory-backend-file,id=dimm0,size=4g,mem-path=/dev/dax0.0,share=on,pmem=on,align=2M \
        -numa node,memdev=dimm0,cpus=0 \
        -monitor stdio \
        -vnc :7
```
登录虚拟机做点你想要做的事情。

2. 保存虚拟机现场
在QEMU console中输入HMP命令，并且推出QEMU

```
(qemu) stop
(qemu) savevm s0
(qemu) q
```

3. 升级操作系统
这个时候，可以对宿主机为所欲为，比如更新QEMU，更新microcode，安装新kernel，kexec软重启。
kexec的使用方法:
```
kernel_image="/boot/vmlinuz-`uname -r`"   
initrd_image="/boot/initrd.img-`uname -r`"
sudo kexec -l $kernel_image --reuse-cmdline --initrd=$initrd_image
```

4. 重启QEMU，恢复虚拟机现场
```
x86_64-softmmu/qemu-system-x86_64 \
        --enable-kvm \
        -M q35 \
        -m 4G -smp 1 \
        -hda $IMAGE_PATH/ubuntu-1904.qcow2 \
        -object memory-backend-file,id=dimm0,size=4g,mem-path=/dev/dax0.0,share=on,pmem=on,align=2M \
        -numa node,memdev=dimm0,cpus=0 \
        -S \
        -monitor stdio \
        -vnc :7
```
在QEMU console中输入HMP命令，并且推出QEMU

```
(qemu) stop
(qemu) loadvm s0
(qemu) c
```

至此，虚拟机又可以接着之前的地方呼啸的跑下去了。效果看下面的视频吧：


[快速启动演示](http://v.youku.com/v_show/id_XNDQ3MTkyMTYzNg==.html?spm=a2h3j.8428770.3416059.1)

