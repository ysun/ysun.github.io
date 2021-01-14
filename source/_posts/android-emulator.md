---
title: Ubuntu中玩转Android模拟器
donate: true
date: 2020-05-11 20:08:48
categories: KVM
tags: [android-emulator, kvm] 
---

近来研究了下Android emulator，就是Android Studio中用于调试App的虚拟机AVD(Android Virtualized Device)。本来是件挺平淡无奇的事情，但非要给生活比个""耶....."(＾－＾)V 需求是，在Linux OS中，使用自定义的Android Kernel! 由于烂樱桃本人只略懂一丢虚拟化技术，对于Android算是一窍不通，所以，本文主要记录步骤为主，木有原理性的东西。

## 0. 准备 安装Android Studio
到Android Studio 官网[下载最新Android for Linux 64-bit](https://developer.android.com/studio#downloads) 基本上解压缩之后就能用，如果安装有问题参考[官方安装文档](https://developer.android.com/studio/install)
注：安装过程需要访问Android的一些服务器，下载文件。所以，需要保证上网方式科学有效，还是那句话，不要问如何上网。

## 1. 安装AVD
Android Studio中AVD的安装很方便，第一次创建虚拟机的时候，需要先点击那个'Download'按钮，在线下载虚拟机镜像。
需要注意的两点：
* 需要下载__不__带有'google play'图标的镜像，因为带有Google play log的镜像中有很多限制，比如无法使用adb root等。
* Android Q内含Android Kernel 4.14， Android R是最新版的Android，内含Android Kernel 5.4. 硬盘空间允许的话，Android Q 和 R 都安装了，下面会分别讲述kernel 4.14 和5.4的不同玩法。

直接上图一看便知
![android_studio_avd](android_studio_3.png)

## 2 命令行启动Android模拟器
为了方便启动模拟器，在安装好AVD之后，我们可以退出Android Studio，正常情况后面的步骤都不在需要用到Android Studio了。
Android Studio在安装过程中，会下载Android SDK，默认路径是`~/Android/SDK` 这就是Android的开发包了，其中`~/Android/SDK/emulator`包含了启动模拟器所需要的脚本。
所以，只要进入到emulator的目录内，或者把emulator加到PATH环境变量中，就可以运行模拟器了
```
DISPLAY=:0 ./emulator -avd Pixel_2_v54 -verbose -show-kernel -shell -memory 8192 -no-snapshot-load -gpu guest #-qemu -enable-kvm
```
具体的参数含义参考[官方文档 emulator-commandline](https://developer.android.com/studio/run/emulator-commandline)

## 3. 更换模拟器的Kernel
这是本文的主要目的，在Android Q(Android Kernel 4.14)以及之前的版本的Android，是吧所有的kernel driver全都built-in到一个内核镜像中(bzImage)，但在Android R(Kernel 5.4)开始，为了适应硬件的需求，开始将部分驱动编译成内核模块(kernel module)放在系统镜像中。更详细的故事可以参考[Google outlines plans for mainline Linux kernel support in Android --Google wants less forking, more modularization for Android's Linux kernel](https://arstechnica.com/gadgets/2019/11/google-outlines-plans-for-mainline-linux-kernel-support-in-android/)

### 3.1 Android Q with Kernel 4.14
此时的事情很简单，仅需要简单的几步: 1. 下载内核镜像; 2. 下载编译工具; 3. 编译内核

```
git clone https://android.googlesource.com/kernel/goldfish/ -b android-goldfish-4.14-dev.150
git clone https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/x86/x86_64-linux-android-4.9 -b android10-release

export PATH=$PATH:$PWD/x86_64-linux-android-4.9/bin

cd goldfish
make ARCH=x86_64 x86_64_ranchu_defconfig
make -j16 ARCH=x86_64 CROSS_COMPILE=x86_64-linux-android-
```
注意，两个repo的branch得是搭配的，不可以随意换。
[Building Kernels Manually](https://source.android.com/setup/build/building-kernels-deprecated)这里列出了各种相关的kernel repo。
编译成功之后，这样启动Android模拟器:
```
DISPLAY=:0 ./emulator -avd Pixel_2_v54 -verbose -show-kernel -shell -memory 8192 -no-snapshot-load -gpu guest -kernel /path/to/repo/goldfish/arch/x86/boot/bzImage #-qemu -enable-kvm
```
方法参考: [Run Android Emulator with a Custom Kernel](https://medium.com/@gabrio.tognozzi/run-android-emulator-with-a-custom-kernel-547287ef708c)

### 3.2 Android R with Kernel 5.4
因为需要重新打包system.img，更新其中的kernel module，所以，除了上面两个repo之外，还需要Android完整的源码，并且编译完整的Android image。

#### 3.2.1 编译Kernel 5.4
首先使用跟4.14类似的编译方法。尽管容易理解，但并不推荐，这样还需要手动打包，制作ramdisk.img。
```
git clone https://android.googlesource.com/kernel/goldfish/ -b android-5.4
或者如果已经clone过goldfish kenrel，执行:
cd goldfish && git checkout android-5.4
```

```
git clone https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/x86/x86_64-linux-android-4.9 -b master
或者如果已经clone过x86_64-linux-android-4.9，执行:
cd x86_64-linux-android-4.9 && git checkout master
```

下载clang编译器，并且使用特别版本clang-r377782c来编译Android-R
```
git clone git clone https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86 -b android-r-preview-4
export PATH=$PATH:/path/to/linux-x86/clang-r377782c/bin:/path/to/x86_64-linux-android-4.9/
```
一切准备就绪之后，编译kernel-5.4
```
make O=out ARCH=x86_64 CC=clang CLANG_TRIPLE=x86_64-linux-gnu x86_64_defconfig
make O=out ARCH=x86_64 CC=clang CLANG_TRIPLE=x86_64-linux-gnu- CROSS_COMPILE=x86_64-linux-androidkernel- LD=ld.lld
```

#### 3.2.1' 编译Kernel 5.4
使用repo下载Android Kernel 5.4 以及编译工具(x86_64-linux-android-4.9) 和 编译器Clang
```
mkdir goldfish-kernel-54
cd goldfish-kernel-54/
repo init -u https://android.googlesource.com/kernel/manifest -b common-android-5.4
repo sync
BUILD_CONFIG=goldfish-modules/build.config.goldfish.x86_64 build/build.sh
#grep '=m' ./out/android-5.4/common/.config
#vim ./goldfish-modules/goldfish_defconfig.fragment
```
所有生成的二进制文件(包含bzImage， *.ko)都在 `out/android-5.4/dist/` 里面了。

#### 3.2.2 编译Android镜像
```
apt install libncurses5-dev
apt install libncurses5

mkdir android-src
repo init -u https://android.googlesource.com/platform/manifest -b master
repo sync -j32
source build/envsetup.sh
lunch sdk_phone_x86_64-userdebug
make -j64
```
注: 初始化仓库的时候，这里使用master branch，如果想编译其他分支参考[Android manifest](https://android.googlesource.com/platform/manifest/+refs)
各个branch的含义以及支持情况，可以参考[Codenames, Tags, and Build Numbers](https://source.android.com/setup/start/build-numbers#honeycomb-gpl-modules)
编译Android源码的更详细介绍，可以参考[Building Android](https://source.android.com/setup/build/building)

所有生成的镜像文件都在文件夹`out/target/product/generic_x86/`中
Andriod源码中包含了模拟器，一旦Android镜像编译完成之后，可以直接启动Android虚拟机
```
emulator
```
并且可以基于这个虚拟机，创建一个可以用于Android studio的AVD，详细参见[Using Android Emulator Virtual Devices](https://source.android.com/setup/create/avd)


#### 3.2.3 替换Kernel，重做system.img
```
rm /path/to/android-src/prebuilts/qemu-kernel/x86_64/5.4/ko/*
cp /path/to/goldfish-kernel-54/out/android-5.4/dist/bzImage /path/to/android-src/prebuilts/qemu-kernel/x86_64/5.4/kernel-qemu2
cp /path/to/goldfish-kernel-54/out/android-5.4/dist/*.ko    /path/to/android-src/prebuilts/qemu-kernel/x86_64/5.4/ko

make  # make again after replacing bzImage and modules !!
```
重新make 之后，会生成包含customized过的kernel以及module，这是我们想起来准备工作中下载的Android-R镜像
默认位置这里`~/Android/Sdk/system-images/android-R/google-apis/x86_64/`

替换掉kernel 和 ramdisk.img:

```
cp /path/to/android-src/out/target/product/generic_x86_64/kernel-ranchu-64 ~/Android/Sdk/system-images/android-R/google-apis/x86_64/
cp /path/to/android-src/out/target/product/generic_x86_64/ramdisk-qemu.img ~/Android/Sdk/system-images/android-R/google-apis/x86_64/
```
Android源码库中并不包含内核，android-src/out/target/product/generic_x86/kernel-ranchu-64仅仅是上一步生产的内核改了个名字。
另外，注意generic_x86_64文件夹中同时还有一个文件'ramdisk.img'，不要混淆，我们需要的是`ramdisk-qemu.img`

然后启动Android虚拟机:
```
DISPLAY=:0 ./emulator -avd Pixel_2_v54 -verbose -show-kernel -shell -memory 8192 -no-snapshot-load -gpu guest #-sysdir /path/to/adroid-R/google-apis/x86_64/ #-qemu -enable-kvm
```
`-sysdir` 参数是说，如果不想直接替换Sdk中的源文件，可以copy一下文件夹x86_64，然后替换kernel 和 ramdisk.img，但同时需要指定sysdir的路径

#### 3.2.3' 替换Kernel，重做system.img
```
export ANDROID_PRODUCT_OUT=/path/to/android_src/out/target/product/generic_x86/
export MYPACKEDIMG=~/mypackedimg
mkdir -p $MYPACKEDIMG/img

cd $MYPACKEDIMG/img
cp $ANDROID_PRODUCT_OUT/system-qemu.img system.img
cp $ANDROID_PRODUCT_OUT/vendor-qemu.img vendor.img
cp $ANDROID_PRODUCT_OUT/ramdisk-qemu.img ramdisk.img
cp $ANDROID_PRODUCT_OUT/kernel-ranchu-64 .

cp -rf $ANDROID_PRODUCT_OUT/data .
cp -rf $ANDROID_PRODUCT_OUT/advancedFeatures.ini advancedFeatures.ini
cp -rf $ANDROID_PRODUCT_OUT/userdata.img .
cp -rf $ANDROID_PRODUCT_OUT/encryptionkey.img .
cp -rf $ANDROID_PRODUCT_OUT/system/build.prop .
cp -rf $ANDROID_PRODUCT_OUT/VerifiedBootParams.textproto .
cp -rf $ANDROID_PRODUCT_OUT/source.properties .

cp /path/to/android_src/prebuilts/android-emulator/linux-x86_64/source.properties .
```
启动Android虚拟机:
```
DISPLAY=:0 ./emulator -avd Pixel_2_v54 -verbose -show-kernel -shell -memory 8192 -no-snapshot-load -gpu guest -sysdir $MYPACKEDIMG/img
```
![android_emulator_demo](android_emulator_demo.png)

## 参考链接:
[如何下载Android源码](https://source.android.com/setup/build/downloading)
[Android相关源码仓库目录](https://android.googlesource.com/)
关于Android 源码编译的问题，文章[android-kernel-clang](https://github.com/nathanchance/android-kernel-clang)以及作者[Nathan Chancellor](https://github.com/nathanchance)帮了不少的忙！
[Android Emulator Linux Development](https://android.googlesource.com/platform/external/qemu.git/+/refs/heads/emu-master-dev/android/docs/LINUX-DEV.md)Android 源码中的一个文章，或多或少参考了了一丢丢。

