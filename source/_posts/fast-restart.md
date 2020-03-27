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
主要是三类内核Configure： NVDIMM，DAX和PMEM相关的都打开吧。
```
	CONFIG_X86_PMEM_LEGACY_DEVICE=y
	CONFIG_X86_PMEM_LEGACY=m
	CONFIG_BLK_DEV_PMEM=m
	CONFIG_ARCH_HAS_PMEM_API=y
	
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
含义是，需要在内存中4G的位置开始，预留2G的内存空间。[了解更详细的memmap用法及含义](https://docs.pmem.io/persistent-memory/getting-started-guide/creating-development-environments/linux-environments/linux-memmap)。

### QEMU准备
#### 下载QEMU
```
git clone git://git.qemu.org/qemu.git
```
其中包含了几个子模块，会在编译过程中下载。但是如果在墙内的网络环境中，通常这会失败，下面是墙内的步骤：
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
直到这样的状态就可以放心编译QEMU了：
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
可以通过DAX设备（DAX device）或者DAX文件（DAX file)两种方式来达到同样的效果。

#### 方法一：DEV device实现方法
使用`/dev/dax0.0`作为vNVDIMM的后端（backend）

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
两点说明：
* `-object memory-backend-file,id=dimm0,size=4g,mem-path=/dev/dax0.0,share=on,pmem=on,align=2M`意思是：
 * 创建一个容量为`4g`的后端存储设备，设备节点路径是`/dev/dax0.0`，所以对这个虚拟NVDIMMM设备（vNDVIMM）设备的访问，都会走到`/dev/dax0.0`
 * `share=on` 控制虚拟机写操作的可见性。如果share=on，那么虚拟机对这个存储设备的“写”操作会提交到设备上，同时，如果有其他虚拟机使用同一个存储设备，上面的“写”操作同样会被“看”到。如果share=off,那么虚拟机的“写”操作不会被提交到存储设备，也因此其他虚拟机无法“看“到此虚拟机”写“的内容。
 * `pmem=on` 同时需要满足QEMU编译的时候，打开了libpmem支持（--enable-libpmem）, 此时QEMU会保证虚拟机的对vNVDIMM设备的“写”操作的“持续性”；但如果这时候QEMU并没有enable libpmep，虚拟机会创建失败并且提示"lack of libpmem support"。
 * `align=2M` DAX设备需要2M对齐。

* `-numa node,memdev=dimm0,cpus=0` 意思是：
描述虚拟机的numa结构，这里主要是为了使用上一步创建的vNVDIMM作为虚拟机的内存。
[了解更详细的vNVDIMM用法及含义](https://docs.pmem.io/persistent-memory/getting-started-guide/creating-development-environments/virtualization/qemu)。

这样虚拟机就创建好了，登录虚拟机（通过vncview :7）做点你想要做的事情。

2. 保存虚拟机现场
在QEMU console中输入HMP命令，并且退出QEMU
```
(qemu) migrate_set_capability x-ignore-shared on	//设置QEMU在保存VM的时候，忽略share=on的那些内存。这里指代不保存VM的pmem。
(qemu) stop						//停止虚拟机
(qemu) savevm s0					//保存虚拟机snapshot为s0
(qemu) q						//退出QEMU
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
  在QEMU console中输入HMP命令，重新加载snapshot s0
  ```
(qemu) stop
(qemu) loadvm s0
(qemu) c
```

#### 方法二：DAX file实现方法
使用DAX file实现时，是用一个支持文件（支持影射为pmem）作为后端。“写”操作的“持续性”是“宿主机”的内核来支持（v4.15之后）。

0. 创建虚拟机前的准备工作
```
mkfs.ext4 -b 4096 -E stride=512 -F /dev/pmem0		//格式化pmem设备
mount -t ext4 -o dax /dev/pmem0 /dax			//把pmem设备mount到一个目录，支持DAX
```

1. 创建虚拟机
```
x86_64-softmmu/qemu-system-x86_64 \
	--enable-kvm \
	-M q35 \
	-m 4G -smp 1 \
	-hda $IMAGE_PATH/ubuntu-1904.qcow2 \
	-enable-dax -mem-path /dax \
	-device vfio-pci,host=81:00.0,romfile= \
	-monitor stdio \
	-vnc :7
```
* `-mem-path /dax` ：为虚拟机分配内存，使用一个临时创建的文件路径。这里是指之前mount的pmem0设备
* `-enable-dax`： 正在努力upstream…… :p

2. 保存虚拟机现场
在QEMU console中输入HMP命令，并且退出QEMU
```
(qemu) migrate_set_capability x-ignore-shared on	//设置QEMU在保存VM的时候，忽略share=on的那些内存。这里指代不保存VM的pmem。
(qemu) stop						//停止虚拟机
(qemu) savevm s0 -dax-no-save				//保存虚拟机snapshot为s0
(qemu) q						//退出QEMU
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
	-enable-dax -mem-path /dax \
	-loadvm s0,mode=dax \
	-device vfio-pci,host=81:00.0,romfile= \
	-monitor stdio \
	-vnc :7
```
* `-loadvm` 正在努力upstream…… :p

至此，虚拟机又可以接着之前的地方呼啸的跑下去了。效果看下面的视频吧：

<iframe height=360 width=640 src='https://player.youku.com/embed/XNDQ3MTkyMTYzNg==' frameborder=0 'allowfullscreen'></iframe>
[快速启动演示](http://v.youku.com/v_show/id_XNDQ3MTkyMTYzNg==.html?spm=a2h3j.8428770.3416059.1)
