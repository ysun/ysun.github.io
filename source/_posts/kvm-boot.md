title: KVM 虚拟化原理2— QEMU启动过程
donate: true
date: 2018-12-10 22:57:17
categories: KVM
tags: KVM
---

## 虚拟机启动过程

```hljs
第一步，获取到kvm句柄
kvmfd = open("/dev/kvm", O_RDWR);
第二步，创建虚拟机，获取到虚拟机句柄。
vmfd = ioctl(kvmfd, KVM_CREATE_VM, 0);
第三步，为虚拟机映射内存，还有其他的PCI，信号处理的初始化。
ioctl(kvmfd, KVM_SET_USER_MEMORY_REGION, &mem);
第四步，将虚拟机镜像映射到内存，相当于物理机的boot过程，把镜像映射到内存。
第五步，创建vCPU，并为vCPU分配内存空间。
ioctl(kvmfd, KVM_CREATE_VCPU, vcpuid);
vcpu->kvm_run_mmap_size = ioctl(kvm->dev_fd, KVM_GET_VCPU_MMAP_SIZE, 0);
第五步，创建vCPU个数的线程并运行虚拟机。
ioctl(kvm->vcpus->vcpu_fd, KVM_RUN, 0);
第六步，线程进入循环，并捕获虚拟机退出原因，做相应的处理。
这里的退出并不一定是虚拟机关机，虚拟机如果遇到IO操作，访问硬件设备，缺页中断等都会退出执行，退出执行可以理解为将CPU执行上下文返回到QEMU。
```

```hljs
open("/dev/kvm")
ioctl(KVM_CREATE_VM)
ioctl(KVM_CREATE_VCPU)
for (;;) {
     ioctl(KVM_RUN)
     switch (exit_reason) {
     case KVM_EXIT_IO:  /* ... */
     case KVM_EXIT_HLT: /* ... */
     }
}
```

关于KVM_CREATE_VM参数的描述，创建的VM是没有cpu和内存的，需要QEMU进程利用mmap系统调用映射一块内存给VM的描述符，其实也就是给VM创建内存的过程。

[KVM ioctl接口文档](https://github.com/torvalds/linux/blob/master/Documentation/virtual/kvm/api.txt)

## 先来一个KVM API开胃菜

下面是一个KVM的简单demo，其目的在于加载 code 并使用KVM运行起来.  
这是一个at&t的8086汇编，.code16表示他是一个16位的，当然直接运行是运行不起来的，为了让他运行起来，我们可以用KVM提供的API，将这个程序看做一个最简单的操作系统，让其运行起来。  
这个汇编的作用是输出al寄存器的值到0x3f8端口。对于x86架构来说，通过IN/OUT指令访问。PC架构一共有65536个8bit的I/O端口，组成64KI/O地址空间，编号从0~0xFFFF。连续两个8bit的端口可以组成一个16bit的端口，连续4个组成一个32bit的端口。I/O地址空间和CPU的物理地址空间是两个不同的概念，例如I/O地址空间为64K，一个32bit的CPU物理地址空间是4G。  
最终程序理想的输出应该是，al，bl的值后面KVM初始化的时候有赋值。  
4\n (并不直接输出\n，而是换了一行），hlt 指令表示虚拟机退出

```hljs
.globl _start
    .code16
_start:
    mov $0x3f8, %dx
    add %bl, %al
    add $'0', %al
    out %al, (%dx)
    mov $'\n', %al
    out %al, (%dx)
    hlt
```

我们编译一下这个汇编，得到一个 Bin.bin 的二进制文件

```hljs
as -32 bin.S -o bin.o
ld -m elf_i386 --oformat binary -N -e _start -Ttext 0x10000 -o Bin.bin bin.o
```

查看一下二进制格式

```hljs
➜  demo1 hexdump -C bin.bin
00000000  ba f8 03 00 d8 04 30 ee  b0 0a ee f4              |......0.....|
0000000c
对应了下面的code数组，这样直接加载字节码就不需要再从文件加载了
    const uint8_t code[] = {
        0xba, 0xf8, 0x03, /* mov $0x3f8, %dx */
        0x00, 0xd8,       /* add %bl, %al */
        0x04, '0',        /* add $'0', %al */
        0xee,             /* out %al, (%dx) */
        0xb0, '\n',       /* mov $'\n', %al */
        0xee,             /* out %al, (%dx) */
        0xf4,             /* hlt */
    };
```

```hljs
#include <err.h>
#include <fcntl.h>
#include <linux/kvm.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/types.h>

int main(void)
{
    int kvm, vmfd, vcpufd, ret;
    const uint8_t code[] = {
        0xba, 0xf8, 0x03, /* mov $0x3f8, %dx */
        0x00, 0xd8,       /* add %bl, %al */
        0x04, '0',        /* add $'0', %al */
        0xee,             /* out %al, (%dx) */
        0xb0, '\n',       /* mov $'\n', %al */
        0xee,             /* out %al, (%dx) */
        0xf4,             /* hlt */
    };
    uint8_t *mem;
    struct kvm_sregs sregs;
    size_t mmap_size;
    struct kvm_run *run;

    // 获取 kvm 句柄
    kvm = open("/dev/kvm", O_RDWR | O_CLOEXEC);
    if (kvm == -1)
        err(1, "/dev/kvm");

    // 确保是正确的 API 版本
    ret = ioctl(kvm, KVM_GET_API_VERSION, NULL);
    if (ret == -1)
        err(1, "KVM_GET_API_VERSION");
    if (ret != 12)
        errx(1, "KVM_GET_API_VERSION %d, expected 12", ret);

    // 创建一虚拟机
    vmfd = ioctl(kvm, KVM_CREATE_VM, (unsigned long)0);
    if (vmfd == -1)
        err(1, "KVM_CREATE_VM");

    // 为这个虚拟机申请内存，并将代码（镜像）加载到虚拟机内存中
    mem = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE, MAP_SHARED | MAP_ANONYMOUS, -1, 0);
    if (!mem)
        err(1, "allocating guest memory");
    memcpy(mem, code, sizeof(code));

    // 为什么从 0x1000 开始呢，因为页表空间的前4K是留给页表目录
    struct kvm_userspace_memory_region region = {
        .slot = 0,
        .guest_phys_addr = 0x1000,
        .memory_size = 0x1000,
        .userspace_addr = (uint64_t)mem,
    };
    // 设置 KVM 的内存区域
    ret = ioctl(vmfd, KVM_SET_USER_MEMORY_REGION, &region);
    if (ret == -1)
        err(1, "KVM_SET_USER_MEMORY_REGION");

    // 创建虚拟CPU
    vcpufd = ioctl(vmfd, KVM_CREATE_VCPU, (unsigned long)0);
    if (vcpufd == -1)
        err(1, "KVM_CREATE_VCPU");

    // 获取 KVM 运行时结构的大小
    ret = ioctl(kvm, KVM_GET_VCPU_MMAP_SIZE, NULL);
    if (ret == -1)
        err(1, "KVM_GET_VCPU_MMAP_SIZE");
    mmap_size = ret;
    if (mmap_size < sizeof(*run))
        errx(1, "KVM_GET_VCPU_MMAP_SIZE unexpectedly small");
    // 将 kvm run 与 vcpu 做关联，这样能够获取到kvm的运行时信息
    run = mmap(NULL, mmap_size, PROT_READ | PROT_WRITE, MAP_SHARED, vcpufd, 0);
    if (!run)
        err(1, "mmap vcpu");

    // 获取特殊寄存器
    ret = ioctl(vcpufd, KVM_GET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_GET_SREGS");
    // 设置代码段为从地址0处开始，我们的代码被加载到了0x0000的起始位置
    sregs.cs.base = 0;
    sregs.cs.selector = 0;
    // KVM_SET_SREGS 设置特殊寄存器
    ret = ioctl(vcpufd, KVM_SET_SREGS, &sregs);
    if (ret == -1)
        err(1, "KVM_SET_SREGS");


    // 设置代码的入口地址，相当于32位main函数的地址，这里16位汇编都是由0x1000处开始。
    // 如果是正式的镜像，那么rip的值应该是类似引导扇区加载进来的指令
    struct kvm_regs regs = {
        .rip = 0x1000,
        .rax = 2,    // 设置 ax 寄存器初始值为 2
        .rbx = 2,    // 同理
        .rflags = 0x2,   // 初始化flags寄存器，x86架构下需要设置，否则会粗错
    };
    ret = ioctl(vcpufd, KVM_SET_REGS, &regs);
    if (ret == -1)
        err(1, "KVM_SET_REGS");

    // 开始运行虚拟机，如果是qemu-kvm，会用一个线程来执行这个vCPU，并加载指令
    while (1) {
        // 开始运行虚拟机
        ret = ioctl(vcpufd, KVM_RUN, NULL);
        if (ret == -1)
            err(1, "KVM_RUN");
        // 获取虚拟机退出原因
        switch (run->exit_reason) {
        case KVM_EXIT_HLT:
            puts("KVM_EXIT_HLT");
            return 0;
        // 汇编调用了 out 指令，vmx 模式下不允许执行这个操作，所以
        // 将操作权切换到了宿主机，切换的时候会将上下文保存到VMCS寄存器
        // 后面CPU虚拟化会讲到这部分
        // 因为虚拟机的内存宿主机能够直接读取到，所以直接在宿主机上获取到
        // 虚拟机的输出（out指令），这也是后面PCI设备虚拟化的一个基础，DMA模式的PCI设备
        case KVM_EXIT_IO:
            if (run->io.direction == KVM_EXIT_IO_OUT && run->io.size == 1 && run->io.port == 0x3f8 && run->io.count == 1)
                putchar(*(((char *)run) + run->io.data_offset));
            else
                errx(1, "unhandled KVM_EXIT_IO");
            break;
        case KVM_EXIT_FAIL_ENTRY:
            errx(1, "KVM_EXIT_FAIL_ENTRY: hardware_entry_failure_reason = 0x%llx",
                 (unsigned long long)run->fail_entry.hardware_entry_failure_reason);
        case KVM_EXIT_INTERNAL_ERROR:
            errx(1, "KVM_EXIT_INTERNAL_ERROR: suberror = 0x%x", run->internal.suberror);
        default:
            errx(1, "exit_reason = 0x%x", run->exit_reason);
        }
    }
}
```

编译并运行这个demo

```hljs
gcc -g demo.c -o demo
➜  demo1 ./demo
4
KVM_EXIT_HLT
```

## 另外一个简单的QEMU emulator demo

[IBM的徐同学有做过介绍](http://soulxu.github.io/blog/2014/08/11/use-kvm-api-write-emulator/)，在此基础上我再详细介绍一下qemu-kvm的启动过程。

```hljs
.globl _start
    .code16
_start:
    xorw %ax, %ax   # 将 ax 寄存器清零

loop1:
    out %ax, $0x10  # 像 0x10 的端口输出 ax 的内容，at&t汇编的操作数和Intel的相反。
    inc %ax         # ax 值加一
    jmp loop1       # 继续循环
```

这个汇编的作用就是一直不停的向0x10端口输出一字节的值。

从main函数开始说起

```hljs
int main(int argc, char **argv) {
    int ret = 0;
    // 初始化kvm结构体
    struct kvm *kvm = kvm_init();

    if (kvm == NULL) {
        fprintf(stderr, "kvm init fauilt\n");
        return -1;
    }

    // 创建VM，并分配内存空间
    if (kvm_create_vm(kvm, RAM_SIZE) < 0) {
        fprintf(stderr, "create vm fault\n");
        return -1;
    }

    // 加载镜像
    load_binary(kvm);

    // only support one vcpu now
    kvm->vcpu_number = 1;
    // 创建执行现场
    kvm->vcpus = kvm_init_vcpu(kvm, 0, kvm_cpu_thread);

    // 启动虚拟机
    kvm_run_vm(kvm);

    kvm_clean_vm(kvm);
    kvm_clean_vcpu(kvm->vcpus);
    kvm_clean(kvm);
}
```

第一步，调用kvm_init() 初始化了 kvm 结构体。先来看看怎么定义一个简单的kvm。

```hljs
struct kvm {
   int dev_fd;              // /dev/kvm 的句柄
   int vm_fd;               // GUEST 的句柄
   __u64 ram_size;          // GUEST 的内存大小
   __u64 ram_start;         // GUEST 的内存起始地址，
                            // 这个地址是qemu emulator通过mmap映射的地址

   int kvm_version;         
   struct kvm_userspace_memory_region mem; // slot 内存结构，由用户空间填充、
                                           // 允许对guest的地址做分段。将多个slot组成线性地址

   struct vcpu *vcpus;      // vcpu 数组
   int vcpu_number;         // vcpu 个数
};
```

初始化 kvm 结构体。

```hljs
struct kvm *kvm_init(void) {
    struct kvm *kvm = malloc(sizeof(struct kvm));
    kvm->dev_fd = open(KVM_DEVICE, O_RDWR);  // 打开 /dev/kvm 获取 kvm 句柄

    if (kvm->dev_fd < 0) {
        perror("open kvm device fault: ");
        return NULL;
    }

    kvm->kvm_version = ioctl(kvm->dev_fd, KVM_GET_API_VERSION, 0);  // 获取 kvm API 版本

    return kvm;
}
```

第二步+第三步，创建虚拟机，获取到虚拟机句柄，并为其分配内存。

```hljs
int kvm_create_vm(struct kvm *kvm, int ram_size) {
    int ret = 0;
    // 调用 KVM_CREATE_KVM 接口获取 vm 句柄
    kvm->vm_fd = ioctl(kvm->dev_fd, KVM_CREATE_VM, 0);

    if (kvm->vm_fd < 0) {
        perror("can not create vm");
        return -1;
    }

    // 为 kvm 分配内存。通过系统调用.
    kvm->ram_size = ram_size;
    kvm->ram_start =  (__u64)mmap(NULL, kvm->ram_size, 
                PROT_READ | PROT_WRITE, MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, 
                -1, 0);

    if ((void *)kvm->ram_start == MAP_FAILED) {
        perror("can not mmap ram");
        return -1;
    }

    // kvm->mem 结构需要初始化后传递给 KVM_SET_USER_MEMORY_REGION 接口
    // 只有一个内存槽
    kvm->mem.slot = 0;
    // guest 物理内存起始地址
    kvm->mem.guest_phys_addr = 0;
    // 虚拟机内存大小
    kvm->mem.memory_size = kvm->ram_size;
    // 虚拟机内存在host上的用户空间地址，这里就是绑定内存给guest
    kvm->mem.userspace_addr = kvm->ram_start;

    // 调用 KVM_SET_USER_MEMORY_REGION 为虚拟机分配内存。
    ret = ioctl(kvm->vm_fd, KVM_SET_USER_MEMORY_REGION, &(kvm->mem));

    if (ret < 0) {
        perror("can not set user memory region");
        return ret;
    }
    return ret;
}
```

接下来就是load_binary把二进制文件load到虚拟机的内存中来，在第一个demo中我们是直接把字节码放到了内存中，这里模拟镜像加载步骤，把二进制文件加载到内存中。

```hljs
void load_binary(struct kvm *kvm) {
    int fd = open(BINARY_FILE, O_RDONLY);  // 打开这个二进制文件(镜像）

    if (fd < 0) {
        fprintf(stderr, "can not open binary file\n");
        exit(1);
    }

    int ret = 0;
    char *p = (char *)kvm->ram_start;

    while(1) {
        ret = read(fd, p, 4096);           // 将镜像内容加载到虚拟机的内存中
        if (ret <= 0) {
            break;
        }
        printf("read size: %d", ret);
        p += ret;
    }
}
```

加载完镜像后，需要初始化vCPU，以便能够运行镜像内容

```hljs
struct vcpu {
    int vcpu_id;                 // vCPU id，vCPU
    int vcpu_fd;                 // vCPU 句柄
    pthread_t vcpu_thread;       // vCPU 线程句柄
    struct kvm_run *kvm_run;     // KVM 运行时结构，也可以看做是上下文
    int kvm_run_mmap_size;       // 运行时结构大小
    struct kvm_regs regs;        // vCPU的寄存器
    struct kvm_sregs sregs;      // vCPU的特殊寄存器
    void *(*vcpu_thread_func)(void *);  // 线程执行函数
};

struct vcpu *kvm_init_vcpu(struct kvm *kvm, int vcpu_id, void *(*fn)(void *)) {
    // 申请vcpu结构
    struct vcpu *vcpu = malloc(sizeof(struct vcpu));
    // 只有一个 vCPU，所以这里只初始化一个
    vcpu->vcpu_id = 0;
    // 调用 KVM_CREATE_VCPU 获取 vCPU 句柄，并关联到kvm->vm_fd（由KVM_CREATE_VM返回）
    vcpu->vcpu_fd = ioctl(kvm->vm_fd, KVM_CREATE_VCPU, vcpu->vcpu_id);

    if (vcpu->vcpu_fd < 0) {
        perror("can not create vcpu");
        return NULL;
    }

    // 获取KVM运行时结构大小
    vcpu->kvm_run_mmap_size = ioctl(kvm->dev_fd, KVM_GET_VCPU_MMAP_SIZE, 0);

    if (vcpu->kvm_run_mmap_size < 0) {
        perror("can not get vcpu mmsize");
        return NULL;
    }

    printf("%d\n", vcpu->kvm_run_mmap_size);
    // 将 vcpu_fd 的内存映射给 vcpu->kvm_run结构。相当于一个关联操作
    // 以便能够在虚拟机退出的时候获取到vCPU的返回值等信息
    vcpu->kvm_run = mmap(NULL, vcpu->kvm_run_mmap_size, PROT_READ | PROT_WRITE, MAP_SHARED, vcpu->vcpu_fd, 0);

    if (vcpu->kvm_run == MAP_FAILED) {
        perror("can not mmap kvm_run");
        return NULL;
    }

    // 设置线程执行函数
    vcpu->vcpu_thread_func = fn;
    return vcpu;
}
```

最后一步，以上工作就绪后，启动虚拟机。

```hljs
void kvm_run_vm(struct kvm *kvm) {
    int i = 0;

    for (i = 0; i < kvm->vcpu_number; i++) {
        // 启动线程执行 vcpu_thread_func 并将 kvm 结构作为参数传递给线程
        if (pthread_create(&(kvm->vcpus->vcpu_thread), (const pthread_attr_t *)NULL, kvm->vcpus[i].vcpu_thread_func, kvm) != 0) {
            perror("can not create kvm thread");
            exit(1);
        }
    }

    pthread_join(kvm->vcpus->vcpu_thread, NULL);
}
```

启动虚拟机其实就是创建线程，并执行相应的线程回调函数。  
线程回调函数在kvm_init_vcpu的时候传入

```hljs
void *kvm_cpu_thread(void *data) {
    // 获取参数
    struct kvm *kvm = (struct kvm *)data;
    int ret = 0;
    // 设置KVM的参数
    kvm_reset_vcpu(kvm->vcpus);

    while (1) {
        printf("KVM start run\n");
        // 启动虚拟机，此时的虚拟机已经有内存和CPU了，可以运行起来了。
        ret = ioctl(kvm->vcpus->vcpu_fd, KVM_RUN, 0);

        if (ret < 0) {
            fprintf(stderr, "KVM_RUN failed\n");
            exit(1);
        }

        // 前文 kvm_init_vcpu 函数中，将 kvm_run 关联了 vCPU 结构的内存
        // 所以这里虚拟机退出的时候，可以获取到 exit_reason，虚拟机退出原因
        switch (kvm->vcpus->kvm_run->exit_reason) {
        case KVM_EXIT_UNKNOWN:
            printf("KVM_EXIT_UNKNOWN\n");
            break;
        case KVM_EXIT_DEBUG:
            printf("KVM_EXIT_DEBUG\n");
            break;
        // 虚拟机执行了IO操作，虚拟机模式下的CPU会暂停虚拟机并
        // 把执行权交给emulator
        case KVM_EXIT_IO:
            printf("KVM_EXIT_IO\n");
            printf("out port: %d, data: %d\n", 
                kvm->vcpus->kvm_run->io.port,  
                *(int *)((char *)(kvm->vcpus->kvm_run) + kvm->vcpus->kvm_run->io.data_offset)
                );
            sleep(1);
            break;
        // 虚拟机执行了memory map IO操作
        case KVM_EXIT_MMIO:
            printf("KVM_EXIT_MMIO\n");
            break;
        case KVM_EXIT_INTR:
            printf("KVM_EXIT_INTR\n");
            break;
        case KVM_EXIT_SHUTDOWN:
            printf("KVM_EXIT_SHUTDOWN\n");
            goto exit_kvm;
            break;
        default:
            printf("KVM PANIC\n");
            goto exit_kvm;
        }
    }

exit_kvm:
    return 0;
}

void kvm_reset_vcpu (struct vcpu *vcpu) {
    if (ioctl(vcpu->vcpu_fd, KVM_GET_SREGS, &(vcpu->sregs)) < 0) {
        perror("can not get sregs\n");
        exit(1);
    }
    // #define CODE_START 0x1000
    /* sregs 结构体
        x86
        struct kvm_sregs {
            struct kvm_segment cs, ds, es, fs, gs, ss;
            struct kvm_segment tr, ldt;
            struct kvm_dtable gdt, idt;
            __u64 cr0, cr2, cr3, cr4, cr8;
            __u64 efer;
            __u64 apic_base;
            __u64 interrupt_bitmap[(KVM_NR_INTERRUPTS + 63) / 64];
        };
    */
    // cs 为code start寄存器，存放了程序的起始地址
    vcpu->sregs.cs.selector = CODE_START;
    vcpu->sregs.cs.base = CODE_START * 16;
    // ss 为堆栈寄存器，存放了堆栈的起始位置
    vcpu->sregs.ss.selector = CODE_START;
    vcpu->sregs.ss.base = CODE_START * 16;
    // ds 为数据段寄存器，存放了数据开始地址
    vcpu->sregs.ds.selector = CODE_START;
    vcpu->sregs.ds.base = CODE_START *16;
    // es 为附加段寄存器
    vcpu->sregs.es.selector = CODE_START;
    vcpu->sregs.es.base = CODE_START * 16;
    // fs, gs 同样为段寄存器
    vcpu->sregs.fs.selector = CODE_START;
    vcpu->sregs.fs.base = CODE_START * 16;
    vcpu->sregs.gs.selector = CODE_START;

    // 为vCPU设置以上寄存器的值
    if (ioctl(vcpu->vcpu_fd, KVM_SET_SREGS, &vcpu->sregs) < 0) {
        perror("can not set sregs");
        exit(1);
    }

    // 设置寄存器标志位
    vcpu->regs.rflags = 0x0000000000000002ULL;
    // rip 表示了程序的起始指针，地址为 0x0000000
    // 在加载镜像的时候，我们直接将binary读取到了虚拟机的内存起始位
    // 所以虚拟机开始的时候会直接运行binary
    vcpu->regs.rip = 0;
    // rsp 为堆栈顶
    vcpu->regs.rsp = 0xffffffff;
    // rbp 为堆栈底部
    vcpu->regs.rbp= 0;

    if (ioctl(vcpu->vcpu_fd, KVM_SET_REGS, &(vcpu->regs)) < 0) {
        perror("KVM SET REGS\n");
        exit(1);
    }
}
```

运行一下结果，可以看到当虚拟机执行了指令 `out %ax, $0x10` 的时候，会引起虚拟机的退出，这是CPU虚拟化里面将要介绍的特殊机制。  
宿主机获取到虚拟机退出的原因后，获取相应的输出。这里的步骤就类似于IO虚拟化，直接读取IO模块的内存，并输出结果。

```hljs
➜  kvmsample git:(master) ✗ ./kvmsample
read size: 712288
KVM start run
KVM_EXIT_IO
out port: 16, data: 0
KVM start run
KVM_EXIT_IO
out port: 16, data: 1
KVM start run
KVM_EXIT_IO
out port: 16, data: 2
KVM start run
KVM_EXIT_IO
out port: 16, data: 3
KVM start run
KVM_EXIT_IO
out port: 16, data: 4
...
```

## 总结

虚拟机的启动过程基本上可以这么总结：  
创建kvm句柄->创建vm->分配内存->加载镜像到内存->启动线程执行KVM_RUN。从这个虚拟机的demo可以看出，虚拟机的内存是由宿主机通过mmap调用映射给虚拟机的，而vCPU是宿主机的一个线程，这个线程通过设置相应的vCPU的寄存器指定了虚拟机的程序加载地址后，开始运行虚拟机的指令，当虚拟机执行了IO操作后，CPU捕获到中断并把执行权又交回给宿主机。

当然真实的qemu-kvm比这个复杂的多，包括设置很多IO设备的MMIO，设置信号处理等。
