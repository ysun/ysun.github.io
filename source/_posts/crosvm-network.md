---
title: 由浅入深CrosVM（三）—— 虚拟机的网络配置
donate: true
date: 2020-04-07 11:28:32
categories: ChromeOS
tags: ChromeOS CrosVM
---

所有虚拟机都面临的问题——网络访问。关于虚拟机的网络模型在前文 [QEMU虚拟机网络模拟](https://www.owalle.com/2019/12/26/network-in-vm/)已经有过详细的描述。基于上篇文章，这里简要说明下如何在CrosVM的虚拟机中使用网络。

## NAT模式
网络拓扑结构参照[QEMU虚拟机网络模拟]([https://www.owalle.com/2019/12/26/network-in-vm/)
配置很简单，在启动虚拟机的时候，增加三个参数`--host_ip --netmask --mac`:
```
./crosvm run --disable-sandbox \
	--cpus 4 --mem 4096 \
	--rwdisk=ubuntu-rootfs.img \
	--params=root=/dev/vda \
	--gpu --x-display :0 \
	--socket=crosvm.sock \
	--evdev /dev/input/event18 --evdev /dev/input/event19 \
	--host_ip 192.168.0.1 --netmask 255.255.255.0 --mac AA:BB:CC:00:00:12 \
	vmlinux-5.4.18
```
这样crosvm会在host中创建一个虚拟网卡，IP地址，子网掩码以及Mac地址都是参数给定的样子:
```
vmtap0: flags=67<UP,BROADCAST,RUNNING>  mtu 1500
        inet 192.168.0.1  netmask 255.255.255.0  broadcast 192.168.0.255
        inet6 fe80::a8bb:ccff:fe00:12  prefixlen 64  scopeid 0x20<link>
        ether aa:bb:cc:00:00:12  txqueuelen 1000  (Ethernet)
        RX packets 0  bytes 0 (0.0 B)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 0  bytes 0 (0.0 B)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
```
然后登录虚拟机之后，给虚拟机中的网卡配置同网段的IP之后，就可以相互访问了:
```
ifconfig eth0 192.168.0.22 netmask 255.255.255.0
```

## Bridge模式
这方法跟"QEMU虚拟机网络模拟"中描述的Bridge思路一致，甚至方法都一样:
首先在host中创建一个bridge:

```
ip link add br0 type bridge
ip link set eth0 master br0
ip link set dev br0 up 
dhclient br0 
```
然后启动VM的时候，同样加上上述三个参数`--host_ip --netmask --mac`用于创建vmtap0和虚拟机中的virtio network设备。

当虚拟机启动起来之后，需要在Host中，把vmtap0绑定到br0上
```
ip link set vmtap0 master br0
ip link set vmtap0 up
```

最后，回到虚拟机中动态获得IP
```
dhclient
```
虚拟机就可以获得跟Host同一网段的IP地址了。

