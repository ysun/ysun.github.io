---
title: 由浅入深CrosVM（二）—— 如何在虚拟机中使用3D加速(借助Virgil 3D项目)
donate: true
date: 2020-04-03 20:08:26
categories: CROSVM
tags: ChromeOS crosvm
---

## 什么是Virgil 3d项目
Virgil是Dave Airlie(from Red Hat)的一个研究项目。该项目在虚拟机中创建一个虚拟GPU，通过它允许虚拟机操作系统(Guest OS)使用物理机(宿主机，Host)的物理GPU来加速3D渲染。让用户感觉拥有一个完全独立于主机的虚拟机GPU。

该虚拟显卡的设计基于Gallium3D，使用Gallium TGSI中间件作为着色器。虚拟显卡的渲染实现是在主机系统中作为qemu、crosvm等VMM(virtual machine manager)的一部分完成的。目前支持OpenGL(4.3)和OpenGL ES (3.2)，并且需要SDL支持。可以在任何支持的显卡/驱动程序上加速渲染。

该项目还包含一个完整的Linux虚拟机技术栈，包括Linux内核KMS驱动程序(DRM/i915)，X.org(2D DDX驱动程序)和Mesa(3D驱动程序)组成。

现在，所有组件都已经集成到了各个项目中:
* Linux 内核4.4开始，包含3D支持的部分。
* Mesa master分支包含virgl 3D驱动程序。
* QEMU 2.5开始包含virtio-gpu，以及支持GL的GTK3前端。
* virglrenderer库已经可以提供QEMU或者CrosVM所需要的API。

未来的功能以及缺点：
* 通过编解码实现远程渲染(rendering)暂不支持。
* Windows Guest以及Direct 3D暂不支持。
* 不支持Passing through GPU给guest。

![virgl_stack.png](virgl_stack.png)
参考: [Virgil 3D GPU project](https://virgil3d.github.io/)

## 开始搭建环境
有了上面的virgl技术栈的图，事情变得清晰多了：在Host端安装virglrenderer，安装最新的Mesa、和Linux Kernel。

### 编译安装virglrenderer
```
apt install python3-pip
pip3 install meson

# 安装依赖
apt install libgbm-dev mesa-utils llvm llvm-9-dev libpciaccess-dev libwayland-egl-backend-dev ninja-build libx11-dev libegl1-mesa-dev libdrm-dev cmake

git clone https://github.com/anholt/libepoxy.git
cd libepoxy
mkdir build && cd build && meson .. && meson install && cd ..

git clone https://gitlab.freedesktop.org/virgl/virglrenderer.git
cd virglrenderer
mkdir build && cd build && meson .. && meson install && cd ..

git clone https://gitlab.freedesktop.org/mesa/drm.git
cd drm
mkdir build && meson build/ && ninja -C build install

```

### 确认Mesa 支持
```
# glxinfo |grep renderer
```

如果renderer string使用 llvmpipe，说明Mesa不支持:
```
OpenGL renderer string: llvmpipe (LLVM 5.0, 256 bits)
```

如果renderer string使用 Intel，说明3D驱动安装正确:
```
OpenGL renderer string: Mesa DRI Intel(R) HD Graphics 620 (Kaby Lake GT2)

```

如果当前Mesa不支持的话，请参考Mesa的官网，[编译安装Mesa](https://www.mesa3d.org/install.html)
跟上面一样，这里还是简述一下吧。
```
apt install libelf-dev libbison-dev flex libxrandr-dev valgrind libunwind-dev wayland-scanner++ libwayland-bin libwayland-dev libxdamage-dev libxcb-glx0-dev libx11-xcb-dev libxcb-dri2-0-dev libxcb-dri3-dev libxcb-present-dev libxshmfence-dev libxxf86vm-dev 

git clone https://gitlab.freedesktop.org/mesa/mesa.git

cd mesa
meson builddir/
ninja -C builddir/
ninja -C builddir/ install
```

## 重新编译安装CrosVM
加上参数`--features=gpu,x`
```
cargo build --features=gpu,x #BTW, 如果需要图形加速，需要打开gpu和x

mkdir -p /usr/share/policy/crosvm/                #这里面是CrosVM运行时的一些policy配置
cp -r src/platform/crosvm/seccomp/x86_64/* /usr/share/policy/crosvm/
```

## 创建虚拟机
### Host
启动X(xinit)，或者桌面环境。加上参数`-gpu --x-display :0`
```
crosvm run --disable-sandbox \
	--cpus 4 --mem 4096 \
	--rwdisk=ubuntu-rootfs.img \
	--params=root=/dev/vda \
	--gpu --x-display :0 \
	--socket=crosvm.sock \
	--evdev /dev/input/event18 --evdev /dev/input/event19 \
	vmlinux-5.4.18
```
参数说明:
* --disable-sandbox: 如果上一篇文章里面的minijail已经正确安装，可以省略这个参数，大概是为了安全性，不详述了吧，因为——不懂~！
* --cpus 4 --mem 4096: vCPU数目和虚拟内存大小4096M
* --rwdisk=ubuntu-rootfs.img: 虚拟机镜像。可以使用上一篇文章中的方法，使用debootstrap生成一个rootfs镜像；CrosVM同样支持带有分区信息虚拟机镜像，可以直接使用QEMU虚拟机的Raw或者Qcow2类型的镜像，没有压力。
* --gpu --x-display :0 : 开起GPU以及X显示支持，这个参数是全篇的"精髓"，上面安装一大堆的库，就为了这两个参数。
* --socket=crosvm.sock : socket用于控制CrosVM以及通信。
* --evdev /dev/input/event18 : Passthrough 鼠标和键盘给虚拟机，需要额接一套键鼠。不过后面想尽量可以专门讲一期外设吧，尽量……。
* vmlinux-5.4.18 : 虚拟机内核，ELF 64-bit LSB executable格式的，就是编译完kernel之后，在源码根目录生成的那个静态链接的内核文件(statically linked)。注: 为了方便，建议将所有用到的内核模块(module)都配置成built-in (y)而不是m。否则，需要一个initramfs，通过(-i)参数传递给crosvm，而且initrd的大小有限制，比较麻烦。

### Guest
启动X(xinit)，执行3D程序。同样可以使用glxinfo来确认3D驱动是否安装正确
```
# glxinfo |grep renderer

OpenGL renderer string: virgl
```
如果renderer string是virgl，说明guest里的3D环境已经ready了。
Have Fun!
