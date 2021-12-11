---
title: Intel® DSA 综述
donate: true
date: 2021-11-05 10:51:49
categories: x86
tags: kernel dsa
---
## 概述
Intel® DSA是集成在Intel处理器中的高速数据拷贝传输的加速器。用于优化应用程中用于存储、网络、persistent memory以及各种数据处理时的的那些数据流搬运和传输。
Intel® DSA取代了Intel® I/O Acceleration Technology中的Intel® QuickData Technology。

DSA主要用来提供高速系统数据搬运的整体性能，同时降低CPU的负担，并且可以涵盖volatile memory, persistent memory, memory-mapped I/O的双向传输，以及Non-Transparent Bridge (NTB) 和不用node间的的volatile 或者persistent memory 的传输。通过PCIE的编程接口来配置和枚举提供给操作系统，并且通过驱动来控制。

除了基本的数据搬运，DSA提供了一组内存数据搬运操作，例如：
* 生成和校验CRC (checksum)，以及Data Integrity Field(DIF) 用来支持存储和网络应用
* 内存比较和增量合并(delta generate/merge)，用来支持虚拟机迁移等。

一个CPU socket可以支持任意多个DSA设备实例。多socket平台支持多SOC。从软件角度出发，每个实体可以看做一个含有PCIe Root Complex(RC)根节点的终端设备(Endpoint)。每一个实体都在DMA Remapping的硬件单元(也叫做IOMMU, input-output management unit)的范围内。不同的系统设计，多个DSA可以在同一个IOMMU或者不同的IOMMU范围内。

DSA可以只支持SVM操作, share virtual memory，允许设备直接访问应用程序的虚地址(virtual address space)。DSA同样支持Scalable I/O virtualization(Scalable IOV, 或者S-IOV)。同样还支持MSI-X 和IMS(Interrupt Message Store)

![dsa-intro-1.png](dsa-intro-1.png)

上图是DSA内部的一个抽象图。I/O Fabric interface用于接收来自下游终端设备的请求，同时为上游提供数据读写和地址转换操作。

DSA含如下基本的组件：

Work Queues (WQ)， 存储设备用于暂存descriptor 队列，通过新指令添加到WQ中。
* Groups, 包含了一个或多个engine 和work queues的抽象容器。
* Engines， 从WQ中拉取任务并处理。

两种WQ:
* Dedicated WQ (DWQ) - 单一终端看独占并且提交任务。
* Shared WQ (SWQ) - 多个终端设备共享队列

终端使用指令MOVDIR64B向DWQ提交任务，异步写操作。所以，终端设备必须跟踪已经提交的descriptors，确保提交的descriptor不会因为超过预设长度而被丢弃。
终端使用指令ENQCMD(内核态)和ENQCMD(用户态)来提交share work queue。可以通过EFLAGS.ZF 位判断指令是否被接收。

更多细节可以参考 [Intel® Software Developer's Manual (SDM)](https://software.intel.com/en-us/articles/intel-sdm#combined)  和 [Intel® Instruction Set Extensions (ISE)](https://software.intel.com/en-us/articles/intel-sdm#architecture)

## 关键架构
![dsa-intro-2.png](dsa-intro-2.png)

上图是软件架构。内核中驱动名字叫做IDXD(Intel® Data Accelerator Driver)。同时也作为Virtual Device Composition Module(VMCM) 被Intel® Scalable IOV specification 引用。用于创建实例暴露给虚拟机。

内核驱动提供了如下服务:

* 为native应用软件配置WQ的字符设备接口，用于mmap这个设备，并且让设备访问WQ。
* 为内核内部的应用提供WQ的访问API
* VDCM 组成虚拟设备，为虚拟机提供Intel DSA实例
* 通过sysfs文件系统提供用户接口，用于发现设备以及配置work queue.

更多详情，参考[ Intel® DSA specification](https://software.intel.com/en-us/download/intel-data-streaming-accelerator-preliminary-architecture-specification)

## ACCELERATOR CONFIGURATOR  (ACCEL-CONFIG)

accel-config是一套给系统管理员配置groups, work queue，engine用的工具。它能够解析经过sysfs提供的头结构以及RSA的能力，并且提供了命令行接口，配置资源。

* 显示设备层级
* 配置属性，为内核和应用提供访问接口。
* 应用程序可以使用标准C语言库来使用API库(libaccel)
* 控制设备启停
* 创建VFIO仲裁设备，为虚拟机的操作系统提供虚拟DSA设备

更多可参考：[accel-config](https://github.com/intel/idxd)

## 内核中使用DSA
通过sysfs，可以为每一个WQ指定类型和名字。这允许WQ被预留。驱动中有三种类型：

* Kernel - 预留给内核使用的
* User - 预留给用户空间使用的，比如DPDK等
* Mdev - 预留给mediated devices (mdev)，是虚拟机使用的

给用户和mdev使用时，可以为WQ指定一个字符串用来表示预留的目的，比如字符串mysql或者DPDK等 用来标示预留的目的。

![dsa-intro-3.png](dsa-intro-3.png)

IDXD驱动处理Linux内核DMA engine产生内核WQ请求。类似的例子还有ClearPage engine, NonTransparent Bridge (NTB),persistent memory

## 参考
Intel® DSA Specification:  https://software.intel.com/en-us/download/intel-data-streaming-accelerat...
Intel® Data Accelerator Driver GitHub repository:  https://github.com/intel/idxd-driver
Intel® Data Accelerator Driver Overview on GitHub.io:  https://intel.github.io/idxd/
Intel® Data Accelerator Control Utility and Library: https://github.com/intel/idxd-config
Shared Virtual Memory:  https://software.intel.com/en-us/articles/opencl-20-shared-virtual-memor...
Intel® Scalable I/O Virtualization:  https://software.intel.com/sites/default/files/managed/cc/0e/intel-scala...
Intel® 64 and IA-32 Architectures Software Developer Manuals:  https://software.intel.com/en-us/articles/intel-sdm

Address Translation Services (ATS)
Process Address Space ID (PASID)
Page Request Services (PRS)
Message Signalled Interrupts Extended (MSI-X)
Advanced Error Reporting (AER)
