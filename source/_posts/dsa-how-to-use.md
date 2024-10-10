---
title: 一张图看明白如何使用Intel DSA
donate: true
date: 2024-10-09 10:55:54
categories: Kernel
tags: Kernel X86
---
## 什么是DSA
英特尔® DSA（Data Stream Accelerator 数据流加速器）是一款高性能的数据复制和转换加速器，自第四代英特尔® 至强® 处理器开始集成在英特尔® 处理器中。专为优化流数据传输和转换而设计。

## 如何配置
### IOMMU 驱动
必须在内核配置中启用支持可扩展模式的 Intel® IOMMU 驱动程序，相关内核配置：
```
CONFIG_INTEL_IOMMU=y
CONFIG_INTEL_IOMMU_SVM=y
CONFIG_INTEL_IOMMU_DEFAULT_ON=y
CONFIG_INTEL_IOMMU_SCALABLE_MODE_DEFAULT_ON=y
```
如果使能`CONFIG_INTEL_IOMMU_DEFAULT_ON`或者`CONFIG_INTEL_IOMMU_SCALABLE_MODE_DEFAULT_ON` 选项，则必须在内核启动参数中添加`intel_iommu=on,sm_on`。

### DSA 驱动
CONFIG_INTEL_IDXD=m
CONFIG_INTEL_IDXD_SVM=y
CONFIG_INTEL_IDXD_PERFMON=y

工作队列（WQs）是设备上的存储，用于存放提交给设备的描述符，可以配置为两种模式：专用模式（DWQ）或共享模式（SWQ）。SWQ 允许多个客户端同时提交描述符，而无需进行跟踪工作队列占用情况的同步操作，因此没有软件开销。SWQ 是首选的工作队列模式，因为它相比于 DWQ 的硬分区提供了更好的设备利用率，而 DWQ 可能会导致资源未充分利用。支持 DWQ 的 Intel® DSA 驱动程序（IDXD）在内核版本 5.6 中引入，而支持 SWQ 的 IDXD 驱动程序在 Linux 主线内核 5.18 及更高版本中提供。

### device ID
DSA的PCI设备ID,在GNR之前（SPR，EMR，GNR）是0x0b25，但是这个只在下一代的CPU上，会发生变化。（可以专门一讲，一块学习下DSA的Device ID为什么会发生变化:p)

```
# lspci | grep 0b25
6a:01.0 System peripheral: Intel Corporation Device 0b25
6f:01.0 System peripheral: Intel Corporation Device 0b25
74:01.0 System peripheral: Intel Corporation Device 0b25
79:01.0 System peripheral: Intel Corporation Device 0b25
e7:01.0 System peripheral: Intel Corporation Device 0b25
ec:01.0 System peripheral: Intel Corporation Device 0b25
f1:01.0 System peripheral: Intel Corporation Device 0b25
f6:01.0 System peripheral: Intel Corporation Device 0b25
```

完整的PCI信息列一下，可以看到更多DSA工作所需要的服务:
```
6a:01.0 System peripheral: Intel Corporation Device 0b25                                                           
        Subsystem: Intel Corporation Device 0000                                                                   
        Control: I/O- Mem+ BusMaster+ SpecCycle- MemWINV- VGASnoop- ParErr+ Stepping- SERR+ FastB2B- DisINTx-      
        Status: Cap+ 66MHz- UDF- FastB2B- ParErr- DEVSEL=fast >TAbort- <TAbort- <MAbort- >SERR- <PERR- INTx-       
        Latency: 0                                                                                                 
        NUMA node: 0                                                                                               
        IOMMU group: 12                                                                                            
        Region 0: Memory at 206ffff40000 (64-bit, prefetchable) [size=64K]                                         
        Region 2: Memory at 206ffff00000 (64-bit, prefetchable) [size=128K]                                        
        Capabilities: [40] Express (v2) Root Complex Integrated Endpoint, MSI 00                                   
                DevCap: MaxPayload 128 bytes, PhantFunc 0                                                          
                        ExtTag+ RBE+ FLReset+                                                                      
                DevCtl: CorrErr+ NonFatalErr+ FatalErr+ UnsupReq-                                                  
                        RlxdOrd+ ExtTag+ PhantFunc- AuxPwr- NoSnoop+ FLReset-                                      
                        MaxPayload 128 bytes, MaxReadReq 4096 bytes                                                
                DevSta: CorrErr- NonFatalErr- FatalErr- UnsupReq- AuxPwr- TransPend-                               
                DevCap2: Completion Timeout: Not Supported, TimeoutDis+ NROPrPrP- LTR+                             
                         10BitTagComp+ 10BitTagReq+ OBFF Not Supported, ExtFmt+ EETLPPrefix+, MaxEETLPPrefixes 1   
                         EmergencyPowerReduction Not Supported, EmergencyPowerReductionInit-                       
                         FRS-                                                                                      
                         AtomicOpsCap: 32bit- 64bit- 128bitCAS-                                                    
                DevCtl2: Completion Timeout: 50us to 50ms, TimeoutDis- LTR- OBFF Disabled,                         
                         AtomicOpsCtl: ReqEn-                                                                      
        Capabilities: [80] MSI-X: Enable+ Count=9 Masked-                                                          
                Vector table: BAR=0 offset=00002000                                                                
                PBA: BAR=0 offset=00003000                                                                         
        Capabilities: [90] Power Management version 3                                                              
                Flags: PMEClk- DSI- D1- D2- AuxCurrent=0mA PME(D0-,D1-,D2-,D3hot-,D3cold-)                         
                Status: D0 NoSoftRst+ PME-Enable- DSel=0 DScale=0 PME-                                             
        Capabilities: [100 v2] Advanced Error Reporting                                                            
                UESta:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- UnxCmplt- RxOF- MalfTLP- ECRC- UnsupReq- ACSViol- 
                UEMsk:  DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- UnxCmplt- RxOF- MalfTLP- ECRC- UnsupReq+ ACSViol- 
                UESvrt: DLP- SDES- TLP- FCP- CmpltTO- CmpltAbrt- UnxCmplt- RxOF- MalfTLP+ ECRC- UnsupReq- ACSViol- 
                CESta:  RxErr- BadTLP- BadDLLP- Rollover- Timeout- AdvNonFatalErr-                                 
                CEMsk:  RxErr- BadTLP- BadDLLP- Rollover- Timeout- AdvNonFatalErr-                                 
                AERCap: First Error Pointer: 00, ECRCGenCap- ECRCGenEn- ECRCChkCap- ECRCChkEn-                     
                        MultHdrRecCap- MultHdrRecEn- TLPPfxPres- HdrLogCap-                                        
                HeaderLog: 00000000 00000000 00000000 00000000                                                     
        Capabilities: [150 v1] Latency Tolerance Reporting                                                         
                Max snoop latency: 0ns                                                                             
                Max no snoop latency: 0ns                                                                          
        Capabilities: [160 v1] Transaction Processing Hints                                                        
                Device specific mode supported                                                                     
                Steering table in TPH capability structure                                                         
        Capabilities: [170 v1] Virtual Channel                                                   
                Caps:   LPEVC=1 RefClk=100ns PATEntryBits=1                                      
                Arb:    Fixed+ WRR32- WRR64- WRR128-                                             
                Ctrl:   ArbSelect=Fixed                                                          
                Status: InProgress-                                                              
                VC0:    Caps:   PATOffset=00 MaxTimeSlots=1 RejSnoopTrans-                       
                        Arb:    Fixed- WRR32- WRR64- WRR128- TWRR128- WRR256-                    
                        Ctrl:   Enable+ ID=0 ArbSelect=Fixed TC/VC=fd                            
                        Status: NegoPending- InProgress-                                         
                VC1:    Caps:   PATOffset=00 MaxTimeSlots=1 RejSnoopTrans-                       
                        Arb:    Fixed- WRR32- WRR64- WRR128- TWRR128- WRR256-                    
                        Ctrl:   Enable+ ID=1 ArbSelect=Fixed TC/VC=02                            
                        Status: NegoPending- InProgress-                                         
        Capabilities: [200 v1] Designated Vendor-Specific: Vendor=8086 ID=0005 Rev=0 Len=24 <?>  
        Capabilities: [220 v1] Address Translation Service (ATS)                                 
                ATSCap: Invalidate Queue Depth: 00                                               
                ATSCtl: Enable+, Smallest Translation Unit: 00                                   
        Capabilities: [230 v1] Process Address Space ID (PASID)                                  
                PASIDCap: Exec- Priv+, Max PASID Width: 14                                       
                PASIDCtl: Enable+ Exec- Priv+                                                    
        Capabilities: [240 v1] Page Request Interface (PRI)                                      
                PRICtl: Enable+ Reset-                                                           
                PRISta: RF- UPRGI- Stopped+                                                      
                Page Request Capacity: 00000200, Page Request Allocation: 00000200               
        Kernel driver in use: idxd                                                               
        Kernel modules: idxd                                                                     
```

### SVM
DSA（数据流加速器）设备支持SVM技术，在Linux共享虚拟地址（SVA）框架下实现。 Intel的SVM（共享虚拟内存）技术，是将设备运行时的地址放在访问该设备的应用程序的 CPU 虚拟地址空间中。设备可以访问虚拟地址空间，而且设备无需具备复杂的MMU功能，使用 PASID 来区分不同应用程序的虚拟地址空间。通过PCI的PASID（进程地址空间标识符）将特定的CPU进程进行绑定，同时IOMMU能够访问CPU的MMU页表。当设备访问的地址不在设备的地址转换缓存（ATC）中时，它会通过地址转换服务（ATS）向IOMMU请求相应的页表转换，无需将设备访问的页面固定在内存中。
上面lspci的输出中可以看到最后三个`Capabilities`： ATSCtrl, PASIDCtl和PRICtl 三项已经启用。

### sysfs
Linux的sysfs文件系统是一种伪文件系统，为内核数据结构提供了一个接口。sysfs 下的文件提供了关于设备、内核模块、文件系统以及其他内核组件的信息。

Linux 驱动程序会为每个处理器生成如下所示的4 个sysfs目录。Intel DSA 和 Intel® IAA 设备都由 IDXD 设备驱动程序进行管理。
可以看到驱动程序创建了4个dsa 设备文件dsa{0,2,4,6}，4个iax设备文件iax{1,3,5,7,9}。同时还有每个设备上的8个workqueue，4个engine和4个group。

```
# ll /sys/bus/dsa/devices/
root /sys/bus/dsa/devices/dsa0 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0
root /sys/bus/dsa/devices/dsa2 -> ../../../devices/pci0000:6f/0000:6f:01.0/dsa2
root /sys/bus/dsa/devices/dsa4 -> ../../../devices/pci0000:74/0000:74:01.0/dsa4
root /sys/bus/dsa/devices/dsa6 -> ../../../devices/pci0000:79/0000:79:01.0/dsa6
root /sys/bus/dsa/devices/iax1 -> ../../../devices/pci0000:6a/0000:6a:02.0/iax1    
root /sys/bus/dsa/devices/iax3 -> ../../../devices/pci0000:6f/0000:6f:02.0/iax3    
root /sys/bus/dsa/devices/iax5 -> ../../../devices/pci0000:74/0000:74:02.0/iax5    
root /sys/bus/dsa/devices/iax7 -> ../../../devices/pci0000:79/0000:79:02.0/iax7    

root /sys/bus/dsa/devices/wq0.0 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.0
root /sys/bus/dsa/devices/wq0.1 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.1
root /sys/bus/dsa/devices/wq0.2 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.2
root /sys/bus/dsa/devices/wq0.3 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.3
root /sys/bus/dsa/devices/wq0.4 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.4
root /sys/bus/dsa/devices/wq0.5 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.5
root /sys/bus/dsa/devices/wq0.6 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.6
root /sys/bus/dsa/devices/wq0.7 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/wq0.7
......

root 0 Oct 10 06:00 engine0.0 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/engine0.0
root 0 Oct 10 06:00 engine0.1 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/engine0.1
root 0 Oct 10 06:00 engine0.2 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/engine0.2
root 0 Oct 10 06:00 engine0.3 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/engine0.3
......

root 0 Oct 10 06:00 group0.0 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/group0.0
root 0 Oct 10 06:00 group0.1 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/group0.1
root 0 Oct 10 06:00 group0.2 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/group0.2
root 0 Oct 10 06:00 group0.3 -> ../../../devices/pci0000:6a/0000:6a:01.0/dsa0/group0.3
......

```

## 设备配置
### DSA WQs
软件通过在内存中构建描述符并将其提交到工作队列（SWQ）来指定设备的工作。共享工作队列（WQ）允许多个客户端同时提交描述符，因此推荐用于应用程序场景。专用工作队列（DWQ）要求软件通过跟踪已提交和已完成的描述符来管理流控制，以确保不会超出工作队列的容量。因此，当单个操作系统级进程使用工作队列时，专用 WQ 非常有用。

### DSA Engines
引擎是 Intel DSA 设备中的一个操作单元。

### DSA Group
组（Group）是逻辑上对一组工作队列和引擎的组织。多个组可以在共享设备的应用程序之间提供性能隔离。

### accel-config
accel-config是一个Linux应用程序，提供了配置DSA设备的命令行工具。

所有DSA以及workqueue engine group等的相关的配置要求root用户。下图可以一个图来说明配置的步骤：
![dsa-usage2-watermark.jpg](dsa-usage2-watermark.jpg)

便于copy-paste
```
方式1：
  echo 0 > /sys/bus/dsa/devices/dsa0/wq0.0/group_id
  echo dedicated > /sys/bus/dsa/devices/dsa0/wq0.0/mode
  echo 10 > /sys/bus/dsa/devices/dsa0/wq0.0/priority
  echo 16 > /sys/bus/dsa/devices/dsa0/wq0.0/size
  echo "kernel" > /sys/bus/dsa/devices/dsa0/wq0.0/type
  echo "dma2chan0" > /sys/bus/dsa/devices/dsa0/wq0.0/name
  echo "dmaengine" > /sys/bus/dsa/devices/dsa0/wq0.0/driver_name
  echo 0 > /sys/bus/dsa/devices/dsa0/engine0.0/group_id
  echo dsa0 > /sys/bus/dsa/drivers/idxd/bind
  echo wq0.0 > /sys/bus/dsa/drivers/dmaengine/bind

方式2:
  accel-config config-engine dsa0/engine0.2 --group-id=0.0
  accel-config config-wq dsa0/wq0.0 --group-id=0 --wq-size=32 --priority=1 --block-on-fault=0 --threshold=4 --type=user --name=swq --mode=shared

  accel-config enable-device dsa0
  accel-config enable-wq dsa0/wq0.0

  accel-config save-config -s save_config.conf
方式3:
  accel-config load-config -c contrib/configs/app_profile.conf -e
```

## 使用DSA
在配置好设备之后，使用DSA需要下面的几步：
1. 配置描述符(descriptor)
2. 打开/映射 /dev/dsa/wq0.0 文件
3. 提交描述符(descriptor)
4. 确认完成

### 描述符descriptor
描述符是一个64字节并且对齐的结构体，用的时候，需要查阅开发者手册，填写对应字节/位上的值，然后把地址通过指定提交给DSA设备。下面是手册中一个基本的描述符的样子。但是对数据的操作不同，描述符的内容不尽相同，具体operation code不同，还需要具体查阅手册。
![dsa-descriptor-format.png](dsa-descriptor-format.png)

### /dev/dsa/wq0.0
在向设备提交描述符之前，应用程序必须打开一个之前配置好的工作队列（WQ）设备文件（例如 /dev/dsa/wq0.0），并将该工作队列的任务提交端口映射到其地址空间(或者使用系统调用write)，将描述符提交到设备。

共享工作队列（WQ）设备文件可以被多个进程同时打开，而专用工作队列设备文件在任何时刻只能由单个进程打开。

### 提交描述符
根据工作队列（WQ）的类型，软件可能会使用 ENQCMD 或 MOVDIR64B 指令来提交描述符。Intel® DSA 架构规范中的“共享工作队列”部分描述了当描述符未被设备接受时，ENQCMD 会返回一个非零值。gcc10通过 -menqcmd 和 -mmovdir64b 选项支持 ENQCMD 和 MOVDIR64B 的内置函数 _enqcmd() 和 _movdir64b()。对于较旧的编译器版本，可以直接使用机器码:
```c
static inline void
movdir64b(void *dst, const void *src)
{
    asm volatile(".byte 0x66, 0x0f, 0x38, 0xf8, 0x02\t\n"
            : : "a" (dst), "d" (src));
}

static inline unsigned int
enqcmd(void *dst, const void *src)
{
    uint8_t retry;
    asm volatile(".byte 0xf2, 0x0f, 0x38, 0xf8, 0x02\t\n"
            "setz %0\t\n"
            : "=r"(retry) : "a" (dst), "d" (src));

    return (unsigned int)retry;
}
```

所以，一个典型DSA应用程序最终这样提交:
```
if (dedicated)
        _movdir64b(wq_portal, &desc);
else {
        retry = 0;
        while (_enqcmd(wq_portal, &desc) && retry++ < ENQ_RETRY_MAX);
    }
```

### 检查完成
当 Intel DSA 硬件完成描述符的处理后，会更新完成记录的状态字段。下面的代码片段展示了完成检查的过程。

```
retry = 0;

while (comp.status == 0 && retry++ < COMP_RETRY_MAX);
if (comp.status == DSA_COMP_SUCCESS) {
    /* Successful completion */
} else {
    /* Descriptor failed or timed out
     * See the “Error Codes” section of the Intel® DSA Architecture Specification for
     * error code descriptions
     */
}
```


Intel DSA 和 Intel IAA 设备的编号取决于每种设备在 CPU SKU 中的数量。在下面的双插槽示例中，每个插槽包含四个 Intel 内存分析加速器（IAA）设备，
在一个具有双插槽系统的示例中，Linux 驱动程序会为总共八个 Intel DSA 设备（每个处理器四个设备）生成如图 3-6 所示的 sysfs 目录。Intel DSA 和 Intel® IAA 设备都由 IDXD 设备驱动程序进行管理。Intel DSA 和 Intel IAA 设备的编号取决于每种设备在 CPU SKU 中的数量。在下面的双插槽示例中，每个插槽包含四个 Intel 内存分析加速器（IAA）设备，它们被命名为 iax{1,3,5,7,9,11,13,15}。相应地，Intel DSA 设备被命名为 dsa{0,2,4,6,8,10,12,14}。

在PCI总线上，PASID占用了TLP（事务层包）头的一部分，通常使用20个比特位来传输PASID值，这个值一般由IOMMU在配置设备时指定。有关PASID TLP的具体格式，请参见PCI规范6.0中的详细描述。PASID的分配和管理代码位于内核目录的drivers/iommu/iommu-sva.c文件中。

在IOMMU中，支持PASID的模式也被称为可扩展模式（Scalable Mode）。当启用可扩展模式时，会在传统页表前面添加PASID的上下文条目。根据最新的VT-d规范，在可扩展模式的地址转换中，每个设备都有各自的PASID上下文表，最终的PASID表会指向一级和二级页表。

ATS通过特殊类型的TLP包来实现，具体的格式可以在PCI规范6.0第十章的地址转换服务中找到。

PRS同样通过特殊类型的TLP包实现，详细格式可以参见PCI规范6.0第十章中的页请求消息相关内容。

当DSA设备与主机共享地址空间时，只需启用ATC/ATS和PRS功能即可实现。这其中PRS与描述符标志中的“block on fault”位有关。

对于DSA与虚拟机共享内存空间的情况，需要平台启用可扩展模式，同时虚拟机管理程序（VMM）需要在IOMMU中为虚拟机配置PASID。分配给虚拟机的DSA虚拟设备（vDEV）也需要支持ATS、PASID和PRS功能。目前，DSA虚拟设备的支持仍在社区中进行评审。




共享虚拟内存（SVM），在支持SVM的系统中，
与 SVM 相关的 PCIe 功能和状态（如 ATSCtl、PASIDCtl 和 PRICtl）已经启用，如图 3-4 所示。有关 Intel DSA 如何利用 PASID、PCIe、ATS 和 PRS 功能来支持 SVM 的详细信息，请参考 Intel® DSA 架构规范中的地址转换部分。


英特尔公司



