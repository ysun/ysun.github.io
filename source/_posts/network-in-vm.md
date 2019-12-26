---
title: QEMU虚拟机上网的三种方式
donate: true
date: 2019-12-26 13:44:43
categories: QEMU KVM
tags: qemu kvm network
---

当我们打算建一个或者多个虚拟机时，通常都伴随着虚拟机的联网问题。这里我们总结一下虚拟机上网的三种方法：NAT方式、Bridge方式和passthrough网卡。

## NAT方式
如图所示，NAT方式与家里上网的方式有点类似，虚拟机在一个子网内(192.168.122.255)，宿主机看做双网卡(虚拟了一个网卡)。此时虚拟机可以访问Internet，但Internet默认是无法访问虚拟机的。
![](network-nat.png)

### NAT配置方法
1. 确保已安装libvirt-clients和libvirt-daemon
```
Ubuntu:
apt-get install libvirt-clients		//使用virsh
apt-get install libvirt-daemon		//使用libvirtd
apt-get install qemu-system-common	//使用qemu-bridge-helper
```

  确保libvirt-daemon服务开启
```
systemctl start libvirtd
systemctl enable libvirtd
```

  如果libvirtd启动成功的话会出现一个虚拟桥virbr0和virbr0-nic：
```
#ip a

1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN group default qlen 1000
    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00
    inet 127.0.0.1/8 scope host lo
       valid_lft forever preferred_lft forever
    inet6 ::1/128 scope host
       valid_lft forever preferred_lft forever
2: eno1: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc fq_codel state UP group default qlen 1000
    link/ether d4:5d:df:07:c1:07 brd ff:ff:ff:ff:ff:ff
    inet 10.239.48.54/24 brd 10.239.48.255 scope global dynamic noprefixroute eno1
       valid_lft 12387sec preferred_lft 12387sec
    inet6 fe80::d65d:dfff:fe07:c107/64 scope link
       valid_lft forever preferred_lft forever
3: virbr0: <NO-CARRIER,BROADCAST,MULTICAST,UP> mtu 1500 qdisc noqueue state DOWN group default qlen 1000
    link/ether 52:54:00:d3:6d:2d brd ff:ff:ff:ff:ff:ff
    inet 192.168.122.1/24 brd 192.168.122.255 scope global virbr0
       valid_lft forever preferred_lft forever
4: virbr0-nic: <BROADCAST,MULTICAST> mtu 1500 qdisc fq_codel master virbr0 state DOWN group default qlen 1000
    link/ether 52:54:00:d3:6d:2d brd ff:ff:ff:ff:ff:ff
```

2. 使用virsh配置网络
在没有进行任何网络配置之前，应该是这样的：
```
#virsh net-list --all

 Name                 State      Autostart     Persistent
----------------------------------------------------------
```

  一个比较偷懒的办法是使用现成的配置文件default.xml，内容如下:
```
<network>
  <name>default</name>
  <uuid>417b7ead-6342-40a4-b29f-02fa2d4df491</uuid>
  <forward mode='nat'/>
  <bridge name='virbr0' stp='on' delay='0'/>
  <mac address='52:54:00:d3:6d:2d'/>
  <ip address='192.168.122.1' netmask='255.255.255.0'>
    <dhcp>
      <range start='192.168.122.2' end='192.168.122.254'/>
    </dhcp>
  </ip>
</network>
```
  ```
#virsh net-define default.xml
#virsh net-start default
#virsh net-list --all

 Name                 State      Autostart     Persistent
----------------------------------------------------------
 default              active     yes           yes

```
  如果看到看到上面的结果，那么“虚拟桥”（virt bridge）就配置成功了。
实际上NAT方式的时候，各个网卡之间的关系如图所示:
![](network-nat2.png)

3. QEMU创建虚拟机
```
qemu-system-x86_64 --enable-kvm -M q35 -m 4G -smp 1 -hda /root/ubuntu1904.qcow -vnc :7 \
	-device virtio-net-pci,netdev=nic0,mac=00:16:3e:0c:12:78 \
	-netdev tap,id=nic0,br=br0,helper=/usr/local/libexec/qemu-bridge-helper,vhost=on
```
  因为使用了工具qemu-bridge-helper，它需要一个配置文件：
```
/usr/local/etc/qemu/bridge.conf:

#把我们有可能用得到的网桥名字都列在这里。

allow br0
allow br1
allow virbr0
```
  顺利的话，虚拟机起来之后会DHCP得到一个IP例如`192.168.122.177`。

## Bridge方式
如图所示，bridge方式是让虚拟机获得跟host一样网段的IP地址，就像是host的一个“网上邻居”一样。
![](network-bridge.png)

### Bridge方式的配置方法1
首先使用'ip'工具来配置，注意这种方法是临时的，一旦重启系统，这些配置需要重新做。

1. 创建一个“网桥”(bridge),取名br0
```
ip link add name br0 type bridge
ip link set br0 up
```

2. 把物理网卡绑定到网桥上：
```
ip link set dev enp3s0f1 master br0	//enp3s0f1 是网卡interface的名字
```
  这步之后，可以通过`ip a`查看，br0 和 enp3s0f1具有相同的mac地址。

3. 重启网络服务：
```
systemctl restart NetworkManager
```
  正常情况下，网络重启之后，br0会拿到IP，而之前的enp3s0f1不会拿到IP了。如果不是，执行下面命令:
```
ifdown enp3s0f1
ifdown br0
ifup br0
ifup enp3s0f1
systemctl restart NetworkManager
```
4. QEMU创建虚拟机
```
qemu-system-x86_64 --enable-kvm -M q35 -m 4G -smp 1 -hda /root/ubuntu1904.qcow -vnc :7 \
	-device virtio-net-pci,netdev=nic0,mac=00:16:3e:0c:12:78 \
	-netdev tap,id=nic0,br=br0,helper=/usr/local/libexec/qemu-bridge-helper,vhost=on
```
  吼吼，创建虚拟机的步骤与NAT时，没有区别，除了注意一下网桥的名字之外。

5. (选做)如果想要删掉“网桥”执行下面的步骤：
```
ip link set dev enp3s0f1 nomaster
ip link set dev br0 down
ip link del br0
```
### Bridge方式的配置方法2
这里借用工具nmcli来配置，参考了[USING THE NETWORKMANAGER COMMAND LINE TOOL, NMCLI](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/7/html/networking_guide/sec-network_bridging_using_the_networkmanager_command_line_tool_nmcli)

1. 简单来说执行下面的命令：
```
#nmcli con add type bridge ifname br0
#nmcli con add type ethernet ifname enp3s0f1 master bridge-br0
#nmcli connection down enp3s0f1
#nmcli connection up bridge-br0

#systemctl restart NetworkManager
```
  这样应该就创建好网桥br1了

2. QEMU创建虚拟机的步骤还是跟之前的一样。
这个方法的有点就是系统重启之后，配置还在。

### pass-through物理网卡
这种方法的网络拓扑结构跟bridge方式是一样的，不过这次虚拟机成为货真价实的网上邻居，因为它使用的是物理网卡。如果host上恰好有一个多余的网卡，不放试下这个方法。
pass-through物理网卡虽然实现起来相对复杂，但用起来确比较容易：

1. 确保host没有加载对应网卡的驱动
  不过通常这都太可能，可以参考[这个脚本](vfio-pci.sh)
```
# ./vfio-pci.sh -h <B:D:F>
```

2. QEMU创建虚拟机
```
qemu-system-x86_64 --enable-kvm -M q35 -m 4G -smp 1 -hda /root/ubuntu1904.qcow -vnc :7 \
	-device vfio-pci,host=81:00.0,romfile= 
```
  相比几种方法，去掉了复杂的网络参数，仅仅加上了一个设备，并且指定其B:D:F是需要被pass-through给虚拟机的网卡对应的B:D:F的即可(例子中为81:00.0)。

