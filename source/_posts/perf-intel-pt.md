---
title: Perf with Intel Processor Trace (intel-pt)
donate: true
date: 2022-03-31 16:16:36
categories: Linux
tags: Linux
---

# 什么是 Intel Processor Trace

Intel Processor Trace (PT) traces技术以非常小的开销跟踪程序的执行，覆盖所有的分支。 本文简单的介绍下如何利用Perf使用Intel PT跟踪程序执行。
更详细的有关Intel PT的介绍请参考 [Adding PT to Linux perf](https://lwn.net/Articles/648154/) 和 [PT reference page](http://halobates.de/blog/p/406).

# PT 的硬件支持

CPU                                      | Support                                
---------------------------------------- | ---------------------------------------
Broadwell (5th generation Core, Xeon v4) | More overhead. No fine grained timing. 
Skylake (6th generation Core, Xeon v5)   | Fine grained timing. Address filtering.

# PT 和Linux支持

PT已经被集成到内核代码的工具包的perf里，可以简单的通过perf使用intel-pt。 当然还有一些其他的工具支持PT的比如[VTune](https://software.intel.com/en-us/intel-vtune-amplifier-xe), [simple-pt](https://github.com/andikleen/simple-pt), gdb, JTAG debuggers.

Linux version | Support                                         
------------- | ------------------------------------------------
Linux 4.1     | Initial PT driver                               
Linux 4.2     | Support for Skylake and Goldmont                
Linux 4.3     | Initial user tools support in Linux perf        
Linux 4.5     | Support for JIT decoding using agent            
Linux 4.6     | Bug fixes. Support address filtering.           
Linux 4.8     | Bug fixes.                                      
Linux 4.10    | Bug fixes. Support for PTWRITE and power tracing

基本上稍微新一点的内核都支持了PT。
本文主要介绍perf中对PT的支持和使用，以及简单的gdb支持。

# 准备工作

```
echo kernel.kptr_restrict=0' >> /etc/sysctl.conf
sysctl -p
```

# 记录PT的perf基础命令

查看PT是否支持，以及有哪些功能：
```
ls /sys/devices/intel_pt/format
```

跟踪程序：
```
perf record -e intel_pt// program
```

例如：
或许系统系统一秒钟的PT trace：
```
perf record -e intel_pt// -a sleep 1
```

Trace CPU 0 for 1 second
```
perf record -C 0 -e intel_pt// -a sleep 1
```

跟踪一个正在运行的程序：
```
perf record --pid $(pidof program) -e intel_pt//
```

perf需要把trace保存到本地硬盘。CPU执行的速度要远大于写磁盘的速度，所以当trace大量的数据的时候，很可能造成数据的丢失。Perf没有办法降低CPU的执行速度。当 `trace带宽 > 硬盘带宽` 时，trace里面就产生gap，所以，不要试图保存长的trace，尽量使用短的trace。

Perf数据解析的时候需要使用root权限:
```
perf script --ns --itrace=cr
```

perf script 解析数据默认时间建个是100us，可以通过参数`-itrace`来缩短时间间隔：

```
perf script --itrace=i0ns --ns -F time,pid,comm,sym,symoff,insn,ip
```
Show every assembly instruction executed with disassembler.

显示源码：
```
perf script --itrace=i0ns --ns -F time,sym,srcline,ip 
```
跳过最初的1M的指令：
```
perf script --itrace=s1Mi0ns .... 
```
把trace切片成多个时间片：
```
perf script --time 1.000,2.000 ...
```
打印每100us打印path
```
perf report --itrace=g32l64i100us  --branch-history
```

每100us采集一次，并生成火图，需要安装Install [Flame graph tools](https://github.com/brendangregg/FlameGraph)。
```
perf script --itrace=i100usg | stackcollapse-perf.pl > workload.folded  
flamegraph.pl workloaded.folded > workload.svg  
google-chrome workload.svg
```

# 记录数据的其他方法

抓取整个系统1秒钟
```
perf record -a -e intel_pt// sleep 1
```
只记录内核trace:
```
perf record -a -e intel_pt//k sleep 1
```
只记录用户态trace:
```
perf record -a -e intel_pt//u
```

使用细力度trace
```
perf record -a -e intel_pt/cyc=1,cyc_thresh=2/ ...
```

`  
增加perf buffer，防止数据丢失
```
echo  $[100*1024*1024] > /proc/sys/kernel/perf_event_mlock_kb  
perf record -m 512,100000 -e intel_pt// ...  `
```

只记录应用程序中main函数的trace
```
perf record -e intel_pt// --filter 'filter main @ /path/to/program'  ... 
```
过滤内核代码(v4.11+):
```
perf record -e intel_pt// -a --filter 'filter sys_write'  program
```

记录程序中，从main开始，到func2结束的trace:
```
perf record -e intel_pt// -a --filter 'start func1 @ program' --filter 'stop func2 @ program' program 
```

# 使用gdb
需要编译gdb是使用libipt，仅供用户态应用

```  
gdb program  
start  
record btrace pt  
cont  
<ctrl-c or="" crash=""><br>
record instruction-history /m	# show instructions<br>
record function-history		# show functions executed<br>
prev			# step backwards in time<br>
</ctrl-c>
```
For more information on gdb pt see the [gdb documentation](https://sourceware.org/gdb/onlinedocs/gdb/Process-Record-and-Replay.html)

# 参考

最详尽的参考：https://man7.org/linux/man-pages/man1/perf-intel-pt.1.html

The [perf PT documentation](https://git.kernel.org/cgit/linux/kernel/git/torvalds/linux.git/tree/tools/perf/Documentation/intel-pt.txt)
```
Reference for –itrace option (from perf documentation)

* i       synthesize "instructions" events  
* b       synthesize "branches" events  
* x       synthesize "transactions" events  
* c       synthesize branches events (calls only)  
* r       synthesize branches events (returns only)  
* e       synthesize tracing error events  
* d       create a debug log  
* g       synthesize a call chain (use with i or x)  
* l       synthesize last branch entries (use with i or x)  
* s       skip initial number of events  

Reference for –filter option (from perf documentation)

A hardware trace PMU advertises its ability to accept a number of address filters by specifying a non-zero value in /sys/bus/event_source/devices/
<pmu>/nr_addr_filters.</pmu>

Address filters have the format:

filter|start|stop|tracestop 
<start> [/ <size>] [@<file name="">]</file></size></start>

Where:  
- 'filter': defines a region that will be traced.  
- 'start': defines an address at which tracing will begin.  
- 'stop': defines an address at which tracing will stop.  
- 'tracestop': defines a region in which tracing will stop.

<file name=""> is the name of the object file, <start> is the offset to the<br>
code to trace in that file, and <size> is the size of the region to<br>
trace. 'start' and 'stop' filters need not specify a <size>.</size></size></start></file>

If no object file is specified then the kernel is assumed, in which case  
the start address must be a current kernel memory address.

<start> can also be specified by providing the name of a symbol. If the<br>
symbol name is not unique, it can be disambiguated by inserting #n where<br>
'n' selects the n'th symbol in address order. Alternately #0, #g or #G<br>
select only a global symbol. <size> can also be specified by providing<br>
the name of a symbol, in which case the size is calculated to the end<br>
of that symbol. For 'filter' and 'tracestop' filters, if <size> is<br>
omitted and <start> is a symbol, then the size is calculated to the end<br>
of that symbol.</start></size></size></start>

If 
<size> is omitted and <start> is '*', then the start and size will<br>
be calculated from the first and last symbols, i.e. to trace the whole<br>
file.<br>
If symbol names (or '*') are provided, they must be surrounded by white<br>
space.</start></size>

The filter passed to the kernel is not necessarily the same as entered.  
To see the filter that is passed, use the -v option.

The kernel may not be able to configure a trace region if it is not  
within a single mapping.  MMAP events (or /proc/
<pid>/maps) can be<br>
examined to determine if that is a possibility.</pid> 

Multiple filters can be separated with space or comma.
```

===================================

Install [xed](https://github.com/intelxed/xed) first.
```
perf script --itrace=i0ns --ns -F time,pid,comm,sym,symoff,insn,ip | xed -F insn: -S /proc/kallsyms -64
```

