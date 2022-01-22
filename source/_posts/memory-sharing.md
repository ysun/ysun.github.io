---
title: POSIX 和 System V 内存共享用法
donate: true
date: 2022-01-22 09:04:06
categories: Linux 
tags: Linux
---

## 名词解释
POSIX: Portable Operating System Interface
A cross-platform specification supported by UNIX operating systems and those considered UNIX-like, such as Linux. The X in the name originally denoted that the interface was "based on UNIX."

System V
The specification that defines the requirements for an operating system to be considered UNIX.

*下表列出了System V IPC 和 POSIX IPC的区别：*

| SYSTEM V | POSIX |
|--------|-------|
|AT & T introduced (1983) three new forms of IPC facilities namely message queues, shared memory, and semaphores | Portable Operating System Interface standards specified by IEEE to define application programming interface (API). POSIX covers all the three forms of IPC|
|SYSTEM V IPC covers all the IPC mechanisms viz., pipes, named pipes, message queues, signals, semaphores, and shared memory. It also covers socket and Unix Domain sockets. | Almost all the basic concepts are the same as System V. It only differs with the interface |
|Shared Memory Interface Calls shmget(), shmat(), shmdt(), shmctl()   | Shared Memory Interface Calls shm_open(), mmap(), shm_unlink() |
|Message Queue Interface Calls msgget(), msgsnd(), msgrcv(), msgctl() | Message Queue Interface Calls mq_open(), mq_send(), mq_receive(), mq_unlink() |
|Semaphore Interface Calls semget(), semop(), semctl()                | Semaphore Interface Calls Named Semaphores sem_open(), sem_close(), sem_unlink(), sem_post(), sem_wait(), sem_trywait(), sem_timedwait(), sem_getvalue() Unnamed or Memory based semaphores sem_init(), sem_post(), sem_wait(), sem_getvalue(),sem_destroy()|
|Uses keys and identifiers to identify the IPC objects.               | Uses names and file descriptors to identify IPC objects |
|NA                                                                   | POSIX Message Queues can be monitored using select(), poll() and epoll APIs |
|Offers msgctl() call                                                 | Provides functions (mq_getattr() and mq_setattr()) either to access or set attributes 11. IPC - System V & POSIX |
|NA                                                                   | Multi-thread safe. Covers thread synchronization functions such as mutex locks, conditional variables, read-write locks, etc. |
|NA                                                                   | Offers few notification features for message queues (such as mq_notify()) |
|Requires system calls such as shmctl(), commands (ipcs, ipcrm) to perform status/control operations. | Shared memory objects can be examined and manipulated using system calls such as fstat(), fchmod() |
|The size of a System V shared memory segment is fixed at the time of creation (via shmget())         | We can use ftruncate() to adjust the size of the underlying object, and then re-create the mapping using munmap() and mmap() (or the Linux-specific mremap()) |

## 实例！
话不多说，来分别看两个实例吧:

### POSIX IPC
```c
//C program for Producer process illustrating POSIX shared-memory API.

#include <time.h>
#include <unistd.h>
#include <string.h>
#include <stdio.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <stdlib.h>
#include <sys/stat.h>        /* For mode constants */
#include <fcntl.h>           /* For O_* constants */

#define SHM_FILE "/apc.shm.kashyap"

void lg(const char *oper, int result) {
  printf("%s %d\n", oper, result);
  if (result < 0) {
    perror(oper);
  }
}

void child(char *result) {
  for (int i = 0; i < 50; ++i) {
    strcpy(result, "child ::: hello parent\n");
    usleep(2);
    printf("child ::: %s", result);
  }
  usleep(5);
}

void parent(char *result) {
  usleep(1);
  for (int i = 0; i < 50; ++i) {
    strcpy(result, "parent ::: hello child\n");
    usleep(2);
    printf("parent ::: %s", result);
  }
  usleep(5);
}

int main() {
  int integerSize = 1024 * 1024 * 256; //256 mb
  
  int descriptor = -1; 
  int mmap_flags = MAP_SHARED;

#ifdef SHM
  // Open the shared memory.
  descriptor = shm_open(SHM_FILE, 
      O_CREAT | O_RDWR, S_IRUSR | S_IWUSR);

  // Size up the shared memory.
  ftruncate(descriptor, integerSize);
#else
  //descriptor = -1;
  descriptor = creat("/dev/zero", S_IRUSR | S_IWUSR);
  mmap_flags |= MAP_ANONYMOUS;
#endif
  char *result = mmap(NULL, integerSize, 
      PROT_WRITE | PROT_READ, mmap_flags, 
      descriptor, 0 );

  perror("mmap");
  printf("%X\n", result);

  pid_t child_pid = fork();

  switch(child_pid) {
    case 0:
      child(result);
      break;
    case -1:
      lg("fork", -1);
      break;
    default:
      parent(result);
  }

  lg("msync", msync(result, integerSize, MS_SYNC));
  lg("munmap", munmap(result, integerSize));

  usleep(500000);

#ifdef SHM
  if (child_pid != 0) {
    lg("shm_unlink", shm_unlink(SHM_FILE));
  }
#endif

  return 0;
}
```
编译命令：
```
gcc ipc_posix.c -o ipc_posix -lrt
```

### System V IPC

```c
#include <stdio.h> 
#include <sys/shm.h> 
#include <sys/stat.h> 

int main () 
{
  int segment_id; 
  char* shared_memory; 
  struct shmid_ds shmbuffer; 
  int segment_size; 
  const int shared_segment_size = 0x6400; 

  /* Allocate a shared memory segment.  */ 
  segment_id = shmget (IPC_PRIVATE, shared_segment_size, 
                 IPC_CREAT | IPC_EXCL | S_IRUSR | S_IWUSR); 
  /* Attach the shared memory segment.  */ 
  shared_memory = (char*) shmat (segment_id, 0, 0); 
  printf ("shared memory attached at address %p\n", shared_memory); 
  /* Determine the segment's size. */ 
  shmctl (segment_id, IPC_STAT, &shmbuffer); 
  segment_size  =               shmbuffer.shm_segsz; 
  printf ("segment size: %d\n", segment_size); 
  /* Write a string to the shared memory segment.  */ 
  sprintf (shared_memory, "Hello, world."); 
  /* Detach the shared memory segment.  */ 
  shmdt (shared_memory); 

  /* Reattach the shared memory segment, at a different address.  */ 
  shared_memory = (char*) shmat (segment_id, (void*) 0x5000000, 0); 
  printf ("shared memory reattached at address %p\n", shared_memory); 
  /* Print out the string from shared memory.  */ 
  printf ("%s\n", shared_memory); 
  /* Detach the shared memory segment.  */ 
  shmdt (shared_memory); 

  /* Deallocate the shared memory segment.  */ 
  shmctl (segment_id, IPC_RMID, 0); 

  return 0; 
} 
```

编译命令：
```
gcc ipc_sysv.c -o ipc_sysv
```

## Refence
[UNIX System V](https://en.wikipedia.org/wiki/UNIX_System_V)
[System V & Posix](https://www.tutorialspoint.com/inter_process_communication/inter_process_communication_system_v_posix.htm)
[Linux kernel interfaces](https://en.wikipedia.org/wiki/Linux_kernel_interfaces#Additions_to_POSIX)
[How to use shared memory with Linux in C](https://stackoverflow.com/questions/5656530/how-to-use-shared-memory-with-linux-in-c)
