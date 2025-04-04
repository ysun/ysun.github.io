---
title: 如何使用Mutt收取office365邮件
donate: true
date: 2025-04-04 13:55:30
categories: office
tags: mutt
---
很多朋友工作在Linux上，但工作邮件是office365的。很多时候在Linux上使用图形化的邮件客户端不太方便，或者说不太好用。今天就来介绍一下如何在Linux上使用Mutt收取office365的邮件。

## 创建 gpg keyring
```bash
gpg --gen-key
```
![](gpg.png)

## 下载mutt_oauth2.py
```bash
https://gitlab.com/muttmua/mutt/-/blob/master/contrib/mutt_oauth2.py
```

## 编辑mutt_oauth2.py

修改microsoft section用下面的固定值:
```bash
  'client_id': '08162f7c-0fd2-4200-a84a-f25a4db0b584',
  'client_secret': 'TxRBilcHdC6WGBee]fs?QR:SJ8nI[g82',
```
填写USER-ID: (上图中红色下划线）
As following: 
```
ENCRYPTION_PIPE = ['gpg', '--encrypt', '--recipient', 'sunyi <yi.sun@xxx.com>']
```

## 运行mutt_oauth2.py 生成token文件
```bash
 ./mutt_oauth2.py yi.sun@xxx.com.tokens --verbose --authorize

```
![](mutt_oauth2.png)

如图，要求点击链接进行授权。点击后会打开一个浏览器窗口，登录授权，完成后会提示授权成功。然后生成一个token文件。

## 配置muttrc

```bash
set folder=imaps://yi.sun@xxx.com@outlook.office365.com:993/
set imap_user=yi.sun@xxx.com
set imap_authenticators="xoauth2"
set imap_oauth_refresh_command='~/.mutt/mutt_oauth2.py ~/.mutt/yi.sun@xxx.com.tokens'
set smtp_authenticators="xoauth2"
set smtp_oauth_refresh_command='~/.mutt/mutt_oauth2.py ~/.mutt/yi.sun@xxx.com.tokens'
set smtp_url=smtp://yi.sun@xxx.com@outlook.office365.com:587
```

## 参考链接
https://gitlab.com/muttmua/mutt/-/blob/master/contrib/mutt_oauth2.py.README
https://hg.mozilla.org/comm-central/file/tip/mailnews/base/src/OAuth2Providers.jsm

