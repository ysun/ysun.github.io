---
title: OpenWrt PassWall2 配置
donate: true
date: 2026-03-06 17:39:17
categories:
tags:
---
## 前述

场景：
- 需要 IPv6（如 iTV 聚合场景）
- 需要可用的代理访问能力
- 设备为光猫桥接 + 主路由拨号 + OpenWrt 旁路由

插件对比后选择 PassWall2，目标是：
- 降低/避免 DNS 泄露
- IPv4 + IPv6 双栈共存
- 兼顾常规上网与代理需求

## 配置步骤

### 一、规则管理
1. 删除所有默认规则，添加 3 条规则：Reject、Direct、Proxy
![规则管理-1](./rulemgr1.png)

2. Reject 规则域名：`geosite:category-ads-all`
![规则管理-2](./rulemgr2-reject.png)

3. Direct 规则：
   - 域名：`xn--ngstr-lra8j.com`、`geosite:private`、`geosite:cn`
   - IP：`geoip:private`、`geoip:cn`
![规则管理-3](./rulemgr3-direct.png)

4. Proxy 规则域名：`geosite:geolocation-!cn`
![规则管理-4](./rulemgr4-proxy.png)

5. 规则顺序必须为：Reject → Direct → Proxy

注释：

- geosite:category-ads-all	去广告
- xn–ngstr-lra8j.com		谷歌商店
- geosite:private		内网地址
- geosite:cn			国内域名
- geoip:private			内网IP
- geoip:cn			国内IP
- geosite:geolocation-!cn	国外域名

### 二、高级设置（其他设置）

- 不使用 UDP 代理时，UDP 不转发端口可设为“所有”
- TCP 转发端口建议“仅网页”（80/443）
- TCP 代理方式可用 REDIRECT 或 TPROXY
- 若节点支持 IPv6 出口，可开启 IPv6 透明代理（TProxy）

配图：

![高级设置](./otherconfig.png)

### 三、节点配置（Xray 分流）

新创建一个“分流总节点”：

- Reject → 黑洞（丢弃）
- Direct → 直连（绕过）
- Proxy → 默认（代理）
- 默认规则 → 按需选择节点
- 域名解析策略 → `AsIs`（仅匹配域名）

配图：

![Xray分流](./mainnode.png)

### 四、基本设置

#### 1) DNS 设置

- 远程 DNS 协议：DOH
- 远程 DNS 出站：远程（走代理）
- 勾选 FakeDNS

说明：
- 远程DNS出站一定要设置为：远程（走代理），不然你走直连大概率是不通的，但是DOH走代理都是会增加延迟
- 勾选FakeDNS后，在Proxy规则内的域名，匹配上的会返回一个假IP作为DNS响应（例如198.18.0.0/16），最后将域名请求发送给节点服务器VPS在它的网络环境中进行解析IP
- 不在Proxy规则内的域名则会使用设置的CloudFlare远程DNS进行本地DNS解析真实IP，最后将这个真实IP发送给节点服务器VPS，而如果遇到解析出的是被污染的IP，由于开启了嗅探功能，会探测HTTP请求里的域名，所以就算本地解析出的IP是被污染也不影响
- 如何判断是走FakeDNS还是走远程DNS，电脑运行CMD窗口，输入 nslookup youtube.com 回车，输入 nslookup ipleak.net 回车

配图：

![DNS设置](./basicdns.png)

#### 2) 主要项

- 节点—Xray 分流选择“分流总节点”

配图：

![主要项](./mainnode.png)

#### 3) 主开关

- 完成以上配置后，打开主开关并保存应用

original from: [Pass Wall2解决DNS泄露IPv4+IPv6双栈共存配置教程](https://mtom.top/archives/Pass-Wall2%E8%A7%A3%E5%86%B3DNS%E6%B3%84%E9%9C%B2IPv4-IPv6%E5%8F%8C%E6%A0%88%E5%85%B1%E5%AD%98%E9%85%8D%E7%BD%AE%E6%95%99%E7%A8%8B/)
