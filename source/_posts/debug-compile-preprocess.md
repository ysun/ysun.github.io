---
title: 内核宏定义展开
donate: true
date: 2022-06-19 20:30:06
categories: Kernel
tags: Kernel
---

最近用到了内核中的一些宏定义(Macro)，但一直以来，内核的宏定义学习起来都是比较费劲的，一层套一层的定义，新上手的同学一时间很难搞清楚运行时到底用了哪个宏定义，宏定义展开到底怎样。今天发现一个不错的方法研究内核的宏定义。

## 使用编译预处理研究宏定义展开

### 编译选项V=1
内核根目录的Makefile里面，搜索`V=1`可以找到如下这段：
```c
# To put more focus on warnings, be less verbose as default
# Use 'make V=1' to see the full commands                   
```
使用这个选项可以看到编译时完整的命令行。

然后执行编译并且保存输出到文件中
```
make V=1 LOCALVERSION="" -j64 >& /tmp/build.log
```

### 修改gcc参数
在文件`build.log`中搜到所需要的`.c`文件，例如
```
gcc -Wp,-MMD,arch/x86/kernel/fpu/.xstate.o.d -nostdinc -I./arch/x86/include -Wall -Wundef -Werror=strict-prototypes 
.......
-DKBUILD_MODFILE='"arch/x86/kernel/fpu/xstate"' -DKBUILD_BASENAME='"xstate"' -DKBUILD_MODNAME='"xstate"' -D__KBUILD_MODNAME=kmod_xstate -c -o arch/x86/kernel/fpu/xstate.o arch/x86/kernel/fpu/xstate.c
```
全部的编译参数很多，这里省略掉。然后把参数`-c` 改成 `-E`，同时把输出文件换个名字比如把`.o`文件换成`.S`。可以把这句家`gcc`命令保存成一个脚本，直接执行就可以得到`arch/x86/kernel/fpu/xstate.o`，其中可以清楚的看到各种宏展开的结果。
