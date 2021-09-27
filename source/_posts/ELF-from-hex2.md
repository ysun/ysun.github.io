---
title: ELF-from-hex2
donate: true
date: 2021-09-17 20:51:18
categories:
tags:
---

之前写过一篇关于[如何手写最小ELF](ELF-from-hex)的文章。但偶然间在油管上发现了一个很好的视频，参考文末链接。
可以进一步缩小ELF文件。大概思路是:
* 将之前64bit的文件改写成32bit
* 整个e_ident部分是可以被覆盖的
* e_shoff e_flags e_ehsize e_shnum e_shstrndx p_flags 是可以去掉的。
* 代码段一堆放不下，是可以用JMP跳转的

视频里一个基础的最小32bit ELF如下：

```
# >>>>>>>>>>>>> ELF FILE HEADER <<<<<<<<<<<<<
                # All numbers (except in names) are in base sixteen (hexadecimal)
                # 00 <- number of bytes listed so far
7F 45 4C 46     # 04 e_ident[EI_MAG]: ELF magic number
01              # 05 e_ident[EI_CLASS]: 1: 32-bit, 2: 64-bit
   01           # 06 e_ident[EI_DATA]: 1: little-endian, 2: big-endian
      01        # 07 e_ident[EI_VERSION]: ELF header version; must be 1
         00     # 08 e_ident[EI_OSABI]: Target OS ABI; should be 0
00              # 09 e_ident[EI_ABIVERSION]: ABI version; 0 is ok for Linux
   00 00 00     # 0C e_ident[EI_PAD]: unused, should be 0
00 00 00 00     # 10

02 00           # 12 e_type: object file type; 2: executable
      03 00     # 14 e_machine: instruction set architecture; 3: x86, 3E: amd64
01 00 00 00     # 18 e_version: ELF identification version; must be 1

54 80 04 08     # 1C e_entry: memory address of entry point (where process starts)
34 00 00 00     # 20 e_phoff: file offset where program headers begin

00 00 00 00     # 24 e_shoff: file offset where section headers begin
00 00 00 00     # 28 e_flags: 0 for x86

34 00           # 2A e_ehsize: size of this header (34: 32-bit, 40: 64-bit)
      20 00     # 2C e_phentsize: size of each program header (20: 32-bit, 38: 64-bit)
01 00           # 2E e_phnum: #program headers
      28 00     # 30 e_shentsize: size of each section header (28: 32-bit, 40: 64-bit)

00 00           # 32 e_shnum: #section headers
      00 00     # 34 e_shstrndx: index of section header containing section names

# >>>>>>>>>>>>> ELF PROGRAM HEADER <<<<<<<<<<<<<

01 00 00 00     # 38 p_type: segment type; 1: loadable

54 00 00 00     # 3C p_offset: file offset where segment begins
54 80 04 08     # 40 p_vaddr: virtual address of segment in memory (x86: 08048054)
    
00 00 00 00     # 44 p_paddr: physical address of segment, unspecified by 386 supplement
34 00 00 00     # 48 p_filesz: size in bytes of the segment in the file image ############

34 00 00 00     # 4C p_memsz: size in bytes of the segment in memory; p_filesz <= p_memsz
05 00 00 00     # 50 p_flags: segment-dependent flags (1: X, 2: W, 4: R)

00 10 00 00     # 54 p_align: 1000 for x86

# >>>>>>>>>>>>> PROGRAM SEGMENT <<<<<<<<<<<<<

# Print "Hello, world" repeatedly.

# Linux system calls:   man 2 syscalls; man 2 write
# Instructions:         Intel Vol 2 Chs 3..5
# Values +rd:           Intel Vol 2 Table 3-1
# Opcode map:           Intel Vol 2 Table A-2

                # 54    INTENTION               INSTRUCTION         OPCODE
BB 01 00 00 00  #       ebx <- 1 (stdout)
B9 7E 80 04 08  #       ecx <- buf
BA 0A 00 00 00  #       edx <- count
BF 03 00 00 00  # 68    edi <- 5 (loop count)
# Begin
B8 04 00 00 00  #       eax <- 4 (write)        mov r32, imm32      B8+rd id
CD 80           #       syscall                 int imm8            CD ib
4F              #       edi <- edi - 1          dec r32             48+rd
75 F6           # 72    jump Begin if nonzero   jnz rel8            75 cb

B8 01 00 00 00  #       eax <- 1 (exit)
BB 00 00 00 00  #       ebx <- 0 (param)
CD 80           # 7E    syscall

48 45 4C 4F 20  #       "HELO "
57 52 4C 44 0A  # 88    "WRLD\n"
```

编译脚本如下：
```
#!/bin/bash
for f in *.dmp ; do
    a=`basename $f .dmp`
    cut -d'#' -f1 <$f | xxd -p -r >$a
    chmod +x $a
done
```
编译好的Binary应该是136字节，是ELF header + Program header + print 字符代码 长度总和。

但这一切仅仅是使用了32bit格式的ELF，还没有开始“爆改”。

## 爆改开始
```
# >>>>>>>>>>>>> ELF FILE HEADER <<<<<<<<<<<<<
                # All numbers (except in names) are in base sixteen (hexadecimal)
                # 00 <- number of bytes listed so far
7F 45 4C 46     # 04 e_ident[EI_MAG]: ELF magic number

## 字符串HELLO WORLD算上回车刚好12字节
## 用这12个字节替换掉整个e_ident头
##
48 45 4C 4C     # 08 Put string "HELLO WORLD\n" 
4F 20 57 4F     # 0C Instead of e_ident, detailed as following
52 4C 44 0a     # 10
#01              # 05 e_ident[EI_CLASS]: 1: 32-bit, 2: 64-bit
#   01           # 06 e_ident[EI_DATA]: 1: little-endian, 2: big-endian
#      01        # 07 e_ident[EI_VERSION]: ELF header version; must be 1
#         00     # 08 e_ident[EI_OSABI]: Target OS ABI; should be 0
#00              # 09 e_ident[EI_ABIVERSION]: ABI version; 0 is ok for Linux
#   00 00 00     # 0C e_ident[EI_PAD]: unused, should be 0
#00 00 00 00     # 10

02 00           # 12 e_type: object file type; 2: executable
      03 00     # 14 e_machine: instruction set architecture; 3: x86, 3E: amd64
01 00 00 00     # 18 e_version: ELF identification version; must be 1

20 00 00 00     # 1C e_entry: memory address of entry point (where process starts)
30 00 00 00     # 20 e_phoff: file offset where program headers begin

##  Code section 从这里开始！替换掉e_shoff e_flags e_ehsize
##  首先查表asm86 把所有指令的输入参数都改用imm8长度
##  这一段依然塞不下，那就在8字节之后，加一个相对跳转指令jmp，参数是相对字节数
B0 04 B3 01     # 24 eax <- 4 (write); ebx <- 1 (stdout) 
B1 04 B2 0C     # 28 ecx <- buf; edx <- count                                         
EB 1E           # 2a Jump relative to 1E, because of not finishing.
#00 00 00 00     # 24 e_shoff: file offset where section headers begin
#00 00 00 00     # 28 e_flags: 0 for x86
#34 00           # 2A e_ehsize: size of this header (34: 32-bit, 40: 64-bit)
      20 00     # 2C e_phentsize: size of each program header (20: 32-bit, 38: 64-bit)
01 00           # 2E e_phnum: #program headers
      28 00     # 30 e_shentsize: size of each section header (28: 32-bit, 40: 64-bit)

## 因为没有section header，所有相关的参数都无所谓了
## 可以直接从这里开始接上program header了！
#00 00           # 32 e_shnum: #section headers
#      00 00     # 34 e_shstrndx: index of section header containing section names

# >>>>>>>>>>>>> ELF PROGRAM HEADER <<<<<<<<<<<<<

01 00 00 00     # 34 p_type: segment type; 1: loadable
20 00 00 00     # 38-4 p_offset: file offset where segment begins
20 00 00 00     # 3C-4 p_vaddr: virtual address of segment in memory (x86: 08048054)
00 00 00 00     # 40 p_paddr: physical address of segment, unspecified by 386 supplement
2C 00 00 00     # 44 p_filesz: size in bytes of the segment in the file image ############
2C 00 00 00     # 48 p_memsz: size in bytes of the segment in memory; p_filesz <= p_memsz

## The second code, instead of p_flags.
## 因为 代码段还需要8字节，得益于ELF header的末尾省掉的4字节，这里可以有8字节了。
## 为什么这么说，因为整个Header还是需要对齐的。
## 接着之前的代码段继续。同时注意前面的JMP后面的参数，就是这里到JMP的相对地址。
CD 80 B0 01		# 4C syscall; eax <- 1 (exit)
B3 00 CD 80		# 50 ebx <- 0 (param); syscall; #p_align: 1000 for x86
#05 00 00 00     # 50 p_flags: segment-dependent flags (1: X, 2: W, 4: R)

```

编译脚本不变。现在编译出来的binary大小为80字节。当然，先前有大神可以缩减到更小，有兴趣自行Google吧，或许某天开悟再来更新。

## Reference
[Handmade Linux x86 executables: ELF header](https://www.youtube.com/watch?v=XH6jDiKxod8)
[Handmade Linux x86 executables](https://www.youtube.com/playlist?list=PLZCIHSjpQ12woLj0sjsnqDH8yVuXwTy3p)
