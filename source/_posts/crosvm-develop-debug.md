---
title: 由浅入深CrosVM（五）—— Crosvm的开发和调试
donate: true
date: 2021-03-24 15:39:28
categories: CROSVM
tags: crosvm ChromeOS
---

前面几篇文章我们完成了Crosvm的编译和安装，以及依赖库的安装。本文将详细阐述一下如何开发和调试crosvm。
我的开发环境是Windows工作机+Ubuntu开发机。当然，可以仅仅用一个Ubuntu做为开发机就可以搞定所有的事情，这种情况最为简单直接。之所以这么做，因为需要使用windows的office，N多年来也习惯了Windows office。出差出门啥的，不需要带两个电脑。
所以，windows中使用的IDE是MS VScode。免费软件，自行下载。

## VSCode 插件
两类插件：Rust编译、调试相关，其他类。
编译调试相关： C/C++, CodeLLDB, Rust/Rust analyzer, Rust Assit, rust-launcher
其他类：Remote-SSH, Terminal, Vim

直接在VSCode里面搜索安装就好了，每个插件都有介绍，都比较常用。

### Remote-SSH
如果再Ubuntu本地开发调试，可以跳过这一步。对于远程调试，之前尝试过几个remote浏览code的方案，最终感觉remote-ssh最符合我的习惯。
安装过Remote-ssh之后，可以如下图配置:
![vscode1](vscode1.png)
```
Host tiaoban
    HostName 10.239.88.88
    Port 22
    User root

Host 192.168.1.66    //需要网关跳转
  HostName 192.168.1.66
  User root
  ProxyCommand ssh tiaoban -W %h:%p

Host 10.239.88.111   //直接ssh
  HostName 10.239.88.111
  User root
  ForwardAgent yes
```
而我又偏偏需要网关跳转一次。配置文件写好后，就可以看到如图所示"SSH TARGETS"里面有对应的机器出现。鼠标右键点击开发机，选择"Connect Host in New Window"，或者host name后面的图标，就弹出一个新的VSCode窗口，分别输入网关和开发机的密码，就可以连上去。然后就像在本地一样，在最上边地址栏里输入项目文件夹的地址就好了。

### rust-launcher
用来运行rust编译和调试程序的插件，运行时要求依赖 C/C++ 和 CodeLLDB，以及Rust（编译器）。rust-launcher的配置文件很关键，我列在这里供参考：
```
{
    "version": "0.2.0",
    "configurations": [
        {
            "type": "lldb",
            "request": "launch",
            "name": "Debug executable 'qcow_img'",
            "cargo": {
                "args": [
                    "build",
                    "--features=gpu,x"
                ],
            },
            "args": [
                "run", 
                "--disable-sandbox",
                "--cpus=4",
                "--mem=4096",
                "--rwdisk=/home/works/kvm/ubuntu20.10_rootfs.img",
                "--params=root=/dev/vda3",
                "--socket=/tmp/crosvm.sock",
                "--host_ip=192.168.0.1",
                "--netmask=255.255.255.0",
                "--mac=AA:BB:CC:00:00:12",
                "--gpu",
                "--x-display=:0",
                "--display-window-keyboard",
                "--display-window-mouse",
                "/home/works/crosvm_kvm/vmlinuz-5.11.0-intel-next-adl-alpha-rc1",
            ],
            "cwd": "${workspaceFolder}"
        },
    ]
}
```
下面是部分参数的说明:
```
// lldb的launch.json配置内容
"version": "0.2.0",
    "configurations": [
        {
            "name": "rust", // 配置名称，将会在调试配置下拉列表中显示
            "type": "lldb", // 调试器类型：Windows表示器使用cppvsdbg；GDB和LLDB使用cppdbg。该值自动生成
            "request": "launch", // 调试方式
            "program": "${workspaceRoot}/target/debug/helloworld", // 要调试的程序（完整路径，支持相对路径）
            "args": [], // 传递给上面程序的参数，没有参数留空即可
            "stopAtEntry": false, // 是否停在程序入口点（即停在main函数开始）（目前为不停下）
            "cwd": "${workspaceRoot}", // 调试程序时的工作目录
            "environment": [],
            "externalConsole": false, // 调试时是否显示控制台窗口(目前为不显示)
            //"preLaunchTask": "build", //预先执行task.json
            "MIMode": "lldb" //MAC下的debug程序
        }
    ]
```
两个注意地方：
1. key "cargo"是rust的编译语句，我这里加入了gpu和x的参数。这里等效Linux command:
`cargo build --features=gpu,x`
2. key "args"是运行时的参数，这里是我常用的启动crosvm虚拟机的参数供大家参考。这里好说的是，参数后面如果有值的话，必须用等号"="，不可以使用空格，否则rust-launcher会报错的。

launcher的配置文件写完之后，再修改最后一个地方，如图所示，在VSCode的左下角点击setting那个小齿轮，然后搜索break，勾选"Allow setting breakpoints in any files"。不知道为何这个选项没有默认勾选，但勾选之后，就可以在source code中使用F9设断点了
![vscode2](vscode2.png)

最后的效果如下图所示：
![vscode3](vscode3.png)

## 补充三个VSCode调试技巧
### 多进程
VSCode可以很优雅的显示多线程，并且可以针对每一个线程分别单步调试。但对于进程(fork()) 默认只能跟踪父进程。如果想在fork()函数之后，debug子进程中的内容，这么做：
在程序创建多进程之前(fork)之前，设置断点，然后在执行到这个断点的时候，在debug console里输入
```
-exec -gdb-set follow-fork-mode child
```
这样继续执行的时候，VSCode就会跟踪子进程了。

### 函数的返回值
进入一个函数，然后执行`-exec finish`这样就可以看到这个执行后的返回值了。

### 查看内存地址上的值
```
-exec x / 4ub 0x555556e9ba10
或者
-exec x4xb
```
