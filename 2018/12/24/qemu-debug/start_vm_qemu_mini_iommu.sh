#!/bin/bash

qemu-system-x86_64 \
	-m 2048 -smp 1 \
	-enable-kvm \
	-cpu max \
	-vga none -nodefaults -nographic \
	-serial mon:stdio \
	-hda /home/works/kvm/ubuntu20.10_mini.img \
	-append "root=/dev/sda3 nokaslr console=ttyS0"  \
	-kernel /home/works/linux-stable/arch/x86/boot/bzImage \
	-net nic -net user,hostfwd=tcp::5028-:22 \
	-s -S \
	-machine q35,kernel-irqchip=split \
	-device intel-iommu,intremap=on
#	-bios ovmf/OVMF_CODE.fd \
#	-boot order=c,menu=off \

