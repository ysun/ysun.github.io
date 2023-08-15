---
title: xsave 寄存器
donate: true
date: 2023-08-06 17:39:17
categories:
tags:
---
最近研究了下xsaves指令，发现国内中文内容XSAVE(s)相关的太少了。这里简单记一下心得和笔记吧。

总的来说，XSAVE 和 XSAVES 指令的引入是为了支持更复杂的处理器状态，并在多任务环境中实现高效的上下文切换。随着处理器技术的发展，Intel 和 AMD 都引入了许多新的特性和扩展，例如浮点单位、SIMD 扩展（如 MMX、SSE 和 AVX）以及其他功能（如 MPX 和 SGX）。这些扩展和特性增加了处理器的状态大小，意味着传统的上下文保存和恢复机制（如使用 FXSAVE 和 FXRSTOR 指令）不再足够。需要一种高效的方式来保存和恢复处理器状态。
XSAVE 允许更灵活地保存和恢复处理器状态。它引入了一个新的数据结构，该结构可以容纳各种处理器状态组件。XSAVE 还支持功能掩码(RFBM/XINUSE)，允许操作系统选择要保存和恢复的状态组件。
尽管 XSAVE 增强了上下文切换的能力，但随着处理器状态的进一步增加，还需要进一步的优化。XSAVES 和 XSAVEC 被设计为 XSAVE 的扩展，提供了更紧凑和高效的保存格式。 特别是，XSAVES 提供了对 SGX 和 MPX 的支持，并为未来的处理器特性提供了兼容性。
与 XSAVE 和 XSAVES 相伴而来的还有其他相关指令，例如 XRSTOR, XRSTORS, XSAVEOPT 等。

SIMD扩展的寄存器的长度经过多年的发展，不同指令大概这样:
![](xsave.svg)

* SSE (Streaming SIMD Extensions):
1990 年代末，多媒体应用程序（如视频解码、图形渲染等）的需求日益增加。为了满足这些应用程序对性能的需求，Intel 提出了 SIMD (Single Instruction, Multiple Data) 的概念，即用单一指令同时处理多个数据项。
SSE 指令集首次出现在 1999 年的 Pentium III 处理器中，随后是SSE2（Pentium 4）, SSE3（Pentium 4）, SSSE3(Core 2 Due), SSE4（Penryn 和 Nehalem）, 持续到2008年。

* AVX (Advanced Vector Extensions):
2000 年代末，随着科学计算和数据分析需求的增加，需要更大的数据向量和更多的并行性。为此，Intel 引入了 AVX 指令集，它提供了 256 位宽的向量寄存器，这比 SSE 的 128 位宽的寄存器长度翻倍了。AVX 指令集首次出现在 2011 年的 Sandy Bridge 架构的处理器中。

* AVX2 和 AVX-512:
随着对更高性能的需求，Intel 又引入了 AVX2 和 AVX-512 扩展。AVX2 增加了新的整数指令和256位宽的整数向量。而 AVX-512 增加了 512 位宽的向量寄存器。
AVX2: 2013 年，与 Haswell 架构的处理器一同推出。
AVX-512: 2016 年，首次出现在 Xeon 和后续的 Skylake-SP 处理器中。

XSAVE指令扩展了FXSAVE使用的格式，以包括附加寄存器集合。然而，与早期保存指令不同，它并不严格限于固定数据集。相反，它使得在不需要添加下一个XSAVE变体或破坏与现有软件兼容性的情况下引入对新CPU扩展支持成为可能。XSAVE围绕状态组件的概念展开。状态组件表示可以独立保存或恢复的单个数据子集。有两个特殊的状态组件对应于原始FXSAVE指令：x86状态组件和SSE状态组件。

在现代处理器中，有两种状态组件：用户状态组件和内核状态组件。前者组表示对用户空间程序可访问的常规寄存器，后者涉及不应暴露给常规程序的特权寄存器。

通过状态组件位图来控制各个状态组件。这个位图由XSAVE用来确定要保存哪些指令集，由XRSTOR用来确定要从这个区域恢复（位设置）还是重置为默认状态（位清除）。启用相应的位会导致将附加数据保存到内存中，从而有效地需要更大的存储区域。
![](bitmap.png)

为了使得保存特定状态组件或在程序中使用相应寄存器成为可能，内核需要在其中一个控制寄存器中启用其跟踪。这些控制寄存器是XCR0用于用户组件，IA32_XSS用于监督者组件。⁷[7]两者都使用与状态组件位图相同的位数。

XSAVE指令使用的数据格式称为XSAVE区域。XSAVE区域由三部分组成：与FXSAVE指令相同的512字节遗留区域，后跟包含有关XSAVE区域中存在的数据信息的64字节XSAVE头，后跟用于存储附加状态组件的可变大小扩展区域。

XSAVE头当前包含两个64位字段，其值对应于状态组件位图：XSTATE_BV和XCOMP_BV。⁹[9]XSTATE_BV由XSAVE写入，以指示特定状态组件已写入扩展区域，并由XRSTOR读取，以确定该组件是否要从该区域恢复（位设置）或重置为默认状态（位清除）。

## 调用
在调用 XSAVE 指令集族中的任何指令之前，需要进行一些简单的步骤，简短地列一下。

首先，需要通过 CPUID 验证指令的支持。
其次，需要启用状态跟踪。就是说在 XCR0 中为用户状态组件设置适当的状态组件位，并在 IA32_XSS 中为suppervisor状态组件设置。还需要在控制寄存器 CR4 中设置适当的 XSAVE 位。所有这些操作都由内核完成。
第三，需要获得足够大的 XSAVE 区域的缓冲区。程序应使用 CPUID 指令来获得所需的大小。缓冲区需要对齐到 64 字节。通常，首先将缓冲区置零可能很方便，这样可以避免需要小心，例如，XSAVE 使未使用的 XSTATE_BV 字节保持不变。
最后，需要将请求的状态组件位图放入寄存器对 EDX:EAX（高 32 位放入 EDX，低 32 位放入 EAX — 这是一个常见的 i386 用于 64 位整数的约定）。完成此操作后，可以调用 XSAVE。
之后，需要进行另一系列的 CPUID 调用，以获得偏移量或大小以及处理 XSAVE 区域内容的对齐要求。

下面的列表展示了一个简单的程序，该程序三次调用 XSAVE，每次都修改了不同的寄存器集。

```c
#include <assert.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>

struct xsave {
    uint8_t legacy_area[512];
    union {
        struct {
            uint64_t xstate_bv;
            uint64_t xcomp_bv;
        };
        uint8_t header_area[64];
    };
    uint8_t extended_area[];
};

int main() {
    uint32_t buf_size = 0;
    uint32_t avx_offset = 0;
    uint8_t avx_bytes[32];
    struct xsave* buf[3];
    int i;
    for (i = 0; i < sizeof(avx_bytes); ++i)
        avx_bytes[i] = i;

    __asm__ __volatile__ (
        /* check CPUID support for XSAVE and AVX */
        "mov $0x01, %%eax\n\t"
        "cpuid\n\t"
        "mov $0x04000000, %%eax\n\t"  /* bit 26 - XSAVE */
        "and %%ecx, %%eax\n\t"
        "jz .cpuid_end\n\t"
        "mov $0x10000000, %%eax\n\t"  /* bit 28 - AVX */
        "and %%ecx, %%eax\n\t"
        "jz .no_avx\n\t"
        /* get AVX offset */
        "mov $0x0d, %%eax\n\t"
        "mov $0x02, %%ecx\n\t"
        "cpuid\n\t"
        "mov %%ebx, %1\n\t"
        "\n"
        ".no_avx:\n\t"
        /* get XSAVE area size for current XCR0 */
        "mov $0x0d, %%eax\n\t"
        "xor %%ecx, %%ecx\n\t"
        "cpuid\n\t"
        "mov %%ebx, %0\n\t"
        "\n"
        ".cpuid_end:\n\t"
        : "=m"(buf_size), "=m"(avx_offset)
        :
        : "%eax", "%ebx", "%ecx", "%edx"
    );

    if (buf_size == 0) {
        printf("no xsave support\n");
        return 1;
    }

    printf("has avx: %s\n", avx_offset != 0 ? "yes" : "no");
    printf("xsave area size: %d bytes\n", buf_size);

    for (i = 0; i < 3; ++i) {
        buf[i] = aligned_alloc(64, buf_size);
        assert(buf[i]);
    }

    __asm__ __volatile__ (
        "mov $0x07, %%eax\n\t"
        "xor %%edx, %%edx\n\t"
        "xsave (%0)\n\t"
        "movd %%eax, %%mm0\n\t"
        "xsave (%1)\n\t"
        "and %3, %3\n\t"
        "jz .xsave_end\n\t"
        "vmovups (%3), %%ymm0\n\t"
        "xsave (%2)\n\t"
        "\n"
        ".xsave_end:\n\t"
        :
        : "r"(buf[0]), "r"(buf[1]), "r"(buf[2]),
          "c"(avx_offset != 0 ? avx_bytes : 0)
        : "%eax", "%edx", "%mm0", "%ymm0", "memory"
    );

    printf("XSTATE_BV (initial): %#018" PRIx64 "\n",
           buf[0]->xstate_bv);
    printf("XSTATE_BV (with MMX): %#018" PRIx64 "\n",
           buf[1]->xstate_bv);
    if (avx_offset != 0) {
        printf("XSTATE_BV (with AVX): %#018" PRIx64 "\n",
               buf[2]->xstate_bv);
        printf("YMM0 most significant quadword: %#018" PRIx64 "\n",
               *((uint64_t*)(((char*)buf[2]) + avx_offset)));
    }

    for (i = 0; i < 3; ++i)
        free(buf[i]);
    return 0;
}
```

使用gcc直接编译就可以执行了，在我的测试机上结果这样：
```bash
has avx: yes
xsave area size: 2688 bytes
XSTATE_BV (initial): 0x0000000000000002
XSTATE_BV (with MMX): 0x0000000000000003
XSTATE_BV (with AVX): 0x0000000000000007
YMM0 most significant quadword: 0x1716151413121110
```
