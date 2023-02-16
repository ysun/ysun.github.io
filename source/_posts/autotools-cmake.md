---
title: Autotools 和 cmake 对比
donate: true
date: 2023-02-16 09:43:43
categories:
tags:
---
## 步骤对比
### Autotools
![autotools.jpeg](autotools.jpeg)

* 运行autoscan命令
将configure.scan 文件重命名为configure.ac，并修改configure.ac文件

* 在项目根目录目录下新建Makefile.am文件，并在子目录下也新建makefile.am文件
Automake工具会根据 configure.in 中的参量把 Makefile.am 转换成 Makefile.in 文件。最终通过Makefile.in生成Makefile文件，所以Makefile.am这个文件非常重要，定义了一些生成Makefile的规则

* 在项目根目录下新建NEWS、 README、 ChangeLog 、AUTHORS文件

* 运行aclocal命令
扫描 configure.ac 文件生成 aclocal.m4文件, 该文件主要处理本地的宏定义，它根据已经安装的宏、用户定义宏和 acinclude.m4 文件中的宏将 configure.ac 文件需要的宏集中定义到文件 aclocal.m4 中

* 运行autoconf命令
这个命令将 configure.ac 文件中的宏展开，生成 configure 脚本。这个过程可能要用到aclocal.m4中定义的宏。

* 运行autoheader
。该命令生成 config.h.in 文件。该命令通常会从 "acconfig.h” 文件中复制用户附加的符号定义。该例子中没有附加的符号定义, 所以不需要创建 "acconfig.h” 文件。

* 运行automake -a命令
执行automake --add-missing命令。该命令生成 Makefile.in 文件。使用选项 "--add-missing" 可以让 Automake 自动添加一些必需的脚本文件。如果发现一些文件不存在，可以通过手工 touch命令创建。

* 运行./confiugre脚本
./congigure主要把 Makefile.in 变成最终的 Makefile 文件。configure会把一些配置参数配置到Makefile文件里面。


## CMake
* 编写CMakeLists.txt
* 运行cmake命令

## 简单用法对比
### Autotools
```
# configure.ac

AC_PREREQ([2.69])
AC_INIT([lkvs], [1.0], [])

AM_INIT_AUTOMAKE

AC_CONFIG_SRCDIR([.])

# Checks for programs.
AC_PROG_CC

AC_PROG_RANLIB

# Checks for libraries.

# Checks for header files.

# Checks for typedefs, structures, and compiler characteristics.

# Checks for library functions.

AC_CONFIG_FILES([Makefile
                 th/Makefile
                 xsave/Makefile])
AC_OUTPUT

```

| 标签 | 说明 | 
| ----- | ----- | 
| AC_PREREQ | 声明autoconf要求的版本号 |
| AC_INIT | 定义软件名称、版本号、联系方式 |
| AM_INIT_AUTOMAKE | 必须要的，参数为软件名称和版本号 |
| AC_CONFIG_SCRDIR | 宏用来侦测所指定的源码文件是否存在, 来确定源码目录的有效性.。此处为当前目录。|
| AC_CONFIG_HEADER | 宏用于生成config.h文件，以便 autoheader 命令使用。如果不用autoheader，可以省略 |
| AC_PROG_CC | 指定编译器，默认GCC |
| AC_CONFIG_FILES | 生成相应的Makefile文件，不同文件夹下的Makefile通过空格分隔。例如：AC_CONFIG_FILES([Makefile src/Makefile]) |
| AC_OUTPUT | 用来设定 configure 所要产生的文件，如果是makefile，configure 会把它检查出来的结果带入makefile.in文件产生合适的makefile。|

这里只特别说明一下 AC_CONFIG_FILES 这个宏的作用 (其他宏是必须的, 但是含义比较简单, 具体细节可以查询 Autoconf 的手册)

AC_CONFIG_FILES 指明了需要根据模版生成的 Makefile 文件. 在这个例子中, 需要生成 3 个 Makefile 文件, 每个 Mafile 文件都需要一个模版:

根目录下需要有模版文件 Makefile.in
test 目录下需要有模版文件 Makefile.in
test/funtest 目录下需要有模版文件 Makefile.in
而这3个 Makefile.in 需要用 Automake 通过各自的 Makefile.am 来生成。

```
#Makefile.am

bin_PROGRAMS = funtest1 funtest2

funtest1_SOURCES = funtest1.c ../../src/fun.h ../../src/fun.c
funtest1_CPPFLAGS = -I$(top_srcdir)/src

funtest2_SOURCES = funtest2.c ../../src/fun.h ../../src/fun.c
funtest2_CPPFLAGS = -I$(top_srcdir)/src
```

* bin_PROGRAMS 生成的可执行文件名称。如果生成的可执行文件名称为多个，则可以通过空格的方式分隔。
* funtest1_SOURCES 指明 funtest1 所依赖的源文件 (特别注意, 利用相对路径指明了所依赖的src目录下的源文件)
* funtest1_CPPFLAGS = -I$(top_srcdir)/src 指明了编译时需要指定的头文件路径
* noinst_PROGRAMS：如果make install的时候不想被安装，可以使用noinst_PROGRAMS命令。
* hello_LDADD: 编译成可执行文件过程中，连接所需的库文件，包括*.so的动态库文件和.a的静态库文件。

### CMake
```CMakeLists.txt
# 根目录
cmake_minimum_required(VERSION 3.10)

# Set project name and version
project(LKVS VERSION 1.0)

# Find all subdirectories in the current directory
file(GLOB children RELATIVE ${CMAKE_CURRENT_SOURCE_DIR} ${CMAKE_CURRENT_SOURCE_DIR}/*)

# Run cmake on all subdirectories containing a CMakeLists.txt file
foreach(child ${children})
    if(IS_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/${child})
        if(EXISTS ${CMAKE_CURRENT_SOURCE_DIR}/${child}/CMakeLists.txt)
            execute_process(
                COMMAND cmake .
                WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/${child}
            )
            add_subdirectory(${child})
        endif()
    endif()
endforeach()
```

```
# 子目录MakeLists.txt
cmake_minimum_required(VERSION 3.10)

# Set project name and version
project(th_test VERSION 1.0)

# Find all source files in the current directory
file(GLOB SOURCES *.c *.h)

# Create an executable from the source files
add_executable(th_test ${SOURCES})
```

### CMake CMakeList.txt 详解
```
#表示注释   
#cmake file for project association

#cmake 最低版本要求，低于2.8 构建过程会被终止。   
CMAKE_MINIMUM_REQUIRED(VERSION 2.8)

#定义工程名称
PROJECT(association)
                     
#打印相关消息消息   
#MESSAGE(STATUS "Project: ${PROJECT_NAME}")
#MESSAGE(STATUS "Project Directory: ${PROJECT_SOURCE_DIR}")  

#指定编译类型debug版
SET(CMAKE_BUILE_TYPE DEBUG)
#发行版
#SET(CMAKE_BUILE_TYPE RELEASE)

#SET(CMAKE_C_FLAGS_DEBUG "-g -Wall")          #C
#SET(CMAKE_CXX_FLAGS_DEBUG "-g -Wall")           #C++

#设置C++ 编译
SET(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++11 -s -Wall -W -O3")   
 
#添加子目录   
ADD_SUBDIRECTORY(src/include)

#设置变量，表示所有的源文件  
SET(SOURCE_FILES
    src/main.cpp    
    )


#配置相关库文件的目录，  
LINK_DIRECTORIES(                                  
    /usr/local/lib
    )  

#找BZip2
FIND_PACKAGE(BZip2)
if (BZIP2_FOUND)
    MESSAGE(STATUS "${BZIP_INCLUDE_DIRS}")  
    MESSAGE(STATUS " ${BZIP2_LIBRARIES}")  
endif (BZIP2_FOUND)
if (NOT BZIP2_FOUND)
    MESSAGE(STATUS "NOT  BZIP2_FOUND")  
endif (NOT  BZIP2_FOUND)


#相关头文件的目录
INCLUDE_DIRECTORIES(  
     /usr/local/include  
     ${PROJECT_SOURCE_DIR}/utility_inc
     ${BZIP_INCLUDE_DIRS}
    )

#链接库
LINK_LIBRARIES(
    ${PROJECT_SOURCE_DIR}/static_libs/libSentinelKeys64.a
    ${BZIP2_LIBRARIES}
    )

#生成可执行文件
ADD_EXECUTABLE(${PROJECT_NAME} ${SOURCE_FILES})

#依赖的库文件  
TARGET_LINK_LIBRARIES(${PROJECT_NAME} eventloop)
```
子目录CMakeLists.txt 文件编写
```
SET(EVENTLOOP_SOURCE_FILES
        tool/BlockingQueue.hpp
        tool/Copyable.h
        tool/ExecuteState.h
        tool/Likely.h
        EventLoop.h
        EventLoop.cpp
        )
#生成静态链接库eventloop 
ADD_LIBRARY(eventloop ${EVENTLOOP_SOURCE_FILES})

```

## 参考文档
[autoconf官方手册](http://www.gnu.org/software/autoconf)
[automake官方手册](http://www.gnu.org/software/automake)
[autotools比较流行的文档](https://www.lrde.epita.fr/~adl/autotools.html)
