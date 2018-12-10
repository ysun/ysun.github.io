---
title: QMP 简介
date: 2018-12-10 21:42:39
categories: QEMU
tags: [QEMU, QMP]
donate: true
---

## 什么是QMP协议##
QMP，即QEMU Machine Protocol，就是qemu虚拟机中的一种协议，是qemu的一部分。qmp是基于json格式的一整套协议，通过这套协议我们可以控制qemu虚拟机实例的整个生命周期，包括挂起、暂停、快照、查询、外设的热插拔等，以及最简单的查询，都可以通过qmp实现。 有多种方法使用qmp，这里简要介绍通过tcp和unix socket使用qmp。

## QMP协议有哪些特征##
1）轻量、基于文本、指令格式易于解析，因为它是json格式的；
2）支持异步消息，主要指通过qmp发送给虚拟机的指令支持异步；
3）Capabilities Negotiation，主要指我们初次建立qmp连接时，进入了capabilities negotiation模式,这时我们不能发送任何指令，除了qmp_capabilities指令，发送了qmp_capabilitie指令，我们就退出了capabilities negotiation模式，进入了指令模式（command mode），这时我们可以发送qmp指令，如{ "execute": "query-status" }，这样就可以查询虚拟机的状态。

## QMP协议有哪些模式##
 有两种模式：Capabilities Negotiation模式和Command模式。

## 那么该如何建立qmp连接呢 ##
这里简要介绍通过tcp和unix socket使用qmp。

### 通过TCP使用QMP ###
使用-qmp添加qmp相关参数：

``` bash
./qemu-system-x86_64 -m 2048 -hda /root/centos6.img -enable-kvm -qmp tcp:localhost:1234,server,nowait
```
新开一个终端使用telnet 链接localhost：1234

``` bash
telnet localhost 1234
```
之后就可以使用qmp的命令和虚拟机交互了

```
[root@localhost ~]# telnet localhost 1234
Trying ::1...
Connected to localhost.
Escape character is '^]'.
{"QMP": {"version": {"qemu": {"micro": 0, "minor": 6, "major": 2}, "package": ""}, "capabilities": []}}
{ "execute": "qmp_capabilities" }
{"return": {}}
{ "execute": "query-status" }
{"return": {"status": "running", "singlestep": false, "running": true}}
```

### 通过unix socket使用QMP ###
使用unix socket创建qmp：

```
./qemu-system-x86_64 -m 2048 -hda /root/centos6.img -enable-kvm -qmp unix:/tmp/qmp-test,server,nowait
```

使用nc连接该socket:

```
nc -U /tmp/qmp-test
```

之后就一样了。

```
[root@localhost qmp]# nc -U /tmp/qmp-test
{"QMP": {"version": {"qemu": {"micro": 0, "minor": 6, "major": 2}, "package": ""}, "capabilities": []}}
{ "execute": "qmp_capabilities" }
{"return": {}}
{ "execute": "query-status" }
{"return": {"status": "running", "singlestep": false, "running": true}}
```

QMP的详细命令格式可以在qemu的代码树主目录下面的qmp-commands.hx中找到。

### 自动批量发送QMP命令

可以通过下面这个脚本给QEMU虚拟机发送命令。这对于测试虚拟机的一些功能是很有用的。试了一下，对于unix socket的方法能使用的，对于tcp连接的方法没有使用成功。

```
# QEMU Monitor Protocol Python class
#
# Copyright (C) 2009 Red Hat Inc.
#
# This work is licensed under the terms of the GNU GPL, version 2.  See
# the COPYING file in the top-level directory.

import socket, json, time, commands
from optparse import OptionParser

class QMPError(Exception):
    pass

class QMPConnectError(QMPError):
    pass

class QEMUMonitorProtocol:
    def connect(self):
        print self.filename
        self.sock.connect(self.filename)
        data = self.__json_read()
        if data == None:
            raise QMPConnectError
        if not data.has_key('QMP'):
            raise QMPConnectError
        return data['QMP']['capabilities']

    def close(self):
        self.sock.close()

    def send_raw(self, line):
        self.sock.send(str(line))
        return self.__json_read()

    def send(self, cmdline, timeout=30, convert=True):
        end_time = time.time() + timeout
        if convert:
            cmd = self.__build_cmd(cmdline)
        else:
            cmd = cmdline
	    print("*cmdline = %s" % cmd)
        print cmd
        self.__json_send(cmd)
        while time.time() < end_time:
            resp = self.__json_read()
            if resp == None:
                return (False, None)
            elif resp.has_key('error'):
                return (False, resp['error'])
            elif resp.has_key('return'):
                return (True, resp['return'])

    def read(self, timeout=30):
        o = ""
        end_time = time.time() + timeout
        while time.time() < end_time:
            try:
                o += self.sock.recv(1024)
                if len(o) > 0:
                    break
            except:
                time.sleep(0.01)
        if len(o) > 0:
            return json.loads(o)
        else:
            return None

    def __build_cmd(self, cmdline):
        cmdargs = cmdline.split()
        qmpcmd = { 'execute': cmdargs[0], 'arguments': {} }
        for arg in cmdargs[1:]:
            opt = arg.split('=')
            try:
                value = int(opt[1])
            except ValueError:
                value = opt[1]
            qmpcmd['arguments'][opt[0]] = value
	print("*cmdline = %s" % cmdline)
        return qmpcmd

    def __json_send(self, cmd):
        # XXX: We have to send any additional char, otherwise
        # the Server won't read our input
        self.sock.send(json.dumps(cmd) + ' ')

    def __json_read(self):
        try:
            return json.loads(self.sock.recv(1024))
        except ValueError:
            return

    def __init__(self, filename, protocol="tcp"):
        if protocol == "tcp":
            self.filename = ("localhost", int(filename))
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        elif protocol == "unix":
            self.filename = filename
            print self.filename
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        #self.sock.setblocking(0)
        self.sock.settimeout(5)

if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option('-n', '--num', dest='num', default='10', help='Times want to try')
    parser.add_option('-f', '--file', dest='port', default='4444', help='QMP port/filename')
    parser.add_option('-p', '--protocol', dest='protocol',default='tcp', help='QMP protocol')
    def usage():
        parser.print_help()
        sys.exit(1)

    options, args = parser.parse_args()

    print options
    if len(args) > 0:
        usage()

    num = int(options.num)
    qmp_filename = options.port
    qmp_protocol = options.protocol
    qmp_socket = QEMUMonitorProtocol(qmp_filename,qmp_protocol)
    qmp_socket.connect()
    qmp_socket.send("qmp_capabilities")
    qmp_socket.close()

##########################################################
#Usage
#Options:
#  -h, --help            show this help message and exit
#  -n NUM, --num=NUM     Times want to try
#  -f PORT, --file=PORT  QMP port/filename
#  -p PROTOCOL, --protocol=PROTOCOL
#                        QMP protocol
# e.g: # python xxxxx.py -n $NUM -f $PORT
##########################################################
```
## 参考文档 ##
关于QMP更详细的文档，可以参考其官方文档：
https://wiki.qemu.org/Documentation/QMP


