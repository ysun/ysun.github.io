---
title: 用QEMU来体会PCI/PCIE设备
donate: true
date: 2021-12-09 17:13:55
categories:
tags:
---

PCI以及PCIE设备非常普遍，其驱动也是内核中非常重要的一部分，受到网友的启发，借助QEMU一次性把PCI/PCIE的拓扑结构给说透(尽量)。
为了简单，这里使用virtio-scsi-pci HBA (host bus adapter)作为例子，分别来探究PCI和PCIE两种不同类型的总线。
## PCI
先来PCI3.0文档里的拓扑图
![pci-topology.png](pci-topology.png)

### PCI Root Bus (PXB, PCI Expander Bridge)
如上图所示，左上角的Processor/cache/DRAM 都经过一个Bridge，链接在了PCI 总线上。(忽略掉Aduio和Motion Video两个设备)，图的左下的Lan 和SCSI两个设备直接连在了PCI总线上。
下面就利用QEMU模拟这两种PCI设备的场景。

```
qemu-system-x86_64 \
    -m 2048 -smp 1 \
    -enable-kvm \
    -cpu max \
    -vga none -nodefaults -nographic \
    -serial mon:stdio \
    -hda /home/works/kvm/ubuntu20.10_mini.img \
    -bios ovmf/OVMF_CODE.fd \
    -append "root=/dev/sda3 nokaslr console=ttyS0"  \
    -kernel /home/works/linux-stable/arch/x86/boot/bzImage \
    -net nic -net user,hostfwd=tcp::5028-:22 \
    -machine pc,kernel-irqchip=split \
1-> -device virtio-scsi-pci,bus=pci.0,addr=0x4 \
2-> -device pxb,id=bridge1,bus=pci.0,bus_nr=3,addr=0x5 \
        -device virtio-scsi-pci,bus=bridge1,addr=0x7 \
3-> -device pxb,id=bridge2,bus=pci.0,bus_nr=8,addr=0x6 \
        -device virtio-scsi-pci,bus=bridge2,addr=0x8 \
        -device virtio-scsi-pci,bus=bridge2,addr=0x9 \
4-> -device pci-bridge,id=bridge10,chassis_nr=3,addr=0x14 \
        -device virtio-scsi-pci,id=scsi0,bus=bridge10,addr=0x16 \
5-> -device pci-bridge,id=bridge11,chassis_nr=4,addr=0x15 \
        -device virtio-scsi-pci,id=scsi1,bus=bridge11,addr=0x17 \
        -device virtio-scsi-pci,id=scsi2,bus=bridge11,addr=0x18
```
说明：
* 箭头1，是把HBA直接接在了PCI bus上，并且地址是0x4。
* 箭头2，是接了一个PXB(PCI Expander Bridge)到PCI bus上，实际上是增加了PCI bus，配置bus号为0x3,地址是0x5。
* 箭头3，跟2类似，只不过下面再接两个HBA，bus号是0x8。
* 箭头4，接一个bridge到PCIbus上面，bridge的地址是0x14; bridge不会新增Bus号!同时在其下添加一个HBA，地址配置为0x6
* 箭头5，与4类似，区别就是在下面接两个HBA。


对应的拓扑结构如下所示：

```
root@u2010-mini:~# lspci -tvnn
-+-[0000:08]-+-00.0-[09]--+-08.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 |           |            \-09.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 |           +-14.0-[0a]----16.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 |           \-15.0-[0b]--+-17.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 |                        \-18.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 +-[0000:03]---00.0-[04]----07.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
 \-[0000:00]-+-00.0  Intel Corporation 440FX - 82441FX PMC [Natoma] [8086:1237]
             +-01.0  Intel Corporation 82371SB PIIX3 ISA [Natoma/Triton II] [8086:7000]
             +-01.1  Intel Corporation 82371SB PIIX3 IDE [Natoma/Triton II] [8086:7010]
             +-01.3  Intel Corporation 82371AB/EB/MB PIIX4 ACPI [8086:7113]
             +-02.0  Intel Corporation 82540EM Gigabit Ethernet Controller [8086:100e]
             +-04.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
             +-05.0  Red Hat, Inc. QEMU PCI Expander bridge [1b36:0009]
             \-06.0  Red Hat, Inc. QEMU PCI Expander bridge [1b36:0009]
```

```
pci.0 bus
-------------------------------------------------------------------------------------
     |             |               |                  |                   |
-----------  ------------  -------------     --------------      --------------
| PCI Dev |  | PXB      |  | PXB       |     | PCI-bridge |      | PCI-bridge |
| 0x4     |  | 0x5      |  | 0x6       |     | 0x14       |      | 0x15       |
-----------  ------------  -------------     --------------      --------------
               |            |         |             |             |           |     
      ------------  -------------  ------------  ------------  ------------ ------------
      |v-scsi-pci|  |v-scsi-pci |  |v-scsi-pci|  |v-scsi-pci|  |v-scsi-pci| |v-scsi-pci|
      | 0x7      |  | 0x8       |  |0x9       |  |0x16      |  |0x17      | |0x18      |
      ------------  -------------  ------------  ------------  ------------ ------------
                   
```

## PCIE
先来PCIE5.0文档里的拓扑结构图。
![pcie-topology.png](pcie-topology.png)

PCIE分两个小结来探讨。
### PCIE root complex / PCIE-PCI bridge / PCIE / PCI
```
qemu-system-x86_64 \
    -m 2048 -smp 1 \
    -enable-kvm \
    -cpu max \
    -vga none -nodefaults -nographic \
    -serial mon:stdio \
    -hda /home/works/kvm/ubuntu20.10_mini.img \
    -bios ovmf/OVMF_CODE.fd \
    -append "root=/dev/sda3 nokaslr console=ttyS0"  \
    -kernel /home/works/linux-stable/arch/x86/boot/bzImage \
    -net nic -net user,hostfwd=tcp::5028-:22 \
    -machine q35,kernel-irqchip=split \
    -device intel-iommu,intremap=on \
    -device e1000e,bus=pcie.0,addr=0x2 \
1-> -device virtio-scsi-pci,bus=pcie.0,addr=0x3 \
2-> -device pxb-pcie,id=pcie1,bus_nr=3,bus=pcie.0,addr=0x4 \
3->   -device ioh3420,id=pcie_port1,bus=pcie1,chassis=1 \
        -device virtio-scsi-pci,bus=pcie_port1 \
      -device ioh3420,id=pcie_port2,bus=pcie1,chassis=2 \
        -device virtio-scsi-pci,bus=pcie_port2 \
4-> -device pcie-pci-bridge,id=pcie_pci_bridge1,bus=pcie.0 \
      -device virtio-scsi-pci,bus=pcie_pci_bridge1
```
说明：
* 箭头3，是把HBA直接接在了PCIE bus上，并且地址是0x3。
* 箭头3，是接了一个PXB(PCI Expander Bridge)到PCIE bus上，增加了PCIE bus，配置bus号为0x3,地址是0x4。
* 箭头3，然后再在pxb-pcie上接一个IOHUB，并且配置地址是0x6，然后再把HBA接再HUB上。相比PCI bug多了一个HUB，是因为pxb-pcie不可以直接接PCIE设备。
* 箭头4，接了一个PCIE-PCI的bridge，下面可以在接多个pci设备。

```
# lspci -tvnn
-+-[0000:03]-+-00.0-[04]----00.0  Red Hat, Inc. Virtio SCSI [1af4:1048]
 |           \-01.0-[05]----00.0  Red Hat, Inc. Virtio SCSI [1af4:1048]
 \-[0000:00]-+-00.0  Intel Corporation 82G33/G31/P35/P31 Express DRAM Controller [8086:29c0]
             +-01.0  Intel Corporation 82574L Gigabit Network Connection [8086:10d3]
             +-02.0  Intel Corporation 82574L Gigabit Network Connection [8086:10d3]
             +-03.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
             +-04.0  Red Hat, Inc. QEMU PCIe Expander bridge [1b36:000b]
             +-05.0-[01]----00.0  Red Hat, Inc. Virtio SCSI [1af4:1004]
             +-1f.0  Intel Corporation 82801IB (ICH9) LPC Interface Controller [8086:2918]
             +-1f.2  Intel Corporation 82801IR/IO/IH (ICH9R/DO/DH) 6 port SATA Controller [AHCI mode] [8086:2922]
             \-1f.3  Intel Corporation 82801I (ICH9 Family) SMBus Controller [8086:2930]
```

```
pci.0 bus
--------------------------------------------------------------------------[0000:00]
     |             |              |               |         
----------     ---------    -------------     ----------    
|PCIE Dev|     |PCI Dev|    |PCIE-PCI-br|     |PXB-PCIE|    
|0x2     |     |0x3    |    | 0x5       |     | 0x4    |    
----------     ---------    ------------      ----------    
                                  |               |         
                            -------------     ----------------------------[0000:03]
                            |v-scsi-pci |            |             |               
                            | 0x0       |       ------------  ------------
                            -------------       |root-port |  |root-port |
                                                | 0x0      |  | 0x1      |
                                                ------------  ------------
                                                     |              |
                                               --------------   --------------
                                               | PCI-bridge |   | PCI-bridge |
                                               | 0x0        |   | 0x0        |
                                               --------------   --------------
```

### PCIE SWITCH
对于switch，这里特别的拎出来说下。PCIE5 spec文档的图是这样的。
![pcie-switch-topology.png](pcie-switch-topology.png)
```
qemu-system-x86_64 \
    -m 2048 -smp 1 \
    -enable-kvm \
    -cpu max \
    -vga none -nodefaults -nographic \
    -serial mon:stdio \
    -hda /home/works/kvm/ubuntu20.10_mini.img \
    -bios ovmf/OVMF_CODE.fd \
    -append "root=/dev/sda3 nokaslr console=ttyS0"  \
    -kernel /home/works/linux-stable/arch/x86/boot/bzImage \
    -net nic -net user,hostfwd=tcp::5028-:22 \
    -machine q35,kernel-irqchip=split \
    -device intel-iommu,intremap=on \
1-> -device ioh3420,id=root_port1,bus=pcie.0 \
2->   -device x3130-upstream,id=upstream1,bus=root_port1 \
3->     -device xio3130-downstream,id=downstream1,bus=upstream1,chassis=9 \
          -device virtio-scsi-pci,bus=downstream1 \
        -device xio3130-downstream,id=downstream2,bus=upstream1,chassis=10 \
          -device e1000e,bus=downstream2 \
          -device virtio-scsi-pci,bus=downstream2 \
```

说明:
* 箭头1，创建一个PCI Express Root Ports (ioh3420)
* 箭头2，与PCI设备不同，PCIE swith其实是两个bus上下连接起来的，upstream 和downstream。
  然后在downstream的下面，接PCI/PCIE设备. switch的upstream，其实相当于一个pci bus.
* 箭头3，switch的downstream，也相当于一个pci bus。再在downstream的下面，挂设备，既有PCI设备(HBA)又有PCIE设备(e1000e)。

```
# lspci -tvnn
-[0000:00]-+-00.0  Intel Corporation 82G33/G31/P35/P31 Express DRAM Controller [8086:29c0]
           +-01.0  Intel Corporation 82574L Gigabit Network Connection [8086:10d3]
           +-02.0-[01-04]----00.0-[02-04]--+-00.0-[03]----00.0  Red Hat, Inc. Virtio SCSI [1af4:1048]
           |                               \-01.0-[04]----00.0  Intel Corporation 82574L Gigabit Network Connection [8086:10d3]
           +-1f.0  Intel Corporation 82801IB (ICH9) LPC Interface Controller [8086:2918]
           +-1f.2  Intel Corporation 82801IR/IO/IH (ICH9R/DO/DH) 6 port SATA Controller [AHCI mode] [8086:2922]
           \-1f.3  Intel Corporation 82801I (ICH9 Family) SMBus Controller [8086:2930]
```

```
pci.0 bus
----------------------------------------------------------------[0000:00]
                     |         
                 -----------    
                 |root port|    
                 | 0x2     |    
                 -----------    
                     |         
               --------------    
               |  upstream  |    
               |            |    
               --------------    
               |            |               
        ---------------- ----------------
        |  downstream  | |  downstream  |
        |   0x0        | |   0x1        |
        ---------------- ----------------
               |            |           |
     -------------- -------------- --------------
     | v-scsi-pci | | pcie-e1000e| | v-scsi-pci |
     | 0x0        | | 0x0        | | 0x1        |
     -------------- -------------- --------------

```

## 参考文档

[NCB-PCI_Express_Base_5.0r1.0-2019-05-22.pdf](NCB-PCI_Express_Base_5.0r1.0-2019-05-22.pdf)
[PCI_LB3.0-2-6-04.pdf](PCI_LB3.0-2-6-04.pdf)
[qemu-6.1.0/docs/pcie.txt](https://fossies.org/linux/qemu/docs/pcie.txt)
[A study of the Linux kernel PCI subsystem with QEMU](https://blogs.oracle.com/linux/post/a-study-of-the-linux-kernel-pci-subsystem-with-qemu)

