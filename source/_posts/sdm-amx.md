---
title: Intel指令AMX_TMUL
donate: true
date: 2021-08-12 13:19:16
categories: X86
tags: SDM
---

Advanced Matrix Extension (AMX) 高级矩阵运算，是x86平台新引入的一个矩阵相关的编程框架。AMX扩展引入了两个新的组件：二维寄存器，成为`tile`, 还有一组可以操作那些`tile`的加速器。Tile指代内存中的一个二维数组。AMX指令在指令流中依靠内存load/store操作同步的访问内存。AMX指令可以自由的于X86的传统指令集，以及其他的扩展指令并发执行，例如AVX512.
![amx_architecture.svg](amx_architecture.svg)

## Palettes

决定操作类型，并且允许枚举硬件支持的操作类型。目前有两种Palettes：

Palette 0 - 初始化阶段
Palette 1 - 8-tile 寄存器文档(registor file)，每个寄存器含有16行 x 64字节(共1KB)的寄存器, 共计8KB的registor file.

开发人员可以通过配置，使用较小的二维数组，来改变register file的大小，以更好地适应他们的算法。Tile可以配置加速器中储存元数据的'行'和'每行字节数'。跟Palette有关的信息，都储存在tile控制寄存器(TILECFG)中，并且可以通过palette_table CPUID(0x1D) 访问。 TILECFG使用LDTILECFG指令来配置。

## Accelerators

AMX 支持一组机器，可以通过他们操作tile。 目前，只有一个加速器

## Tile matrix multiply unit (TMUL)
Tile Matrix Multiply (TMUL) 单元就是那个加速器, 包括一系列针对Tile上的'乘-加'操作. AMX-INT8 以及 AMX-BF16 以及其自扩展正是定义了这些操作。TMUL指令集计算：
```
TileC[M][N] += TileA[M][K] * TileB[K][N].
```
![amx_dot_product_of_tiles.svg](amx_dot_product_of_tiles.svg)

TMUL单元有一些支持的参数，包括maximum height (tmul_maxk)和 maximum SIMD dimension (tmul_maxn). 这些参数可以动态的被TMUL单元读取。

## Instructions

AMX新引入了12个新指令:

配置：
`LDTILECFG` - Load tile configuration, loads the tile configuration from the 64-byte memory location specified.
`STTILECFG` - Store tile configuration, stores the tile configuration in the 64-byte memory location specified.

数据：
`TILELOADD/TILELOADDT1` - Load tile
`TILESTORED` - Store tile
`TILERELEASE` - Release tile, returns TILECFG and TILEDATA to the INIT state
`TILEZERO` - Zero tile, zeroes the destination tile

操作：
`TDPBF16PS` - Perform a dot-product of BF16 tiles and accumulate the result. Packed Single Accumulation.
`TDPB[XX]D` - Perform a dot-product of Int8 tiles and accumulate the result. Dword Accumulation.
Where XX can be: SU = Signed/Unsigned, US = Unsigned/Signed, SS = Signed/Signed, and UU = Unsigned/Unsigned pairs.

## Feature set
不是所有的硬件实现支持这些所有的操作。AMX扩展包含三个自扩展: AMX-TILE, AMX-INT8, and AMX-BF16.

|Instruction	| AMX-TILE(Base)	|AMX-INT8(TMUL)	|AMX-BF16(TMUL)	|
| ----- 	| ----- 		| -----		| -----		|
|LDTILECFG	|✔			| 		|		|
|STTILECFG	|✔			| 		|		|
|TILELOADD	|✔			| 		|		|
|TILELOADDT1	|✔			| 		|		|	
|TILESTORED	|✔			| 		|		|
|TILERELEASE	|✔			| 		|		|
|TILEZERO	|✔			| 		|		|
|TDPBSSD	|			|✔		|		|
|TDPBSUD	|			|✔		|		|
|TDPBUSD	|			|✔		|		|
|TDPBUUD	|			|✔		|		|
|TDPBF16PS	|			|		|✔		|

## Detection
|CPUID		|Output		|Instruction Set|
| ----- 	| ----- 	| -----		|
|EAX=07H, ECX=0	|EDX[bit 22]	|AMX-BF16	|
|EAX=07H, ECX=0	|EDX[bit 24]	|AMX-TILE	|
|EAX=07H, ECX=0	|EDX[bit 25]	|AMX-INT8	|

## 参考文献
[Advanced Matrix Extension (AMX) - x86](https://en.wikichip.org/wiki/x86/amx)
[Intel® Architecture Instruction Set Extensions and Future Features 319433-044 May 2021](architecture-instruction-set-extensions-programming-reference_20210812.pdf)

## 参考代码
(稍后更新)
