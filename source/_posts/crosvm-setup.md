---
title: 由浅入深CrosVM（一）—— 如何在Ubuntu中搭建CrosVM
donate: true
date: 2020-03-30 10:27:44
categories: ChromeOS
tags: ChromeOS Crosvm KVM
---

## 什么是CrosVM
CrosVM是Chrome操作系统中，用于创建虚拟机的应用。是一个Rust编写的轻量级的虚拟机。亚马逊的Firecracker从crosvm开始。借助于CrosVM 用户可以很容易的在ChromeOS中运行Linux、Android以及Windows应用程序。

[CrosVM](https://chromium.googlesource.com/chromiumos/platform/crosvm) 的源码是Google ChromeOS的一部分，但也可以独立编译使用。哎，还是那句话“不要问为什么连接打不开”。还好github.com有好多CrosVM的镜像，有需要的可以上去找下。
本文，我们着重描述下如何在Ubuntu 19.10中使用CrosVM创建一个Linux 虚拟机。

## 环境准备
### 安装minijail
这个是CrosVM 打开feature ’sandbox‘时需要的，因为是默认打开的，这里就罗列一下。如果编译有问题，或者很费劲，可以在运行crosvm的时候加上'--disable-sandbox' 参数即可。
```
git clone https://android.googlesource.com/platform/external/minijail
cd minijail
make
make install
```

## 编译CrosVM
```
git clone https://chromium.googlesource.com/chromiumos/platform/crosvm
cd crosvm

cargo build
cargo build --features=gpu,x #BTW, 如果需要图形加速，需要打开gpu和x

mkdir -p /usr/share/policy/crosvm/                #这里面是CrosVM运行时的一些policy配置
cp -r iseccomp/x86_64/* /usr/share/policy/crosvm/
```

## 准备虚拟镜像
```
# 创建一个空的image，大小是20G
dd if=/dev/zero of=ubuntu19.10_rootfs.img bs=1M count=20480
方法2：
qemu-img create -f raw ubuntu19.10_rootfs.img 20G

# 格式化
mkfs.ext4 ubuntu19.10_rootfs.img

mkdir rootfs/
sudo mount ubuntu19.10_rootfs.img rootfs/

# 下载Ubuntu 19.10文件系统(eoan)
debootstrap --arch amd64  eoan rootfs/ http://archive.ubuntu.com/ubuntu

sudo umount rootfs/
```
对镜像的一些修改：
```
sudo mount ubuntu19.10_rootfs.img rootfs/

# 去掉rootfs中的密码：
vim /etc/passwd
root:x:0:0:root:/root:/bin/bash
取缔 root: 后面的那个x

```

## 创建虚拟机
```
sudo LD_LIBRARY_PATH=~/project/vm/minijail/ ./target/debug/crosvm run --rwroot ubuntu19.10_rootfs.img --seccomp-policy-dir=/usr/share/policy/crosvm/x86_64/ -i /boot/initrd.img-4.13.0-46-generic /boot/vmlinuz-4.13.0-46-generic

sudo ./target/debug/crosvm run --disable-sandbox --rwroot rootfs.ext4 --seccomp-policy-dir=./seccomp/x86_64/ -i /boot/initrd.img-4.13.0-46-generic /boot/vmlinuz-4.13.0-46-generic
```

运气好的话，在创建VM的终端里面，应该可以看到Kernel启动的log，最后停在登录提示符。输入root 并回车，就可以直接登录虚拟机了。
