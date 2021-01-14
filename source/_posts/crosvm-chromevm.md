---
title: 创建ChromeOS虚拟机
donate: true
date: 2020-06-03 22:48:53
categories: QEMU
tags: QEMU
---

ChromeOS开发者们已经帮玩家实现了创建一个ChromeOS的虚拟机镜像。有兴趣的同学，可以玩一下。

## 编译ChromeOS
借助本文，顺便简介下ChromeOS的编译和打包过程
全文可以参考ChromeOS官方文档[developer_guide.md](https://chromium.googlesource.com/chromiumos/docs/+/master/developer_guide.md)
以及[quick-start-guide](https://sites.google.com/a/chromium.org/dev/chromium-os/quick-start-guide)

```
# 下载ChromeOS source code，还是那句话，不要问我为什么无法下载，需要科学上网
repo init -u https://chromium.googlesource.com/chromiumos/manifest.git --repo-url https://chromium.googlesource.com/external/repo.git 

# 大概N个小时之后，chroot 切换root到cros_sdk环境
cros_sdk

# 这步是为了方便后面使用。BOARD有很多类型，如果不是Google生产的笔记本，想把ChromeOS安装到PC上，或者是制作虚拟机镜像，都使用amd64-generic
export BOARD=amd64-generic
```

Apply 下面这个patch，或者手动改下，让SDK使用5.4的kernel，因为默认是4.14
```
diff --git a/overlay-amd64-generic/profiles/base/make.defaults b/overlay-amd64-generic/profiles/base/make.defaults
index 0c2aceb2ed..b529759635 100644
--- a/overlay-amd64-generic/profiles/base/make.defaults
+++ b/overlay-amd64-generic/profiles/base/make.defaults
@@ -20,7 +20,7 @@ USE=""

 USE="${USE} containers kvm_host crosvm-gpu virtio_gpu"

 -USE="${USE} legacy_keyboard legacy_power_button sse kernel-4_14"
 +USE="${USE} legacy_keyboard legacy_power_button sse kernel-5_4"

  USE="${USE} direncryption"

```
```
# 编译包，这里的jobs参数然而并没有什么用，--autosetgov是说让CPU高性能运转(performance)
./build_packages --board=${BOARD}  --autosetgov --jobs 16

# 打包安装镜像
./build_image --board=${BOARD} --noenable_rootfs_verification test
```
在编译完安装镜像之后，SDK会提示我们如何生成虚拟机镜像
```
./image_to_vm.sh --from=../build/images/amd64-generic/R85-13106.0.2020_06_02_0109-a1 --board=amd64-generic --test

```
生成了虚拟机镜像之后，SDK继续提示我们如何运行ChromeOS虚拟机
```
cros_vm --start --image-path /mnt/host/source/src/build/images/amd64-generic/R85-13106.0.2020_06_02_0109-a1/chromiumos_qemu_image.bin
```
cors_vm是一个Python脚本，其实就是组装了一个QEMU的命令行。可以直接运行下，就得到QEMU命令行了, 整理之后，这样

```
#DISPLAY=:0 qemu-system-x86_64 \
#    -m 8G -smp 8 \
#    -vga virtio \
#    -pidfile /tmp/cros_vm_9222/kvm.pid \
#    -cpu host \
#    -serial stdio \
#    -device 'virtio-net,netdev=eth0' \
#    -device 'virtio-scsi-pci,id=scsi' \
#    -device virtio-rng \
#    -device 'scsi-hd,drive=hd' \
#    -drive 'if=none,id=hd,file=./chromiumos_qemu_image.bin,cache=unsafe,format=raw' \
#    -netdev 'user,id=eth0,net=10.0.2.0/27,hostfwd=tcp:127.0.0.1:9222-:22' \
#    -enable-kvm

# 下面的参数也是cros_vm创建的命令行中的参数，由于QEMU升级等原因，在最新的QEMU里面，需要调整。后面会进一步更新
#    -serial file:/tmp/cros_vm_9222/kvm.monitor.serial \
#    -cpu 'SandyBridge,-invpcid,-tsc-deadline,check,vmx=on' \
#    -chardev 'pipe,id=control_pipe,path=/tmp/cros_vm_9222/kvm.monitor' \
#    -usbdevice tablet \
#    -mon 'chardev=control_pipe' \
#    -daemonize \
```
拿到QEMU的命令行之后，只要把镜像chromiumos_qemu_image.bin copy到任何一个Linux distribution，比如Ubuntu中，安装好QEMU，就可以跑起来了
![chrome-vm](chrome-vm.png)

顺带提一下，做个笔记吧：
生成了ChromeOS的安装镜像之后，安装到物理机上做法：
```
# 烧写到USB上
cros flash usb:// ${BOARD}/latest 

# 或者这样，明确的给出上一步生成的镜像，这个会在打包的最后提示里面有
cros flash usb:// ../build/images/amd64-generic/R85-13106.0.2020_06_02_0109-a1/chromiumos_test_image.bin

# 或者，如果局域网内已经有个ChromeOS的系统，可以远程烧录升级
cros flash 192.168.3.10 /path/to/image.bin
```
单独更新内核的方法:
```
cros_workon --board=${BOARD} start sys-kernel/chromeos-kernel-5_4
# remove old kernel from build
emerge-${BOARD} -C sys-kernel/chromeos-kernel-4_14
# OR
emerge-amd64-generic --unmerge chromeos-kernel-4_14

# build different kernel from local source
cd ~/trunk/src/third_party/kernel/v5.4
cros_workon_make --board=${BOARD} start sys-kernel/chromeos-kernel-5_4

# Configure Kernel
./chromeos/scripts/kernelconfig editconfig

# build image
emerge-${BOARD} sys-kernel/chromeos-kernel-5_4
Or
FEATURES="noclean" cros_workon_make --board=${BOARD} --install chromeos-kernel-5_4

# 远程安装kernel
~/trunk/src/scripts/update_kernel.sh --remote 10.239.159.52

```
编译安装Cros_SDK中的软件到package以及发布到ChromeOS的方法:
```
emerge-amd64-generic minigbm 
emerge-amd64-generic libepoxy 
emerge-amd64-generic virglrenderer 

cros deploy 10.239.159.37 minigbm
cros deploy 10.239.159.37 libepoxy
cros deploy 10.239.159.37 virglrenderer
```
