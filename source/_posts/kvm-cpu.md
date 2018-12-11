---
title: KVM 虚拟化原理3--CPU
donate: true
date: 2018-12-10 23:16:24
categories: KVM
tags: KVM
---
## CPU 虚拟化简介

上一篇文章笼统的介绍了一个虚拟机的诞生过程，从demo中也可以看到，运行一个虚拟机再也不需要像以前想象的那样，需要用软件来模拟硬件指令集了。虚拟机的指令集直接运行在宿主机物理CPU上，当虚拟机中的指令设计到IO操作或者一些特殊指令的时候，控制权转让给了宿主机（这里其实是转让给了vm monitor，下面检查VMM），也就是一个demo进程，他在宿主机上的表现形式也就是一个用户级进程。

用一张图来解释更为贴切。

![](vcpu-follow.png)

VMM完成vCPU，内存的初始化后，通过ioctl调用KVM的接口，完成虚拟机的创建，并创建一个线程来运行VM，由于VM在前期初始化的时候会设置各种寄存器来帮助KVM查找到需要加载的指令的入口（main函数）。所以线程在调用了KVM接口后，物理CPU的控制权就交给了VM。VM运行在VMX non-root模式，这是Intel-V或者AMD-V提供的一种特殊的CPU执行模式。然后当VM执行了特殊指令的时候，CPU将当前VM的上下文保存到VMCS寄存器（这个寄存器是一个指针，保存了实际的上下文地址），然后执行权切换到VMM。VMM 获取 VM 返回原因，并做处理。如果是IO请求，VMM 可以直接读取VM的内存并将IO操作模拟出来，然后再调用VMRESUME指令，VM继续执行，此时在VM看来，IO操作的指令被CPU执行了。

## Intel-V 技术

Intel-V 技术是Intel为了支持虚拟化而提供的一套CPU特殊运行模式。

### Intel-V虚拟化技术结构

Intel-V 在IA-32处理器上扩展了处理器等级，原来的CPU支持ring0~ring3 4个等级，但是Linux只使用了其中的两个ring0,ring3。当CPU寄存器标示了当前CPU处于ring0级别的时候，表示此时CPU正在运行的是内核的代码。而当CPU处于ring3级别的时候，表示此时CPU正在运行的是用户级别的代码。当发生系统调用或者进程切换的时候，CPU会从ring3级别转到ring0级别。ring3级别是不允许执行硬件操作的，所有硬件操作都需要系统提供的API来完成。  
比如说一个IO操作：

```hljs
int nread = read(fd, buffer, 1024);
```

当执行到此段代码的时候，然后查找到系统调用号，保存到寄存器eax，然后会将对应的参数压栈后产生一个系统调用中断，对应的是 int $0x80。产生了系统调用中断后，此时CPU将切换到ring0模式，内核通过寄存器读取到参数，并完成最后的IO后续操作，操作完成后返回ring3模式。

```hljs
movel　　$3,%eax
movel　　fd,%ebx
movel　　buffer,%ecx
movel　　1024,%edx　　　　　　
int　　  $0x80
```

Intel-V 在 ring0~ring3 的基础上，增加了VMX模式，VMX分为root和non-root。这里的VMX root模式是给VMM（前面有提到VM monitor)，在KVM体系中，就是qemu-kvm进程所运行的模式。VMX non-root模式就是运行的Guest，Guest也分ring0~ring3，不过他并不感知自己处于VMX non-root模式下。

![](vcpu-ring.png)

Intel的虚拟架构基本上分两个部分:

* 虚拟机监视器
* 客户机（Guest VM)

#### 虚拟机监视器（Virtual-machine monitors - VMM)

虚拟机监视器在宿主机上表现为一个提供虚拟机CPU，内存以及一系列硬件虚拟的实体，这个实体在KVM体系中就是一个进程，如qemu-kvm。VMM负责管理虚拟机的资源，并拥有所有虚拟机资源的控制权，包括切换虚拟机的CPU上下文等。

#### Guest

这个Guest在前面的Demo里面也提到，可能是一个操作系统（OS），也可能就是一个二进制程序，whatever，对于VMM来说，他就是一堆指令集，只需要知道入口（rip寄存器值）就可以加载。  
Guest运行需要虚拟CPU，当Guest代码运行的时候，处于VMX non-root模式，此模式下，该用什么指令还是用什么指令，该用寄存器该用cache还是用cache，但是在执行到特殊指令的时候（比如Demo中的out指令），把CPU控制权交给VMM，由VMM来处理特殊指令，完成硬件操作。

#### VMM 与 Guest 的切换

![](vmm_guest_switch.png)

Guest与VMM之间的切换分两个部分：VM entry 和 VM exit。有几种情况会导致VM exit，比如说Guest执行了硬件访问操作，或者Guest调用了VMCALL指令或者调用了退出指令或者产生了一个page fault，或者访问了特殊设备的寄存器等。当Guest处于VMX模式的时候，没有提供获取是否处于此模式下的指令或者寄存器，也就是说，Guest不能判断当前CPU是否处于VMX模式。当产生VM exit的时候，CPU会将exit reason保存到MSRs（VMX模式的特殊寄存器组），对应到KVM就是vCPU->kvm_run->exit_reason。VMM根据exit_reason做相应的处理。

#### VMM 的生命周期

如上图所示，VMM 开始于VMXON 指令，结束与VMXOFF指令。  
第一次启动Guest，通过VMLAUNCH指令加载Guest，这时候一切都是新的，比如说起始的rip寄存器等。后续Guest exit后再entry，是通过VMRESUME指令，此指令会将VMCS(后面会介绍到）所指向的内容加载到当前Guest的上下文，以便Guest继续执行。

#### VMCS （Virtual-Machine control structure)

顾名思义，VMCS就是虚拟机控制结构，前面提到过很多次，Guest Exit的时候，会将当前Guest的上下文保存到VMCS中，Guest entry的时候把VMCS上下文恢复到VMM。VMCS是一个64位的指针，指向一个真实的内存地址，VMCS是以vCPU为单位的，就是说当前有多少个vCPU，就有多少个VMCS指针。VMCS的操作包括VMREAD，VMWRITE，VMCLEAR。

#### Guest exit Reason

下面是qemu-kvm定义的exit reason。可以看到有很多可能会导致Guest转让控制权。选取几个解释一下。

```hljs
static int (*const kvm_vmx_exit_handlers[])(struct kvm_vcpu *vcpu) = {
    [EXIT_REASON_EXCEPTION_NMI]           = handle_exception, 
    [EXIT_REASON_EXTERNAL_INTERRUPT]      = handle_external_interrupt, 
    [EXIT_REASON_TRIPLE_FAULT]            = handle_triple_fault,
    [EXIT_REASON_NMI_WINDOW]              = handle_nmi_window,
     // 访问了IO设备
    [EXIT_REASON_IO_INSTRUCTION]          = handle_io,
     // 访问了CR寄存器，地址寄存器，和DR寄存器（debug register)一样，用于调试
    [EXIT_REASON_CR_ACCESS]               = handle_cr,
    [EXIT_REASON_DR_ACCESS]               = handle_dr, 
    [EXIT_REASON_CPUID]                   = handle_cpuid,
    // 访问了MSR寄存器
    [EXIT_REASON_MSR_READ]                = handle_rdmsr,
    [EXIT_REASON_MSR_WRITE]               = handle_wrmsr,
    [EXIT_REASON_PENDING_INTERRUPT]       = handle_interrupt_window,
    // Guest执行了HLT指令，Demo开胃菜就是这个指令
    [EXIT_REASON_HLT]                     = handle_halt,
    [EXIT_REASON_INVD]                    = handle_invd,
    [EXIT_REASON_INVLPG]                  = handle_invlpg,
    [EXIT_REASON_RDPMC]                   = handle_rdpmc,
    // 不太清楚以下VM系列的指令有什么用，猜测是递归VM（虚拟机里面运行虚拟机）
    [EXIT_REASON_VMCALL]                  = handle_vmcall, 
    [EXIT_REASON_VMCLEAR]                 = handle_vmclear,
    [EXIT_REASON_VMLAUNCH]                = handle_vmlaunch,
    [EXIT_REASON_VMPTRLD]                 = handle_vmptrld,
    [EXIT_REASON_VMPTRST]                 = handle_vmptrst,
    [EXIT_REASON_VMREAD]                  = handle_vmread,
    [EXIT_REASON_VMRESUME]                = handle_vmresume,
    [EXIT_REASON_VMWRITE]                 = handle_vmwrite,
    [EXIT_REASON_VMOFF]                   = handle_vmoff,
    [EXIT_REASON_VMON]                    = handle_vmon,

    [EXIT_REASON_TPR_BELOW_THRESHOLD]     = handle_tpr_below_threshold,
    // 访问了高级PCI设备
    [EXIT_REASON_APIC_ACCESS]             = handle_apic_access,
    [EXIT_REASON_APIC_WRITE]              = handle_apic_write,
    [EXIT_REASON_EOI_INDUCED]             = handle_apic_eoi_induced,
    [EXIT_REASON_WBINVD]                  = handle_wbinvd,
    [EXIT_REASON_XSETBV]                  = handle_xsetbv,
    // 进程切换
    [EXIT_REASON_TASK_SWITCH]             = handle_task_switch,
    [EXIT_REASON_MCE_DURING_VMENTRY]      = handle_machine_check,
    // ept 是Intel的一个硬件内存虚拟化技术
    [EXIT_REASON_EPT_VIOLATION]           = handle_ept_violation,
    [EXIT_REASON_EPT_MISCONFIG]           = handle_ept_misconfig,
    // 执行了暂停指令
    [EXIT_REASON_PAUSE_INSTRUCTION]       = handle_pause,
    [EXIT_REASON_MWAIT_INSTRUCTION]       = handle_invalid_op,
    [EXIT_REASON_MONITOR_INSTRUCTION]     = handle_invalid_op,
    [EXIT_REASON_INVEPT]                  = handle_invept,
};
```

## 总结

KVM的CPU虚拟化依托于Intel-V提供的虚拟化技术，将Guest运行于VMX模式，当执行了特殊操作的时候，将控制权返回给VMM。VMM处理完特殊操作后再把结果返回给Guest。  
CPU虚拟化可以说是KVM的最关键的核心，弄清楚了VM Exit和VM Entry。后续的IO虚拟化，内存虚拟化都是建立在此基础上。下一章介绍内存虚拟化。
