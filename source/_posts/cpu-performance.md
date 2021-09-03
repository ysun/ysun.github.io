---
title: 怎样精确计算CPU频率
donate: true
date: 2021-08-31 13:29:21
categories: Kernel
tags: Kernel
---

最近因工作需要，需要精确计算CPU的performance，顺便查了下，应该如何稍微精确的计算CPU的频率。
大概网上搜到三种方法：1，使用rdtsc，通过tsc计算CPU频率；2，IA32_APERF 和 IA32_MPERF两个MSR计算；3，系统接口"/sys/devices/system/cpu/cpu<x>/cpufreq/scaling_cur_freq"
下面来分别比较下三种方法的优劣：

## rdtsc
tsc是一个内核态和用户态都能访问的指令。有两种方式读取tsc。

### 内嵌汇编
  __asm volatile ("rdtsc" : "=A"(t));

参考code：

```
#include <stdint.h>

uint64_t rdtsc(){
	unsigned int lo,hi;
	__asm__ __volatile__ ("rdtsc" : "=a" (lo), "=d" (hi));
	return ((uint64_t)hi << 32) | lo;
}
```

* "=a"(lo) 和 "=d"(hi): 输出操作符，使用固定的寄存器EAX 和 EDX来存放结果。x86 rdtsc指令存放64位结果到`EDX:EAX`, 所以如果使用"=r"是不工作的。
* ((uint64_t)hi << 32) | lo 


### __rdtsc() intrinsic
参考code:

```
#include <stdint.h>
#include <x86intrin.h>

uint64_t rdtsc(){
	return __rdtsc();
}
```

### 读取CPU频率
这两种读取tsc的方法可能没啥区别，下面看下实际上读取CPU频率的逻辑：

```
int main(void)
{
    double c1, c2;

    c1 = rdtsc();
    sleep(1);

--> mfence();
--> __cpuid({0,0,0,0}, 0);

--> // unsigned eax;
--> //__asm__ __volatile__("cpuid" : "=a"(eax) : "a"(0x00));

    c2 = rdtsc();

    printf("CPU Frequency: %.1f MHz\n", (c2-c1)/1E6);
    printf("CPU Frequency: %.1f GHz\n", (c2-c1)/1E9);

    return 0;
}
```

注意，在两次rdtsc中间，需要插入fence或者cpuid，防止CPU重排序，一般现代的CPU都会发生类似下面的事情：

```
rdtsc
push 1
call sleep
rdtsc
```

重排序为：
```
rdtsc
rdtsc
push 1
call sleep
```
TSC完美的时间源，以一个固定的频率计数，无论turbo 或者 power-saveing 功能开关与否，不受这些新功能的影响。并且在较新的CPU上，CPU频率仅仅是与之接近，并不是一样的。例如 i7-6700HQ 2.6 GHz Skylake 实际频率是2592MHZ。或者4000MHz i7-6700k实际频率是4008MHZ。所以，即便禁用了turbo或者power-saving 依然不能得到CPU的准确的工作频率


##  IA32_MPERF 和 IA32_APERF
MPERF计数，使用一个固定不变的频率计数，是在CPU一开始启动的时候就配置好了。
APERF计数，CPU指令实际的计数。

所以得到如下公式：
```
CPU_freq = tsc_freq * (aperf_t1 - aperf_t0) / (mperf_t1 - mperf_t0)
```

MPERF 和 APERF 的大概读取方法如下。注意，rdmsr是特权(privileged)指令，只能运行在ring 0(内核态)。
```
; read MPERF
mov ecx, 0xe7
rdmsr
mov mperf_var_lo, eax
mov mperf_var_hi, edx

; read APERF
mov ecx, 0xe8
rdmsr
mov aperf_var_lo, eax
mov aperf_var_hi, edx

; read maxfreq
rdmsr ecx, 0xce
;bits 8:15
```
如果，只能在user space的话，读取MSR可以使用msr module。
```
modprobe msr
msr 0xe7 -a    //可以指定具体哪一个cpu thread
```
可以使用文件`/dev/cpu/*/msr`获取MSR。

可以说MPERF和APERF来计算CPU实际的频率应该是最精确的。但正当我在想如何在user space更优雅的使用MSR的时候，我发现了这个[patch](https://lore.kernel.org/lkml/52f711be59539723358bea1aa3c368910a68b46d.1459485198.git.len.brown@intel.com/)：

## scaling driver
Scaling驱动就是利用MPERF和APERF计算出来，从内核角度看到的CPU当前实际运行的频率。 尽管在user space查询频率有点额外effort，但这可能是最为准确的方法了。如果有更好的方法，欢迎留言通知。

```
/sys/devices/system/cpu/cpu*/cpufreq/scaling_cur_freq
```

## Reference

[How to get the CPU cycle count in x86_64 from C++?](https://stackoverflow.com/questions/13772567/how-to-get-the-cpu-cycle-count-in-x86-64-from-c/51907627#51907627)
[Calculating CPU frequency in C with RDTSC always returns 0](https://stackoverflow.com/questions/2814569/calculating-cpu-frequency-in-c-with-rdtsc-always-returns-0)
[Assembly CPU frequency measuring algorithm](https://stackoverflow.com/questions/65095/assembly-cpu-frequency-measuring-algorithm)

[access to model specific registers, IA32_APERF / IA32_MPERF, to measure actual CPU frequency](https://stackoverflow.com/questions/16145835/access-to-model-specific-registers-ia32-aperf-ia32-mperf-to-measure-actual-c)
