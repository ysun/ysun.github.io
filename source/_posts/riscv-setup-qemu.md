---
title: 玩转RISC-V系列1 在QEMU中运行RISC-V
donate: true
date: 2025-03-27 15:26:23
categories: riscv
tags: riscv
---

本系列逐步RISC-V的相关知识，范围可能比较广，也可能有时比较专，都是实际用到的使用经验，自己做个笔记也希望能帮助一同学习的朋友们。
# 一重功力：快速启动RISC-V的方法
```bash
apt install opensbi  u-boot-qemu qemu-system-misc

wget https://cdimage.ubuntu.com/releases/24.04.2/release/ubuntu-24.04.2-preinstalled-server-riscv64.img.xz
xz -d ubuntu-24.04.2-preinstalled-server-riscv64.img.xz

./qemu/build/qemu-system-riscv64        \                                              
        -machine virt -vga none -nographic -m 2048 -smp 4       \                      
        -kernel /usr/lib/u-boot/qemu-riscv64_smode/uboot.elf    \                      
        -device virtio-rng-pci  \                                                      
        -drive file=ubuntu-24.04.2-preinstalled-server-riscv64.img,format=raw,if=virtio
```

# 二重功力：内核+QEMU+busybox开发流程
## 依赖包
```bash
apt install autoconf automake autotools-dev curl libmpc-dev libmpfr-dev libgmp-dev \
            gawk build-essential bison flex texinfo gperf libtool patchutils bc \
            zlib1g-dev libexpat-dev github
```

## REPOS
```bash
git clone https://github.com/torvalds/linux
git clone https://github.com/qemu/qemu
git clone https://git.busybox.net/busybox
```

## QEMU编译安装
```bash
./configure --target-list=riscv64-softmmu
make -j $(nproc)
sudo make install
```

## 内核编译
```bash
cd linux
make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- defconfig
make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- -j $(nproc)
```

## 编译busybox
```bash
cd busybox
git chekcout 1_36_stable # 其他稳定版本都编译不过
修改.config中这个配置如下：
CONFIG_TC=n

make menuconfig
选中选项 "Settings/Build static binary(no shared libs)"

CROSS_COMPILE=riscv64-linux-gnu- make oldconfig
CROSS_COMPILE=riscv64-linux-gnu- make -j $(nproc)
CROSS_COMPILE=riscv64-linux-gnu- make install
```

## 创建文件系统rootfs
```bash
# Create root filesystem image
mkdir rootfs
cd rootfs
dd if=/dev/zero of=rootfs.img bs=1M count=50
mkfs.ext2 -L riscv-rootfs rootfs.img
sudo mkdir /mnt/rootfs
sudo mount rootfs.img /mnt/rootfs
sudo cp -ar ../_install/* /mnt/rootfs
sudo mkdir /mnt/rootfs/{dev,home,mnt,proc,sys,tmp,var}
sudo chown -R -h root:root /mnt/rootfs
sudo umount /mnt/rootfs
sudo rmdir /mnt/rootfs
```

## 运行QEMU 自编译内核+busybox
```bash
sudo qemu-system-riscv64 -nographic -machine virt \
     -kernel linux/arch/riscv/boot/Image -append "root=/dev/vda ro console=ttyS0" \
     -drive if=none,file=rootfs.img,format=raw,id=hd0 \
     -device virtio-blk-device,drive=hd0
```

# 三重功力：内核 + QEMU + UEFI + UbuntuOS + opensbi开发流程

## REPOS
```bash
git clone https://github.com/riscv-software-src/opensbi.git
git clone https://github.com/tianocore/edk2.git tianocore/edk2
git clone https://github.com/tianocore/edk2-platforms.git tianocore/edk2-platforms
```
### Workaround
```bash
edk2 repo:
git checkout 3c0d567c3719675b9d8ecf07c31706d96467e31b
git submodule update --init --recursive --force

edk2-platforms:
git checkout 727e458d638784d5e1e9385c61ffc28f23809109
git submodule update --init --recursive --force
git am --3way --ignore-space-change --keep-cr 0001-Riscv-support-based-on-Qemu-mode.patch
```

## 编译opensbi (已经默认集成到了QEMU，可以不需要这步了)
这步的产出是一个elf，作为bios, 通过QEMU的`-bios`参数传递。
```bash
cd $WORK_DIR/opensbi
make ARCH=riscv CROSS_COMPILE=riscv64-linux-gnu- PLATFORM=generic
```

## 编译EDK2
```bash
cd $WORK_DIR/tianocore
export WORKSPACE=`pwd`
export GCC5_RISCV64_PREFIX=/usr/bin/riscv64-linux-gnu-
export PACKAGES_PATH=$WORKSPACE/edk2:$WORKSPACE/edk2-platforms
export EDK_TOOLS_PATH=$WORKSPACE/edk2/BaseTools
source edk2/edksetup.sh
make -C edk2/BaseTools clean
make -C edk2/BaseTools
make -C edk2/BaseTools/Source/C
source edk2/edksetup.sh BaseTools
build -a RISCV64 -b RELEASE -D FW_BASE_ADDRESS=0x80200000 -D EDK2_PAYLOAD_OFFSET -p Platform/Qemu/RiscvVirt/RiscvVirt.dsc -t GCC5
```

## 编译Rootfs (可选后续补充）
```bash
cd $WORK_DIR/
git clone https://github.com/buildroot/buildroot.git
cd $WORK_DIR/buildroot
make qemu_riscv64_virt_defconfig
make rootfs-ext2
```

## 运行QEMU
```bash
./qemu-system-riscv64 -nographic -machine virt,aclint=on,aia=aplic-imsic \
    -cpu rv64,sscofpmf=true -smp 8 -m 2G \
    -kernel tianocore/Build/RiscvVirt/RELEASE_GCC5/FV/RISCVVIRT.fd \
    -drive if=none,file=ubuntu-24.04.2-preinstalled-server-riscv64.img,format=raw,id=hd0 \
    -device virtio-blk-device,drive=hd0
```

## 参考
https://risc-v-getting-started-guide.readthedocs.io/en/latest/linux-qemu.html
https://github.com/riscvarchive/risc-v-getting-started-guide/issues/29
