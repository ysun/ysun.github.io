---
title: 由浅入深CrosVM（一）—— 如何在Ubuntu中搭建CrosVM
donate: true
date: 2020-03-30 10:27:44
categories: CROSVM
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
apt install build-essential libcap-dev libfdt-dev pkg-config python cargo wayland-scanner++ python-is-python3
git clone https://android.googlesource.com/platform/external/minijail
cd minijail
make
cp libminijail.so libminijailpreload.so /usr/local/lib/
cp minijail0 /usr/local/bin
```
或者，如有有cros_sdk的话，在`~/trunk/src/aosp/external/minijail`目录中执行`cargo build`同样可以编译得到库文件，然后可以复制到/usr/local/lib/下面就好。

如果repo安装失败，手动安装一下：
```
curl https://storage.googleapis.com/git-repo-downloads/repo > /usr/local/bin/repo
chmod a+x /usr/local/bin/repo
```
## 编译安装CrosVM
```
mkdir crosvm
cd crosvm
repo init -g crosvm -u https://chromium.googlesource.com/chromiumos/manifest.git --repo-url=https://chromium.googlesource.com/external/repo.git
repo sync

cd src/platform/crosvm    #sync下来的是整个ChromeOS project的目录结构，需要进到crosvm目录里面编译
cargo build

mkdir -p /usr/share/policy/crosvm/                #这里面是CrosVM运行时的一些policy配置
cp -r seccomp/x86_64/* /usr/share/policy/crosvm/
```

## 编译虚拟机的内核(Kernel)
```
git clone https://git.kernel.org/pub/scm/linux/kernel/git/stable/linux.git
```
这里是我自己配置的[kernel config](config-builtin-guest-host)
下载并并且改名字为 `.config`
然后编译内核:
```
make olddefconfig
make -j8
```
在内核根目录中生成的vmlinux就是需要的内核文件了(ELF 64-bit LSB executable)。

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
取掉 root: 后面的那个x

```
建议尝试启动VM之前，在rootfs中安装udev 和 systemd, 似乎debootstrap创建的rootfs并没有自带这两个tool，需要自己安装下，否则启动的时候会遇到问题。
```
mount ubuntu19.10_rootfs.img rootfs/
chroot rootfs

apt install udev systemd
exit
umount rootfs
```
注: 如果有同学玩过Qemu，那么可以直接使用Qemu支持的raw或者qcow2格式的虚拟机镜像。

## 创建虚拟机
```
sudo LD_LIBRARY_PATH=~/project/vm/minijail/ ./target/debug/crosvm run \
	--rwroot ubuntu19.10_rootfs.img \
	--seccomp-policy-dir=/usr/share/policy/crosvm/x86_64/ \
	vmlinux
```

或者，CrosVM同样支持带有initrd的内核，如果编译内核有困难或者比较“懒”的同学，可以直接把Ubuntu或者其他Linux发行版的内核拿来用下，启动时可能会有少许问题，但或许可以起来尝鲜一下虚拟机:
```
sudo LD_LIBRARY_PATH=~/project/vm/minijail/ ./target/debug/crosvm run \
	--rwroot ubuntu19.10_rootfs.img \
	--seccomp-policy-dir=/usr/share/policy/crosvm/x86_64/ \
	-i /boot/initrd.img-4.13.0-46-generic \
	/boot/vmlinuz-4.13.0-46-generic
```

运气好的话，在创建VM的终端里面，应该可以看到Kernel启动的log，最后停在登录提示符。输入root 并回车，就可以直接登录虚拟机了。
