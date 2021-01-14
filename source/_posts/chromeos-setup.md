---
title: 新安装ChromeOS之后需要做的事情
donate: true
date: 2020-03-03 12:52:34
categories: OS
tags: ChromeOS
---

最近“被迫”研究ChromeOS——这个东东在国内往实在是太痛苦了！！不管怎么样，把最近玩ChromeOS的过程记个流水账。防止自己遗忘，也给国内同样想玩ChromeOS的玩家提供点参考——国内可以搜到的东西实在是太少了。
下面所有的步骤，都默认读者是可以无障碍访问互联网的，对于GFW这件事情，这篇文章基本上帮不上忙，因为我自己没有找到一个完美解决的办法。

## 安装ChromeOS
### 从源码使用cros_sdk编译
这个不多说了，再华丽的描述都不及Google的[官方文档](https://chromium.googlesource.com/chromiumos/docs/+/master/developer_guide.md)非常的详细。

### Google partner账户
另外，如果不想自己编译，可以选择下载Google的[FE built](https://www.google.com/chromeos/partner/fe/#release)

## 登录
登录时须要有网络，或许是因为ChromeOS的bug，在登录时的网络窗口是无法设置代理的。还是那么那句话，没有办法解决网络的问题。

## 配置开始
上面都是准备工作，这里我们正式开始配置ChromeBook了。

### 安装Linux Beta
点“开始”(或许ChromeOS里左下角那个按钮不叫“开始”)，输入Linux 或者 Terminal 出现一个终端的图标，点它。
这是ChromeOS会联网下载Guest的镜像或者是镜像里的容器。

大概过10分钟，就会弹出来一个类似Linux下terminal的窗口，可以输入命令了 ———— 这就是Linux 虚拟机，基于CrosVM的虚拟机。

### 安装Chromebrew
使用CTRL+ALT+F2 切换到终端；或者打开浏览器 CTRL+ALT+T 输入shell 都可以通过终端操作ChromeOS。但此时你会惊讶的发现，其实啥装不了。官方的安装需要通过cros_sdk 来编译(emerge)和部署(deploy)，但这样不够灵活，也非常的慢。
强烈推荐[Chromebrew](http://skycocker.github.io/chromebrew/) [git](https://github.com/skycocker/chromebrew.git)

安装方法也很简单，切换到chronos用户，然后输入
```
wget -q -O - https://raw.github.com/skycocker/chromebrew/master/install.sh | bash

-- or --

curl -Ls git.io/vddgY | bash

-- or --

curl -Ls https://raw.github.com/skycocker/chromebrew/master/install.sh | bash
```
然后等就好了。
然后需要安装软件大概有：
```
crew install vim
crew install git 
```

### 安装Crouton
[Crouton](https://github.com/dnschneid/crouton.git)是Chrome下的一个choot，可以让用户在ChromeOS里安装Linux Distribution的文件系统，比如Ubuntu Debain 等，对于想在ChromeOS的Host环境里做点hack事情的玩家，还是很方便的！
```
git clone https://github.com/dnschneid/crouton.git
./installer/crouton    # 查看help
./installer/crouton -r help  #列出所有的可以用的'release'
./installer/crouton -t help  #列出所有的可以用的'target'
```

通常我这样安装:
注意，需要在桌面环境的shell里面运行，而不是CTRL+ALT+F2的VT！！
```
./installer/crouton -r buster -t xfce

```
然后就是等就好了 :) 中间会让输入一个常用用户名和密码，结束之后这样用：
```
enter-chroot    #进入chroot环境
startxfce4      #启动桌面

```
好了现在就看像使用Debian一样，使用Chromebook了。
如果想要退出chroot的环境，使用快捷键 CTRL+ALT+SHIFT+F1，回到native的桌面
插一句，[crouton github](https://github.com/dnschneid/crouton) 上的wiki以及问答已经是有挺多内容参考和借鉴了。

### 读写分区
```
sudo su -
cd /usr/share/vboot/bin/
./make_dev_ssd.sh --remove_rootfs_verification --partitions 4
reboot
```
默认的ChromeOS的分区是只读的，这样给他重新挂载
```
mount -o remount,rw /
mount -o remount,exec /mnt/stateful_partition/
```

### 清空iptable规则
```
iptables -F
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD ACCEPT
```

### 安装pip3
`crew install python3-pip 或者 python2-pip`

### 安装paramiko -- python的一个包
`pip3 install paramiko`

### Chroot中 安装apitrace
```
git clone https://github.com/apitrace/apitrace.git
sudo apt install libx11-dev automake gcc cmake
cmake .
make && make install
```

### 解锁module_locking
默认情况下，ChromeOS是不允许插入`/lib/modules/<kernel version>`之外的内核模块的，看可以通过传一个kernel option来解锁。有个网友现成的脚本：
方式链接失效，[可以从这里下载](change-kernel-flags)
参考链接[这里](https://github.com/divx118/crouton-packages/blob/master/README.md)

```
$ wget https://raw.githubusercontent.com/divx118/crouton-packages/master/change-kernel-flags
$ sudo sh ./change-kernel-flags

```

## 总结
至此，基本上，一个ChromeBook已经可以用起来了。如果谁还有那些新奇好玩的用法，欢迎留言

## 安装其他benchmark
### glmark2
source code: https://github.com/glmark2/glmark2.git

Chroot 中编译：
```
sudo apt install libx11-dev libjpeg-dev libpng*

./waf configure --with-flavors x11-gl
sudo ./waf install
```

VM 中编译：
```
apt install libjpeg-dev pkg-config libpng* libdrm-dev libgbm-dev libwayland-client0 libudev-dev libx11-dev

./waf configure --with-flavors x11-gl
sudo ./waf install
```

## 安装Steam
目前基于Linux的游戏平台，可以说就只有Steam了。安装Steam的坑在于，Steam自己为了支持多数游戏运行，平台客户端软件只支持32bit。安装步骤：
### 安装32bit支持
```
sudo dpkg --add-architecture i386
sudo apt-get update
sudo apt-get dist-upgrade
sudo apt-get install libc-i386
```

### 下载Steam 安装包
官方下载地址: https://store.steampowered.com/about/
dpkg -i setup.deb
