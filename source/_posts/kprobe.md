---
title: Kprobe原理和应用
donate: true
date: 2022-11-06 16:13:30
categories: kernel
tags: kernel
---

Kprobes 能够动态地中断任何内核正在执行的指令，可以在几乎任何内核代码地址处捕获，指定在断点被命中时要调用的处理函数。
目前有两种类型的probe：kprobes 和 kretprobes（也称为return probe）。 kprobe 可以插入到内核中的几乎任何指令上；而kretprobe是当指定函数返回时，会触发返回函数调用。
通常，Kprobes会被在内核模块中。在模块的初始化函数中，注册一个或多个probe函数，而在该模块的exit函数中取消注册的函数。后面会贴一些内核的事例代码。

## Kprobe
### Kprobe 工作原理？
注册kprobe函数后，Kprobes会复制被探测的指令，并用断点指令（x86_64 上的 int3指令）替换被探测指令的第一个字节。
当 CPU 遇到断点指令时，会发生`trap`，保存 CPU 的寄存器，并通过 notifier_call_chain 机制将控制权传递给 Kprobes。 Kprobes 执行与 kprobe 相关的`pre_handler`，将 kprobe 结构的地址和保存的寄存器传递给处理程序。

接下来，Kprobes一次性执行完被probe的指令。 然后Kprobes 执行`post_handler`（如果有）。
最后，返回继续执行探测点之后的指令。

### 更改执行路径
由于 kprobes 可以探测正在运行的内核代码，所以它可以更改寄存器，包括指令指针。此操作需要非常小心，例如保护堆栈，恢复执行路径等。
如果在回调函数pre_handler中修改指令指针(IP)寄存器以及相关的寄存器，那么`pre_handler`必须返回非零值，此时，kprobes会停止上面提到的一次性执行的步骤，仅会返回一个到给定地址。这也意味着不应再调用`post_handler`函数。

## return probe
### return probe 工作原理
KProbe利用注册函数register_kretprobe()，在要探测的函数入口处建立一个探测点。当被探测的函数被调用并且这个探测被命中时，Kprobes会保存一份返回地址的副本，并将返回地址替换为另一个“trampoline”的地址。"trampoline"是一段任意代码，通常只是一条 nop 指令。在启动时，Kprobes 在蹦床上注册一个 kprobe。
当被探测的函数执行它的返回指令时，控制权传递给“trampoline”指令，并且该探测被命中。 Kprobes 的 trampoline 处理程序调用kretprobe注册的用户指定的返回处理程序，然后将保存的指令指针设置为保存的返回地址，这就是从陷阱返回后恢复执行的地方。

当被探测函数正在执行时，它的返回地址存储在一个kretprobe_instance类型的对象中。在调用 register_kretprobe() 之前，用户设置 kretprobe 结构的 maxactive 字段来指定可以同时探测多少个指定函数的实例。 register_kretprobe() 预分配指定数量的 kretprobe_instance 对象。

例如，如果函数是非递归的并且在调用时持有自旋锁，那么 maxactive = 1 就足够了。如果函数是非递归的并且永远不会放弃 CPU（例如，通过信号量或抢占），则 NR_CPUS 应该足够了。如果 maxactive <= 0，则设置为默认值。

如果 maxactive 设置得太低，会错过一些探测。在 kretprobe 结构中，nmissed 字段在注册返回探针时设置为零，并且每次进入被探测函数但没有可用于建立返回探针的 kretprobe_instance 对象时递增。

### Kretprobe 入口处理程序

Kretprobes 还提供了一个可选的用户指定的处理程序，它在函数入口上运行。该处理程序是通过设置 kretprobe 结构的 entry_handler 字段来指定的。每当 kretprobe 放置在函数入口处的 kprobe 被命中时，都会调用用户定义的 entry_handler，如果有的话。如果 entry_handler 返回 0（成功），则保证在函数返回时调用相应的返回处理程序。如果 entry_handler 返回非零错误，则 Kprobes 将返回地址保持原样，并且 kretprobe 对该特定函数实例没有进一步的影响。

使用与它们关联的唯一 kretprobe_instance 对象来匹配多个入口和返回处理程序调用。此外，用户还可以将每个返回实例的私有数据指定为每个 kretprobe_instance 对象的一部分。这在相应的用户条目和返回处理程序之间共享私有数据时特别有用。每个私有数据对象的大小可以在 kretprobe 注册时通过设置 kretprobe 结构的 data_size 字段来指定。可以通过每个 kretprobe_instance 对象的数据字段访问此数据。

如果输入了探测函数但没有可用的 kretprobe_instance 对象，则除了增加 nmissed 计数外，还会跳过用户 entry_handler 调用。

![kprobe](KProbeExecution.png)

```c
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>

static char symbol[KSYM_NAME_LEN] = "kernel_clone";
module_param_string(symbol, symbol, KSYM_NAME_LEN, 0644);

/* For each probe you need to allocate a kprobe structure */
static struct kprobe kp = {
	.symbol_name	= symbol,
};

/* kprobe pre_handler: called just before the probed instruction is executed */
static int __kprobes handler_pre(struct kprobe *p, struct pt_regs *regs)
{
	pr_info("<%s> p->addr = 0x%p, ip = %lx, flags = 0x%lx\n",
		p->symbol_name, p->addr, regs->ip, regs->flags);

	/* A dump_stack() here will give a stack backtrace */
	return 0;
}

/* kprobe post_handler: called after the probed instruction is executed */
static void __kprobes handler_post(struct kprobe *p, struct pt_regs *regs,
				unsigned long flags)
{
	pr_info("<%s> p->addr = 0x%p, flags = 0x%lx\n",
		p->symbol_name, p->addr, regs->flags);
}

static int __init kprobe_init(void)
{
	int ret;
	kp.pre_handler = handler_pre;
	kp.post_handler = handler_post;

	ret = register_kprobe(&kp);
	if (ret < 0) {
		pr_err("register_kprobe failed, returned %d\n", ret);
		return ret;
	}
	pr_info("Planted kprobe at %p\n", kp.addr);
	return 0;
}

static void __exit kprobe_exit(void)
{
	unregister_kprobe(&kp);
	pr_info("kprobe at %p unregistered\n", kp.addr);
}

module_init(kprobe_init)
module_exit(kprobe_exit)
MODULE_LICENSE("GPL");
```
```c
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/kprobes.h>

static char func_name[KSYM_NAME_LEN] = "kernel_clone";
module_param_string(func, func_name, KSYM_NAME_LEN, 0644);
MODULE_PARM_DESC(func, "Function to kretprobe; this module will report the"
			" function's execution time");

/* per-instance private data */
struct my_data {
	ktime_t entry_stamp;
};

/* Here we use the entry_hanlder to timestamp function entry */
static int entry_handler(struct kretprobe_instance *ri, struct pt_regs *regs)
{
	struct my_data *data;

	if (!current->mm)
		return 1;	/* Skip kernel threads */

	data = (struct my_data *)ri->data;
	data->entry_stamp = ktime_get();
	return 0;
}
NOKPROBE_SYMBOL(entry_handler);

/*
 * Return-probe handler: Log the return value and duration. Duration may turn
 * out to be zero consistently, depending upon the granularity of time
 * accounting on the platform.
 */
static int ret_handler(struct kretprobe_instance *ri, struct pt_regs *regs)
{
	unsigned long retval = regs_return_value(regs);
	struct my_data *data = (struct my_data *)ri->data;
	s64 delta;
	ktime_t now;

	now = ktime_get();
	delta = ktime_to_ns(ktime_sub(now, data->entry_stamp));
	pr_info("%s returned %lu and took %lld ns to execute\n",
			func_name, retval, (long long)delta);
	return 0;
}
NOKPROBE_SYMBOL(ret_handler);

static struct kretprobe my_kretprobe = {
	.handler		= ret_handler,
	.entry_handler		= entry_handler,
	.data_size		= sizeof(struct my_data),
	/* Probe up to 20 instances concurrently. */
	.maxactive		= 20,
};

static int __init kretprobe_init(void)
{
	int ret;

	my_kretprobe.kp.symbol_name = func_name;
	ret = register_kretprobe(&my_kretprobe);
	if (ret < 0) {
		pr_err("register_kretprobe failed, returned %d\n", ret);
		return ret;
	}
	pr_info("Planted return probe at %s: %p\n",
			my_kretprobe.kp.symbol_name, my_kretprobe.kp.addr);
	return 0;
}

static void __exit kretprobe_exit(void)
{
	unregister_kretprobe(&my_kretprobe);
	pr_info("kretprobe at %p unregistered\n", my_kretprobe.kp.addr);

	/* nmissed > 0 suggests that maxactive was set too low. */
	pr_info("Missed probing %d instances of %s\n",
		my_kretprobe.nmissed, my_kretprobe.kp.symbol_name);
}

module_init(kretprobe_init)
module_exit(kretprobe_exit)
MODULE_LICENSE("GPL");
```

## 参考文档
https://www.kernel.org/doc/html/latest/trace/kprobes.html
