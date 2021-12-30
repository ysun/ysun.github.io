---
title: 函数调用序列
donate: true
date: 2021-12-30 22:26:29
categories: x86
tags: X86
---

今天学到一个知识点[X86-64-ABI](https://gitlab.com/x86-psABIs/x86-64-ABI/-/jobs) pre-build [X86-64-ABI 下载地址](abi.pdf)
斗胆翻译下其中的3.2章节

本节介绍了标准的函数调用顺序，包括堆栈框架的布局、寄存器的使用、参数传递等等。标准调用顺序的要求只适用于全局函数。局部函数不能从其他编译单元访问，所以不尽相同。尽管如此，我们还是建议所有的函数在可能的情况下使用标准的调用顺序。

### 3.2.1 寄存器
AMD64架构提供16个通用的64位寄存器，16个SSE寄存器，每个128位宽，以及8个x87浮点寄存器，每个80位宽。每个x87浮点寄存器可以在MMX/3DNow！模式下被称为一个64位寄存器。所有这些寄存器对一个给定的线程的程序都是全局的。
还有16个256bit的 Intel AVX (Advanced Vector Extensions) provides 16 256-bit wide AVX registers (%ymm0 - %ymm15)， 32个Intel AVX-512 provides 512-bit wide SIMD registers (%zmm0 - %zmm31). 8个Intel AVX-512 also provides 8 vector mask registers (%k0 - %k7)。
还有Intel Advanced Matrix Extensions (Intel AMX) 8个 tile registers (%tmm0-%tmm7) 和 一个control 寄存器。

上面说了那么多重点来了：
** 只有寄存器 %rbp、%rbx 和 %r12 到 %r15“属于”调用函数并且被调用函数需要保留它们的值。** 换句话说，一个被调用的函数必须为调用函数保留这些寄存器的值。剩余的寄存器 "属于"被调用的函数。如果一个调用函数想在整个函数调用中保留这样的寄存器值，它必须在其本地堆栈框架中保存该值。注意，Intel386 ABI则不同，%rdi和%rsi属于被调用的函数，而不是调用者。

在进入一个函数时，CPU可以应处于x87模式。每个使用MMX寄存器的函数在使用MMX寄存器后，且在返回或调用另一个函数之前，都需要发出emms或femms指令。所有的x87寄存器都是调用者保存的，所以利用MMX寄存器的调用者可以使用更快的femms指令。

%rFLAGS寄存器中的方向标志DF在函数进入和返回时必须清零（设置为 "前进 "方向）。其他用户标志在标准调用序列中没有指定的作用，所以调用中不保留。

MXCSR寄存器的控制位是被调用函数保存的（跨调用保存），而状态位是调用者保存的。x87状态字寄存器是调用者保存的，而x87控制字是调用者保存的。

![register-usage.png](register-usage.png)

就先到这里把，后面还有一半 ** 寄存器的参数 ** 和 ** 返回值 ** 回头有时间再继续吧。
