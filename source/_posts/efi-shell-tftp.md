---
title: EFI Shell中使用tfpt.efi 自动化Kernel测试方案
donate: true
date: 2019-05-07 09:44:48
categories: efi
tags: efi
---
## 引言
对于Linux Kernel 或者OS相关的自动化测试，如何自动更新被测的Kernel以及OS image有时候是比较困难的事情。
Linux社区的"老神仙"Fengguang同学牵头开发了0-day自动化测试系统，系统期初的核心功能是利用kexec加载待测的kernel image二次启动。大概流程是:

``` flow
st=>start: 系统启动
op1=>operation: 启动small size的kernel + ramfs
op2=>operation: 初始化网络并获取IP地址
op3=>operation: 从服务器上获取可用的kernel image列表
op4=>operation: 根据列表的配置获取待测的kernel image
op5=>operation: 在ramfs初始化的最后阶段使用Kexec加载待测的kernel image启动本地文件系统
e=>end: 系统启动结束

st->op1->op2->op3->op4->op5->e

```

这个方法对于绝大多数kernel或者module测试中是工作的，也是非常灵活的。但有几个特例：
1. 由于Kexec的限制，上述方法对Xen支持的不好。
2. 对于被测对象是hypervisor的情况，因为没有host OS的支持，无法加载ramfs

这里大概验证了一个补充的方法，可以覆盖对于hypervisor等运行在Linux Kernel下层的组建进行自动化测试。

## EFI 以及EDKII
我不是EFI或者EDKII的专家，这里就简单描述使用方法。另外之所以需要编译EDKII，是因为一般平台自带的EFI shell网络支持都不是很好。

### 下载EDKII source code：
```
git clone https://github.com/tianocore/edk2.git
cd edk2
git submodule update --init --recursive

```

### 编译edk2的编译工具
```
. edksetup.sh BaseTools
cd BaseTools/
make

```
### 编译EFI Shell包
```
build -p ShellPkg/ShellPkg.dsc  -t GCC5 -a IA32 -a X64
```

然后就可以在目录`Build/Shell/RELEASE_GCC5/X64/` 中找到`shell.efi`和`tftp.efi`。可以将这两个文件copy到efi分区中，就可以使用了。

### 加载shell.efi
`shell.efi`也只是个EFI 的application，可以使用Linux下的工具`efibootmgr`让BIOS自动加载
```
efibootmgr -c -l "\EFI\shell.efi" -d /dev/nvme0n1 -p 1  -L "MY EFI SHELL" 
```
大概意思是创建(`-c`)一个entry，加载(`-l`)EFI文件`\EFI\shell.efi`，磁盘(`-d`)`/dev/nvme0n1`的第1个分区(`-p 1`)，标签命名为(`-L "MY EFI SHELL"`)

另外还有两个常用命令：
```
efibootmgr -v
efibootmgr -o 0001,0002,0005,0003,0004,0000
```
`-v` 列出当前的启动顺序，一般新加入的都是第一个启动
`-o` 后面列出来重新排列的启动顺序，需要需要从上一条命令中查到。

### 确认网络工作
执行命令
```
ifconfig -l
```
可以列出来所有的网络接口。默认会自动dhcp，如果没有可以使用
```
ifconfig -i etho dhcp
```
来手动获取IP地址。

tips: 如果在BIOS里面设置关闭PXE网络启动的话，网络驱动就不会加载了，所以，建议在BIOS里面enable PXE boot，尽管我们并不使用它。

## TFTP
接下来简单说下TFTP的使用方法

### 搭建TFTP server
以Ubuntu为例：
```
安装：
apt-get install tftp-hpa tftpd-hpa

创建目录：
mkdir /tftpboot # 这是建立tftp传输目录。
sudo chmod 0777 /tftpboot
sudo touch test.txt # test.txt文件最好输入内容以便区分

配置：
vim /etc/default/tftpd-hpa3
TFTP_USERNAME="tftp"
TFTP_DIRECTORY="/tftpboot" # 这里是你的tftpd-hpa的服务目录,这个想建立在哪里都行
TFTP_ADDRESS="0.0.0.0:69"
TFTP_OPTIONS="-l -c -s" # 这里是选项,-c是可以上传文件的参数，-s是指定tftpd-hpa服务目录，上面已经指定

重启服务
sudo service tftpd-hpa restart # 启动服务，这里要注意，采用的独立服务形式。

测试
$ tftp 127.0.0.1
tftp>get test.txt
tftp>put test1.txt
```

### EFI Shell 中使用tftp.efi

在EFI shell中进入tftp.efi所在目录然后执行
```
tftp.efi <tftp server IP> <文件名字>
```
就可以下载文件了。

## 自动化kernel 测试方案：
在EFI Shell的根目录中，比如fs0: 中添加一个文件 startup.nsh 内容如下：
```
if not exist fs0:\EFI\tftp.efi then
        echo "No tftp.efi"
endif

fs0:
cd \EFI

tftp.efi 10.239.159.139 kernel_images/bzImage_current bzImage


:boot_os
        cd \EFI\ubuntu
        grubx64.efi 
```

这样Ubuntu grub加载的时候，就可以使用刚刚下载来的kernel了，因为grub和efi都可以使用FAT分区格式。

当系统死掉了，并且需要更新kernel的时候，只需要覆盖tftp server上的bzimage_current或者改变其软连接的指向，然后重启系统，就可以一次性更新kernel。

## Todo
目前EFI shell能做的事情相比Linux shell还相差甚远，没有太多现成的application可以直接使用。
tftp.efi也能是download，并不能upload，这使得EFI直接并不能对server进行通知，需要借助OS。
后面，可以增加application，实现类似Linux工具curl，或者patch tfpt让它可以上传文件，这样就可以双向通信了。

