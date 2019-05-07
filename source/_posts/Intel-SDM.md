---
title: 英特尔®64和IA-32架构软件开发人员手册(Intel SDM)
donate: true
date: 2019-01-29 14:05:12
categories:
tags:
---

### 23.1 概述
本章介绍虚拟机体系结构的基础知识和虚拟机扩展的概述(VMX),支持多个软件环境的处理器硬件虚拟化。
关于VMX指令的信息参考英特尔®64和IA-32架构软件开发人员手册中的第2B卷。其他关于VMX和系统编程参考SDM 第3B卷

### 23.2虚拟机器结构
虚拟机扩展为IA-32处理器上的虚拟机定义了处理器级支持。两个重要支持的软件类别：

- 虚拟机监视器(VMM)
VMM充当主机，可以完全控制处理器和其他处理器平台硬件。 VMM使用虚拟的抽象来呈现客户软件(参见下一段)
处理器并允许它直接在逻辑处理器上执行。 VMM能够保留选择性控制处理器资源，物理内存，中断管理和I / O。

- Guest- 每个虚拟机(VM)
是一个支持堆栈组成的客户软件环境,操作系统(OS)和应用程序软件。每个都独立于其他虚拟机运行在物理的处理器上，内存，存储器，图形和I / O的相同接口上使用平台。软件堆栈就像在没有VMM的平台上运行一样。软件执行中虚拟机必须以降低的权限运行，以便VMM可以保留对平台资源的控制。

### 23.3 VMX操作简介
虚拟化的处理器支持由称为VMX操作的处理器操作形式提供。有两种VMX操作：VMX root和VMX non-root操作。通常，VMM运行在VMX root模式下，同时将guest 软件运行在non-root模式下。
VMX root操作和VMX non-root操作的转换称为VMX转换。有两种VMX转换:
- 从VMX root过渡到VMX non-root模式称为VM entry； 
- 从VMX not-root操作到VMX root的转换成为VM exit。
VMX root操作中的处理器行为与VMX操作之外的处理器行为非常相似。主要区别是一组新指令(VMX指令)（见第23.8节）。
VMX non-root操作中的处理器行为受到限制和修改，以便于虚拟化。那些指令（包括新的VMCALL指令）和事件会导致VM EXIT的发生，而不仅仅是他们原来的操作。由于这些VM Exit取代了普通行为，因此VMX non-root操作中的软件功能是有限制的。正是这种限制允许VMM保持对处理器资源的控制。
并不存在用于通知guest“是否处于VMX non-root”的寄存器。这一事实可以防止guest软件察觉它正在虚拟机中运行。
因为VMX操作对(CPL)Level 0做了限制，guest的软件可以在最初设计的权限级别运行。这样就可以简化VMM的开发。

### 23.4 VMM软件的生命周期
图23-1说明了VMM及其客户软件的生命周期以及它们之间的交互。以下项目总结了生命周期：
![](figure23-1.png)

- 软件通过执行VMXON指令进入VMX操作
- 使用VM entry，VMM可以执行guest，一次一个。
- VMM通过使用VMLAUNCH和VMRESUME指令干预虚拟机。通过VM EXIT，VMM重新获得控制权。
- VM移交控制权到VMM指定的入口点。VMM可以采取适当的措施使得VM exit发生，然后可以使用VM entry返回到虚拟机。
- 最终，VMM可以通过执行VMXOFF自行决定关闭并离开VMX操作。

### 23.5虚拟机控制结构
VMX non-root的操作以及VMX转换由名为“虚拟机控制”(VMCS)的数据结构控制。
通过VMCS指针(每个逻辑CPU一个)来管理对VMCS的访问。VMCS指针的值是64位地址。读取和写入VMCS指针使用指令VMPTRST和VMPTRLD。并且VMM使用VMREAD，VMWRITE和VMCLEAR指令来配置VMCS。
VMM可以为其支持的每个虚拟机使用不同的VMCS。对于具有多个的虚拟机在逻辑处理器（虚拟处理器）中，VMM可以为每个虚拟处理器使用不同的VMCS。

### 23.6 发现对VMX的支持
在系统软件进入VMX操作之前，它必须检查处理器中是否存在VMX支持。系统软件可以使用CPUID确定处理器是否支持VMX操作。如果`CPUID.1：ECX.VMX [bit 5] = 1`那么当前平台支持VMX操作。请参见第3章“指令集参考，A-L”英特尔®64和IA-32架构软件开发人员手册，第2A卷。
VMX体系结构旨在实现可扩展性，以便VMX操作中的未来处理器可以支持VMX体系结构的第一代实现中不存在的其他功能。使用一组VMX功能MSR向软件报告可扩展VMX功能的可用性（参见附录A，“VMX功能”)。

### 23.7启用和进入VMX操作
在系统软件进入VMX操作之前，它通过设置`CR4.VMXE [bit 13] = 1` VMX操作来启用VMX。然后通过执行VMXON指令进入。当'CR4.VMXE = 0'时，如果执行指令VMXON会导致无效操作码异常（#UD)；一旦执行过VMX操作，就无法清除CR4.VMXE（参见第23.8节）。系统软件通过执行VMXOFF指令离开VMX操作。执行VMXOFF后，可以在VMX操作之外清除CR4.VMXE。
VMXON也由IA32_FEATURE_CONTROL MSR（MSR地址3AH）控制。该MSR清零重置逻辑处理器时MSR的相关位是：
- 位0是锁定位。如果该位清零，则VMXON会导致general-protection异常。如果设置了锁定位，WRMSR到此MSR会导致general-protection异常;在上电复位之前，不能修改MSR。系统BIOS可以使用此位为BIOS提供设置选项以禁用对VMX的支持。在平台中启用VMX支持，BIOS必须设置位1或者位2或两者（见下文）以及锁定位。
- 位1在SMX操作中启用VMXON。如果该位清零，则在SMX操作中执行VMXON会导致general-protection expection。尝试在不支持两个VMX的逻辑处理器上设置此位操作（参见第23.6节）和SMX操作（参见英特尔®中的第6章“安全模式扩展参考”第2D卷）导致general-proction异常。
- 位2在SMX操作之外启用VMXON。如果该位清零，则在SMX外部执行VMXON操作会导致general-proction异常。尝试在没有的逻辑处理器上设置此位支持VMX操作（参见第23.6节）导致general-proction异常。

在执行VMXON之前，软件应该分配一个逻辑上自然对齐的4 KB内存区域,处理器可用于支持VMX操作.1该区域称为VMXON region。VMXON zone的地址区域（VMXON指针）在VMXON的操作数中提供。第24节

### 23.8 VMX操作限制
（作者：限制还有很有一些的，暂且不一一列举了吧，这里挑1-2点）
- 当逻辑处理器在VMX root操作时，中断信号是被block的。但当在VMX non-root模式的时候，不会被block，相反中断信号会触发VM exit。


### 24.1 虚拟机控制结构(VMCS)
逻辑处理器在VMX操作中使用"虚拟机控制结构"（VMCS）。这些管理VMX进出非root与root操作（VM entry和VM exit）以及处理器在VMX non-root时的行为。这个结构由新指令VMCLEAR，VMPTRLD，VMREAD, VMWRITE操纵。
VMM可以为其支持的每个虚拟机使用不同的VMCS。对于具有多个的虚拟机在逻辑处理器（虚拟处理器）中，VMM可以为每个虚拟处理器使用不同的VMCS。
逻辑处理器将存储器中的区域与每个VMCS相关联。该区域称为VMCS region。软件使用区域的64位物理地址（VMCS指针）引用特定VMCS。 VMCS指针必须在4 KB边界上对齐（位11：0必须为零）。这些指针不能设置超出理器的物理地址宽度。
逻辑处理器可以维护多个活动的VMCS。处理器通过维护内存中活跃VMCS的状态来优化VMX操作。在任何给定时间，最多一个活动VMCS的数量是当前VMCS。 （本文档经常使用术语“VMCS”来指代当前VMCS。）VMLAUNCH，VMREAD，VMRESUME和VMWRITE指令仅对当前操作VMCS。
以下各项描述了逻辑处理器如何确定哪些VMCS处于活动状态以及哪些VMCS处于当前状态：
- VMPTRLD指令的内存操作数是VMCS的地址。执行完指令后VMCS在逻辑处理器上既是活动的和也是当前的。任何其他活动的VMCS都不是当前VMCS。
- VMCS中的VMCS链接指针字段（参见第24.4.2节）本身就是VMCS的地址。如果VM entry正确执行了，并且“VMCS shadow”VM执行控制（VMCS）的1设置成功，那么VMCS链接指针字段引用的字符在逻辑处理器上变为活动状态。当前VMCS不会改变。
- VMCLEAR指令的内存操作数也是VMCS的地址。执行完毕后指令，VMCS在逻辑处理器上既不是活动的也不是当前的。如果VMCS已经开启逻辑处理器，逻辑处理器不再具有当前的VMCS。

VMPTRST指令将逻辑处理器的当前VMCS的地址存储到指定的存储器位置（如果没有当前的VMCS，则存储值FFFFFFFF_FFFFFFFFH）。
VMCS的启动状态确定哪个VM-entry指令应该与该VMCS一起使用：VMLAUNCH指令需要VMCS，其启动状态为“清除”; VMRESUME指令需要VMCS，其发射状态是“发射”。逻辑处理器在相应的VMCS中维护VMCS的启动状态区域。以下各项描述了逻辑处理器如何管理VMCS的启动状态：
- 如果当前VMCS的启动状态为“clear”，则VMLAUNCH指令的成功执行会发生变化发射状态为“launched”。
- VMCLEAR指令的内存操作数是VMCS的地址。执行完指令后VMCS的启动状态是“clear”。
- 没有其他方法可以修改VMCS的启动状态（无法使用VMWRITE进行修改）也没有直接的方法来发现它（它无法使用VMREAD读取）

图24-1说明了VMCS的不同状态。它使用“X”表示VMCS，使用“Y”表示任何其他VMCS。因此：“VMPTRLD X”总是使得VMCS变为当前和活动状态; “VMPTRLD Y”让X不再是当前状态（因为它使Y变为当前状态）;如果X是当前的并且其启动状态时，则VMLAUNCH的会将X变为“launched"; VMCLEAR X总是使X处于非活动状态而不是当前状态，并使其启动状态“clear”。
该图未示出相对于这些参数不修改VMCS状态的操作（例如，当X已经是当前时执行VMPTRLD X）。请注意，VMCLEAR X使X“处于非活动状态，非当前状态，并且clear。即使X的当前状态未定义（例如，即使X尚未初始化）。见24.11.3节。
由于影子VMCS（请参阅第24.10节）不能用于VM条目，因此影子VMCS的启动状态为没有意义。图24-1未说明可以使影子VMCS处于活动状态的所有方式。
![](figure24-1.png)

### 24.2 VMCS Region的格式
VMCS的格式包含了4K，VMCS的格式如表24-1

|byte offside | 内容|
|------|------|
|0|0~30位 VMCS保留，识别符<br>31位: shadow-VMCS标识位|
|4|VMCS终止位|
|8|VMCS 数据|

VMCS区域的前4个字节包含位30：0的VMCS修订标识符。维护的处理器不同格式的VMCS数据（见下文）使用不同的VMCS修订标识符。位31：shadow-VMCS指标（参见第24.10节）

在将该区域用于VMCS之前，软件应将VMCS标识符写入VMCS区域。该VMCS标识符永远不会被处理器写入;如果VMPTRLD的操作数引用VMCS区域的标识符与处理器正在使用的VMCS不同，则VMPTRLD会失败。 （如果是影子VMCS，并且处理器不支持shadow-VMCS，那么VMPTRLD也会失败）软件可以通过读取VMX相关MSR IA32_VMX_BASIC来检查处理器VMCS标识符。
软件应根据VMCS是否为普通还是shadow-vmcs来设置或者清楚shadow-VMCS标识符.不支持“VMCS阴影”VM执行控件的1设置。软件可以通过读取VMX功能MSR IA32_VMX_PROCBASED_CTLS2来检查是否支持。
VMCS区域的接下来的4个字节用于VMX中止指示符。这些位的内容没有控制处理器。当VMX中止发生时，逻辑处理器将非零值写入这些位。软件也可以写入此字段。
VMCS区域的其余部分用于VMCS数据（控制VMX non-root操作以及VMX转换）。这些数据的格式是特定的。写回可缓存内存中的VMCS区域和相关结构（在第24.11.4节中列举）。未来实现可以允许或要求不同的存储器类型。软件应参考VMX功能MSR
IA32_VMX_BASIC（见附录A.1）

未完待续…… 


