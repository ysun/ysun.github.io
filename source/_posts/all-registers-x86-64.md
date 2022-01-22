---
title: X86_64 机器上一共有多少个寄存器
donate: true
date: 2021-12-26 23:01:32
categories: X86
tags: x86
---

玩了这么久的Intel CPU，今天一个问题忽然闪现在我脑海：“X86_64到底有多少个寄存器”？ 带着知识的渴求，我们来掰一下手指头。

## 通用寄存器 (general register)

通用寄存器(general-purpose registers, GPRs) 可能是读书是最早接触的寄存器。每一个用户空间的程序，或者内核程序都用到的，基本的寄存器。
因为X86-64是从32位的X86，甚至16位、8位演变而来的，为了软件可以向前兼容，所以，这些寄存器都有不同的版本。话不多说，看下表：

64-bit | 32-bit | 16-bit | 8-bit (low)
------ | ------ | ------ | -----------
RAX    | EAX    | AX     | AL         
RBX    | EBX    | BX     | BL         
RCX    | ECX    | CX     | CL         
RDX    | EDX    | DX     | DL         
RSI    | ESI    | SI     | SIL        
RDI    | EDI    | DI     | DIL        
RBP    | EBP    | BP     | BPL        
RSP    | ESP    | SP     | SPL        
R8     | R8D    | R8W    | R8B        
R9     | R9D    | R9W    | R9B        
R10    | R10D   | R10W   | R10B       
R11    | R11D   | R11W   | R11B       
R12    | R12D   | R12W   | R12B       
R13    | R13D   | R13W   | R13B       
R14    | R14D   | R14W   | R14B       
R15    | R15D   | R15W   | R15B       

其中，16位的寄存器中的AX, BX, CX, DX 可以高低位分别访问，所以又增加4个

16-bit | 8-bit (high)
------ | ------------
AX     |  AH         
BX     |  BH         
CX     |  CH         
DX     |  DH         


**通用寄存器总共: 68**.

**到目前为止一共: 68**.


## 特殊寄存器 (Special registers)

* 指针寄存器(_instruction pointer_, `RIP`.)
X86-64的RIP可以切分成32位的EIP 和 16位IP，但他们不可以同时使用，所以这里不重复计数。

* 状态寄存器(_status register_, `RFLAGS`)
就像上面的RIP一样，RFLAGS也有32位和16位版本，分别是EFLAGS 和 FLAGS，但不同的是PUSHF 和 PUSHFQ可以在`长模式`下同时使用，以及LAHF 和 SAHF可以同时在一个CPU上使用，这里计数。

**本部分寄存器总共: 4**.

**到目前为止一共: 72**.

## 段寄存器 (Segment registers)

X86-64一共有6个段寄存器: `CS`, `SS`, `DS`, `ES`, `FS`, and `GS`。

* 除了`长模式`以外的所有CPU运行模式里，都有一个段`选择器 selector`, 表示当前使用[GDT](https://en.wikipedia.org/wiki/Global_Descriptor_Table) 还是 [LDT](https://en.wikipedia.org/wiki/Global_Descriptor_Table#Local_Descriptor_Table)。 同时，还需要一个`段描述符descriptor`, 提供了段的基址和范围。

* `长模式`中，除了 FS 和 GS 之外的所有内容都被视为在一个具有零基地址和64位范围的平面地址空间中。 FS 和 GS 作为特殊情况保留，但不再使用段描述符表，取而代之的是，访问保存在 FSBASE 和 GSBASE 中的MSR寄存器中的基地址。

**本部分寄存器总共: 6**.

**到目前为止一共: 78**.

## 单指令多数据SIMD 和浮点运算指令FP

X86家族经历了几代 SIMD 和浮点指令，每一代都引入、扩展或重新定义各种各样的指令：
* x87
* MMX
* SSE (SSE2, SSE3, SSE4, SSE4, …)
* AVX (AVX2, AVX512)
* AMX

### x87

X87最初是一个独立的协处理器，有自己的指令集和寄存器，从80486开始，x87指令就经常被植入x86内核本身。
由于其协处理器的历史，x87定义了正常的寄存器（类似于GPR）和控制FPU状态所需的各种特殊寄存器。
* ST0到ST7：8个80位浮点寄存器
* FPSW, FPCW, FPTW 7：控制、状态和标签字寄存器
* "数据操作数指针Data operand pointer"。我不知道这个是做什么的，但英特尔SDM规定了它
* 指令指针Instruction pointer：x87状态机显然持有它自己的当前x87指令的拷贝。
* 最后一条指令的操作码Last instruction opcode：与x87操作码不同，并且有它自己的寄存器。

**本部分寄存器总共: 14**.

**到目前为止一共: 92**.

### MMX

MMX是Intel在X86芯片上添加SIMD指令的第一次尝试，发布于1997年。MMX寄存器实际上是x87 STn寄存器的子集。每个64位MMn占用其相应STn的尾数部分。因此，x86（和x86-64）CPU不能同时执行MMX和x87指令。
MMX定义了MM0到MM7，8个寄存器，另外还有一个新的状态寄存器（MXCSR），以及用于操作它的加载/存储指令对（LDMXCSR和STMXCSR）。

**本部分寄存器总共: 9**.

**到目前为止一共: 101**.

### SSE and AVX

为了简单起见，我打算把SSE和AVX包成一个部分：它们使用与GPR和x87/MMX相同的子寄存器模式，所以放在一个表中。

AVX-512 (512-bit) | AVX-2 (256-bit) | SSE (128-bit)
----------------- | --------------- | -------------
ZMM0              | YMM0            | XMM0         
ZMM1              | YMM1            | XMM1         
ZMM2              | YMM2            | XMM2         
ZMM3              | YMM3            | XMM3         
ZMM4              | YMM4            | XMM4         
ZMM5              | YMM5            | XMM5         
ZMM6              | YMM6            | XMM6         
ZMM7              | YMM7            | XMM7         
ZMM8              | YMM8            | XMM8         
ZMM9              | YMM9            | XMM9         
ZMM10             | YMM10           | XMM10        
ZMM11             | YMM11           | XMM11        
ZMM12             | YMM12           | XMM12        
ZMM13             | YMM13           | XMM13        
ZMM14             | YMM14           | XMM14        
ZMM15             | YMM15           | XMM15        
ZMM16             | YMM16           | XMM16        
ZMM17             | YMM17           | XMM17        
ZMM18             | YMM18           | XMM18        
ZMM19             | YMM19           | XMM19        
ZMM20             | YMM20           | XMM20        
ZMM21             | YMM21           | XMM21        
ZMM22             | YMM22           | XMM22        
ZMM23             | YMM23           | XMM23        
ZMM24             | YMM24           | XMM24        
ZMM25             | YMM25           | XMM25        
ZMM26             | YMM26           | XMM26        
ZMM27             | YMM27           | XMM27        
ZMM28             | YMM28           | XMM28        
ZMM29             | YMM29           | XMM29        
ZMM30             | YMM30           | XMM30        
ZMM31             | YMM31           | XMM31        

换句话说：每个ZMMn的低字节部分是YMMn，而每个YMMn的低字节部分是XMMn。没有直接的寄存器可以只访问YMMn的高字节部分，或者ZMMn的高128位或者256位字部分。
SSE还定义了一个新的状态寄存器MXCSR，它包含的标志与RFLAGS中的算术标志大致平行（与x87状态字中的浮点标志一起）。
AVX-512还引入了8个OPMask寄存器，k0到k7。k0是一个特殊的情况，它的行为很像一些RISC ISA上的 "零 "寄存器：它不能被存储到，而且从它的加载总是产生一个全部为1的位掩码。

**本部分寄存器总共: 33**.

**到目前为止一共: 134**.

## 边界寄存器(Bounds registers)

英特尔在[MPX](https://en.wikipedia.org/wiki/Intel_MPX)中加入了BR，其目的是提供硬件加速的边界检查。但好像名声并不是很大，暂且放这里把。
BND0 - BND3：单独的128位寄存器，每个都包含一对绑定的地址。
BNDCFG: 绑定配置，内核模式。
BNDCFU: 绑定配置，用户模式。
BNDSTATUS: 绑定状态，在一个#BR被提出后。

**本部分寄存器总共: 7**.

**到目前为止一共: 141**.

## 调试寄存器(Debug registers)

正如他们的名字那样，帮助和加速软件调试器的寄存器，如GDB。
有6个调试寄存器，分为两种类型：
* DR0到DR3包含线性地址，每个地址都与一个断点条件相关。
* DR6和DR7是调试状态和控制寄存器。DR6的低位表示遇到了哪些调试条件（在进入调试异常处理程序时），而DR7控制哪些断点地址被启用以及它们的断点条件（例如，当某一地址被写入时）。
* 那么，DR4和DR5呢？不清楚! 但它们确实有编码，但分别被当做DR6和DR7，或者在CR4.DE[位3]=1时产生#UD异常。

**本部分寄存器总共: 6**.

**到目前为止一共: 147**.

## 控制寄存器 (Control registers)

x86-64 定义了一组控制寄存器，可用于管理和检查 CPU 的状态。有 16 个“主”控制寄存器，所有这些都可以通过[`MOV` variant](https://www.felixcloutier.com/x86/mov-1)变体访问:

Name | Purpose                       
---- | ------------------------------
CR0  | Basic CPU operation flags     
CR1  | Reserved                      
CR2  | Page-fault linear address     
CR3  | Virtual addressing state      
CR4  | Protected mode operation flags
CR5  | Reserved                      
CR6  | Reserved                      
CR7  | Reserved                      
CR8  | Task priority register (TPR)  
CR9  | Reserved                      
CR10 | Reserved                      
CR11 | Reserved                      
CR12 | Reserved                      
CR13 | Reserved                      
CR14 | Reserved                      
CR15 | Reserved                      

所有reserved的控制寄存器在访问时都会产生#UD，不把它们算在本文里。
除了 "主 "CRn控制寄存器之外，还有 "扩展 "控制寄存器，由XSAVE功能集引入。截至目前，XCR0是唯一指定的扩展控制寄存器。
扩展控制寄存器使用[`XGETBV`](https://www.felixcloutier.com/x86/xgetbv) 和 [`XSETBV`](https://www.felixcloutier.com/x86/xsetbv)而不是MOV的变种。

**本部分寄存器总共: 6**.

**到目前为止一共: 153**.

## “System table pointer registers”

这就是英特尔SDM对这些寄存器的称呼。这些寄存器保存着各种保护模式表的大小和指针。
据我所知，它们有四个：
* GDTR：存放GDT的大小和基址。
* LDTR：保存LDT的大小和基址。
* IDTR：保存IDT的大小和基址。
* TR：保存TSS的选择器和TSS的基址。

GDTR、LDTR和IDTR在64位模式下都是80位：16个低位是寄存器的表的大小，高64位是表的其实地址。
TR同样也是80位。16位用于选择器（其行为与段选择器相同），然后另外64位用于TSS的基本地址。

**本部分寄存器总共: 4**.

**到目前为止一共: 157**.

## Memory-type-ranger registers

这些是有趣的例子：与到目前为止所涉及的所有其他寄存器不同，这些不是多核芯片中某个特定CPU所独有的，相反，它们是所有内核共享的。
MTTR的数量似乎因CPU型号而异，并且在很大程度上被页中的所取代[page attribute table](https://en.wikipedia.org/wiki/Page_attribute_table)，该表是用MSR编程的。

**本部分寄存器总共: ?**.

**到目前为止一共: >157**.

## MSR Model specific registers

像XCR一样，MSR可以通过一对指令间接地（通过标识符）访问，RDMSR和WRMSR。
MSR本身是64位的，但起源于32位的时代，所以RDMSR和WRMSR从两个32位的寄存器中读取和写入。EDX和EAX。
举个例子：下面是访问IA32_MTRRCAP MSR的设置和RDMSR调用，其中包括（除其他外）系统上可用的MTRR的实际数量。

```
MOV ECX, 0xFE ; 0xFE = IA32_MTRRCAP
RDMSR  ; The bits of IA32_MTRRCAP are now in EDX:EAX
```
RDMSR和WRMSR是特权指令，所以Ring 3代码不能直接访问MSR。我知道的一个例外是时间戳计数器（TSC），它存储在IA32_TSC MSR中，但是可以通过RDTSC和RDTSCP从非特权上下文中读取。
另外两个是FSBASE和GSBASE，除非启用了 FSGSBASE 支持，否则可以直接从环 3 修改 FSBASE 和 GSBASE。Linux 在 5.9 中启用了 FSGSBASE。它们分别存储为IA32_FS_BASE和IA32_GS_BASE。正如在段寄存器部分所提到的，这些存储在x86-64 CPU上的FS和GS段基。这使得它们成为相对频繁使用的目标（根据MSR标准），所以它们有自己专门的R/W操作码。
* RDFSBASE和RDGSBASE用于读取
* WRFSBASE和WRGSBASE用于写入
但回到本文主题：有多少个MSR？ 我们从[SDM 335592-sdm-vol-4](335592-sdm-vol-4.pdf)中寻找答案。

许多MSRs已经从一代IA-32处理器延续到下一代，并延续到Intel 64处理器。MSR的一个子集和相关的位域，被认为是架构MSR。由于历史原因（从奔腾4处理器开始），这些 "架构性MSR "被赋予 "IA32_"的前缀。
根据SDM中的Table 2-2， 最高序号的MSR是6097/17D1H，即IA32_HW_FEEDBACK_CONFIG。
然而，在记录的MSR序号是存在着明显的洞。SDM直接从3506/DB2H（IA32_THREAD_STALL）跳到6096/17D0H（IA32_HW_FEEDBACK_PTR）。在空的范围之上，还有一些范围被明确地标记为保留的范围。
为了计算MSR的实际数量，只提取SDM第4卷中的[表2-2中的值](ia32-architectural-msrs.txt)。

* 解压缩 SDM
```
$ pdfjam 335592-sdm-vol-4.pdf 19-67 -o 2-2.pdf
```
* 利用pdftotext，把PDF转换为纯文本。
```
  $ pdftotext 2-2.pdf table.txt
  # edit table.txt by hand
```

* 使用 IA32_ 前缀，筛选字符串
```
  $ tr -s '[:space:]' '\n' < table.txt \
      | grep 'IA32_' \
      | tr -d '.' \
      | sed 's/\[.*$//' \
      | sort | uniq | wc -l
```

最后得到400个MSR，这要比6096合理多了。

**本部分寄存器总共: 400**.

**到目前为止一共: >557**.

## 参考

* [sandpile.org](https://sandpile.org/x86/msr.htm) MSR 可视化。
* Vol. 3A § 8.7.1 (“State of the Logical Processors”) of the Intel SDM has a useful list of
    nearly all of the registers that are either unique to or shared between x86-64 cores.
* The [OSDev Wiki](https://wiki.osdev.org/) has collection of helpful pages on various x86-64
    registers, including a [great page](https://wiki.osdev.org/SWAPGS) on the behavior of the segment
    base MSRs.

总而言之，在相对较新的x86-64 CPU内核上大约有557个寄存器。但一些我不确定的外设情况。
现代英特尔CPU使用集成的APICs作为其SMT实现的一部分。这些APICs有自己的寄存器库，可以被内存映射，以便由x86 CPU读取和潜在的修改。本文没有计算它们，因为(1)它们是内存映射的，因此表现得更像来自任意硬件的映射寄存器，而不是CPU寄存器
英特尔的SDM 说[Last Branch Records](https://lwn.net/Articles/680996/) 存储在离散的非MSR寄存器中，本文也没有单独计算这些。

https://blog.yossarian.net/2020/11/30/How-many-registers-does-an-x86-64-cpu-have
