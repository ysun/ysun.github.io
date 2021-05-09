---
title: 创建mini虚拟机镜像
donate: true
date: 2021-01-09 07:48:48
categories: OS
tags: 最小系统 QEMU KVM
---

很多同学可能想要着手学习Linux kernel、虚拟机，或者刚入门不久。今天写一个入门用的很有用的教程，教大家如何创建最小化的虚拟机镜像。

## 创建镜像文件 ##

创建一个名为rootfs-debootstrap.img 大小为20G的空文件
`dd if=/dev/zero of=rootfs-debootstrap.img bs=1M count=20480`

## 下载Ubuntu 20.04 文件系统 ##

安装debootstrap工具
apt-get install -y debootstrap arch-install-scripts

创建分区
`gdisk /dev/sda`

在gdisk命令行中，一次执行：
```
创建EFI分区, 1G:
按 n,1, [Enter]，[Enter], +1024M [Enter], ef00 [Enter]

创建swap分区，2G:
按 n, 2 [Enter], [Enter], +2G [Enter], 8200 [Enter]

创建根分区:
按 n, 3 [Enter], [Enter], [Enter], [Enter]

写入分区表:
Press w, Y [Enter]
```

创建Loop 设备

```
losetup -f                                                                               
# 返回一个空闲的loop设备，比如这里是/dev/loop12

```

```
losetup -P /dev/loop12 /home/works/kvm/ubuntu20.04_rootfs.img
```
为镜像中的分区创建对应的分区loop device
参数`-P`很重要,是直接创建带有分区信息的Loop设备。如果顺利，可以到创建了三个loop设备文件例如：
```
/dev/loop1p1
/dev/loop1p2
/dev/loop1p3
```

然后就可以格式化分区了

```
mkfs.vfat /dev/loop12p1                                                                  
mkswap /dev/loop12p2 && swapon /dev/loop12p2                                             
mkfs.ext4 /dev/loop12p3                                                                  
# 分别格式化三个不同的分区
```

挂载根分区以及EFI分区,按习惯把efi分区挂载到/boot/下面
```
mount /dev/loop12p3 /mnt/                                                                
mkdir -p /mnt/boot/efi && mount /dev/loop12p1 /mnt/boot/efi                              
ll /mnt/boot/efi/                                                                        
```

下载文件系统Ubuntu 20.04 (focal)
```
debootstrap --arch amd64 focal /mnt http://archive.ubuntu.com/ubuntu
```
视网络情况，我大概用了30分钟，因为科学上网可能比较慢，大概只下载了几十兆的东西

debootstrap 下载的文件系统是没有源的，给手动添加源
```
release="focal"

printf "deb http://archive.ubuntu.com/ubuntu/ ${release} main restricted universe\ndeb http://security.ubuntu.com/ubuntu/ ${release}-security main restricted universe\ndeb http://archive.ubuntu.com/ubuntu/ ${release}-updates main restricted universe\n" > /mnt/etc/apt/sources.list
```

同样，创建fstab
```
genfstab -U /mnt >> /mnt/etc/fstab

```

进入刚创建的文件系统里面
```
arch-chroot /mnt
```

安装必要的包
```

apt-get update

apt-get install -y --no-install-recommends linux-generic linux-image-generic linux-headers-generic initramfs-tools linux-firmware efibootmgr

```

设置时区
```
dpkg-reconfigure tzdata
```
我选择了`en_US.UTF-8`

选择语言
```
dpkg-reconfigure locales
```

如果有必要，设置hostname
```
vi /etc/hosts
```

很重要的一件事情，为root设置密码
```
passwd root
```

安装grub2
```
apt install grub-efi-amd64
grub-install
```
到此为止，基本上已经完成了所有的创建最小虚拟机镜像的步骤。后面就可以退出chroot了。

尝试一下虚拟机镜像:

```
qemu-system-x86_64 -m 2048 -smp 8 --enable-kvm -cpu host -bios OVMF.fd -boot order=c,menu=off -hda rootfs-debootstrap.img
```

OVMF.fd是EDKII编译出来的虚拟BIOS，预编译的二进制文件在早前的博文里面有的，有需要的读者可以搜寻一下。
如果安装按装grub2，找不到configure文件，可以修改一下grub的这个配置文件:

```
/boot/efi/EFI/ubuntu/grub.cfg

search.fs_uuid xkjdiw-18e9-4d0a-ac55-2skjdh8425f root hd1,gpt5 
set prefix=($root)'/grub'
configfile $prefix/grub.cfg

```
直接修改configfile，使其直接指向你的grub.cfg, 比如 (hd1,gpt3)/boot/grub.cfg 即可。

最后，安全退出
```
umount /mnt/boot/efi
umount /mnt/
losetup -d /dev/loop12
kpartx -dv /dev/loop12
```
