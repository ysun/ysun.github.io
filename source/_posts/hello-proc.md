---
title: 一个可读可写的procfs模板,基于kernel-5.12
donate: true
date: 2021-06-29 10:39:40
categories:
tags: kernel
---

一个最简单的内核模块，其中创建一个最简单的可读可写的proc fs的模板，供大家参考和备忘。
首先创建一个文件，或者干脆把新模块文件放在`<linux source>/fs/proc/`文件夹中，命名`debug_sy.c`
```
#include <linux/module.h>       /* Specifically, a module */
#include <linux/kernel.h>       /* We're doing kernel work */
#include <linux/proc_fs.h>      /* Necessary because we use the proc fs */
#include <asm/uaccess.h>        /* for copy_from_user */
#include <linux/seq_file.h>     //using seq_printf
#include <linux/slab.h>         // Using kzalloc

#define PROCFS_NAME             "debug_sy"

MODULE_AUTHOR("Yi Sun");
static char *str = NULL;

static int my_proc_show(struct seq_file *m,void *v){
        seq_printf(m,"%s\n",str);
        return 0;
}

static ssize_t my_proc_write(struct file* file,const char __user *buffer,size_t count,loff_t *f_pos){
        char *tmp = kzalloc((count+1),GFP_KERNEL);
        if(!tmp)return -ENOMEM;
        if(copy_from_user(tmp,buffer,count)){
                kfree(tmp);
                return EFAULT;
        }
        kfree(str);
        str=tmp;
        return count;
}

static int my_proc_open(struct inode *inode,struct file *file){
        return single_open(file,my_proc_show,NULL);
}

static const struct proc_ops my_fops={
        .proc_open = my_proc_open,
        .proc_release = single_release,
        .proc_read = seq_read,
        .proc_lseek = seq_lseek,
        .proc_write = my_proc_write
};

static int __init hello_init(void){
        struct proc_dir_entry *entry;
        entry = proc_create(PROCFS_NAME,0777,NULL,&my_fops);
        if(!entry){
                return -1;
        }else{
                printk(KERN_INFO "create proc file successfully\n");
        }
        return 0;
}

static void __exit hello_exit(void){
        remove_proc_entry(PROCFS_NAME,NULL);
        printk(KERN_INFO "Goodbye world!\n");
}

module_init(hello_init);
module_exit(hello_exit);
MODULE_LICENSE("GPL");
```

如果单独的文件，创建一个`Makefile`文件：
```
obj-m += debug_sy.o

all:
        make -C /lib/modules/$(shell uname -r)/build M=$(PWD) modules
clean:
        make -C /lib/modules/$(shell uname -r)/build M=$(PWD) clean
```
如果直接放在`fs/proc中`，修改文件夹中的Makefile:
```
 proc-y += namespaces.o
 proc-y += self.o
 proc-y += thread_self.o
+proc-y += debug_sy.o
 proc-$(CONFIG_PROC_SYSCTL)     += proc_sysctl.o
 proc-$(CONFIG_NET)             += proc_net.o
 proc-$(CONFIG_PROC_KCORE)      += kcore.o
```

然后就可以make，insmod了。
