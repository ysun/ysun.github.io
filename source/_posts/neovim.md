---
title: 打造完美内核开发IDE -- neovim
donate: true
date: 2023-06-14 20:32:30
categories: Linux
tags: Linux
---

工作在Linux下的小伙伴可以说对VIM是又爱又恨。今天，用半小时时间让同学们对vim只留下爱，不再有恨。

## 下载和安装neovim
### 下载
neovim的下载地址： https://github.com/neovim/neovim/releases/tag/stable
下载[nvim-linux64.tar.gz](https://github.com/neovim/neovim/releases/download/stable/nvim-linux64.tar.gz) stable版的预编译包。

BTW，不要安装系统自带的neovim，版本太老了，会导致后面的配置失败的。

### 安装
解压缩刚刚下载的压缩包: `tar xzvf nvim-linux64.tar.gz`
当然跑到解压缩后的目录中直接运行，但这并不方便。为了让生活更容易，这里提供两种简单方便的安装方法：
1. 设置环境变量PATH
编译文件 `~/.bashrc`，可以在文件的末尾处添加一行:
```
export <path of nvim-linux>:$PATH
```
这样的好处是，操作简单。但博主本人并不喜欢这样做，因为回头软件一多，需要维护好多PATH变量的export，同时安装文件也容易到处都是。
个人推荐第二种方法。
2. 安装到系统目录中
通常系统中有几个目录默认在变量`PATH`中了，可以通过`echo $PATH`看到那些路径可以被默认遍历到。从中挑一个喜欢的，我通常会把安装的软件放在`/usr/local/bin`中。然后利用rsync工具：
```
rsync -avz <path to nvim-linux> /usr/local/     #注意，这里没有bin
```
这样所有文件夹结构都会同步到系统的文件夹中。

不管哪种方式安装好neovim之后，建议重新开一个Terminal，试下nvim是不是工作了。而博主比较激进一点，直接在刚刚安装nvim的系统目录中创建一个软连接:
```
ln -s nvim vim
```
这么做是为了直接覆盖掉系统中原来安装的vim。如果日常使用git, mutt 之类的依赖于vim的工具，那么现在使用那些工具的时候，也一并将用nvim代替掉vim，快哉！


## 配置
博主使用vim大概有15个年头了，提到vim的配置，也是头皮发紧，真心不敢折腾vim的配置。但，nvim不一样了，单个插件变强了很多，而且，现在又有GPT的加持。
总之，来吧保证不虚此行，半小时结束战斗！

### 创建配置文件
由于我们是手动安装nvim应用，所有，同样需要手动为其创建配置文件。幸运的是，可以直接clone博主的配置。（博主也是参考其他大神的配置）
```
git clone  https://github.com/ysun/nvim ~/.config/nvim
```

### 启动VIM
是不是很意外，这就结束了？昂，对于配置这就结束了！运行`nvim`或者你也创建了软连接的话，运行`vim`。在首次运行的时候，会自动安装所有配置文件中的插件。

## 使用
可以从插件配置文件查看具体使用了那些插件`~/.config/nvim/lua/plugins.lua`。所有插件都是使用包管理`packer`安装的。一共大概20几个。
这里简单说下快捷键吧。

### nvim-tree
`tt`可以呼出nvim-tree，显示当前文件夹结构。

### lsp
使用lsp自动补全。lsp需要一个文件`compile_commands.json`，手动执行内核代码中的脚本
```
scripts/clang-tools/gen_compile_commands.py
```
即可生成。
** lsp 需要安装一个服务 clangd **
Ubuntu 中这样安装：
```
apt install clangd
```
### nvim-telescope
我的理解，这个插件是lsp的前端，可以方便的进行跳转
`ctrl+j -> ctrl+s`： 跳转到函数的引用
`ctrl+j -> ctrl+g`： 跳转到函数的定义

### tabnine-nvim
这个插件其实是我开始neovim的最开始的动力。他是github copilot的平替。虽然也是付费软件，但免费也可以使用，就暂时官网github copilot了。
它会自动预测将要输入的单词，使用`tab`键自动补全。这里有点小冲突，lsp也会自动补全，但lsp只是自动补全代码,而tabnine-nvim是一个AI工具，它除了可以帮忙补全注释之外，还可以补全注释下面的整段函数。

### Chatgpt.nvim
无论在插入状态、normal状态、还是visual状态，都可以输入
```
:Chatgpt
```
呼出Chatgpt 的功能，包括ChatGPT、ChatGPTActAs、ChatGPTCompleteCode、ChatGPTEditWithInstructions、ChatGPTRun 等命令，各个命令下还有子命令。详细介绍参考官网`https://github.com/jackMort/ChatGPT.nvim`
ChatGPT是需要OpenAI的API Key，所以每一条调用都是付费的，大家酌情使用。

### 更新插件
如果对插件的配置有更新，可以两个方法来更新插件：
- lua脚本
```
:lua require("packer").sync()
```

- 重建share/nvim
安装的插件默认都放在目录`~/.local/share/nvim`中，如果想重建插件的话，可以简单的全部删除，然后在下次打开vim的时候会自动重建插件。
```
rm -rf ~/.local/share/nvim
```
![nvim](nvim.png)
