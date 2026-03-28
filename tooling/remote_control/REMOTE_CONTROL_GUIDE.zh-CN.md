# Remote Control 使用总览

## 文档关系

这份文档是 `tooling/remote_control/` 当前的中文主文档，用来统一说明：

- 本地构建与 `.local` 配置
- 飞书 MVP 接入
- 本地与远程共享 Codex 会话

配套文档关系如下：

- 框架初始化：
  - [AI_AGENT_SETUP.md](../../AI_AGENT_SETUP.md)
- Harness 更新 / 重编流程：
  - [Harness_Update_Guide.md](../../Harness_Update_Guide.md)

## 适用范围

本目录当前负责 3 类能力：

- `cc-connect` 的本地补丁构建与运行
- 飞书 / 远程控制接入
- 本地手动 Codex 与远程聊天之间的共享会话

明确不包含：

- `auto_iterate` 运行时会话共享

`auto_iterate` 仍然保持独立，这样 phase 日志、错误定位和恢复逻辑不会被共享上下文污染。

## 推荐阅读顺序

如果你是新 workspace 第一次接入：

1. [AI_AGENT_SETUP.md](../../AI_AGENT_SETUP.md)
2. 本文的“1. 本地构建与配置”
3. 本文的“2. 飞书 MVP 接入”
4. 本文的“3. 共享会话模型”

如果你已经接好，只是在维护：

1. [Harness_Update_Guide.md](../../Harness_Update_Guide.md)
2. 本文的“1. 本地构建与配置”
3. 本文的“3. 共享会话模型”

## 当前整体能力

当前阶段已经落地的功能是：

- 当前 workspace 使用 repo-local 的 `data_dir`
- 支持本地构建 patched `cc-connect`
- 支持飞书入口、`/home` 工作台卡片、`/ai` auto-iterate wrapper
- 远程聊天默认进入共享会话体系
- 本地通过 `codex_all` / `cw` 默认进入共享会话体系
- 本地支持 `codex_all next` 自动切到另一个账号并续同一个 slot
- 本地交互式 Codex 启动前，会把跨账号 transcript 镜像到当前 `CODEX_HOME`
- 原生 Codex 终端中的 `/resume` 也能看到这些已镜像会话

## 0. `codex_all` 命令到底在哪里

如果你在拉取仓库后想确认 `codex_all` 是怎么来的，当前结构是：

- 最外层入口：
  - [tooling/remote_control/bin/codex_all](./bin/codex_all)
- 实际本地命令分发：
  - [tooling/remote_control/bin/cw](./bin/cw)
- 真正的共享会话 CLI 逻辑：
  - [tooling/remote_control/cc_connect_src/cmd/cc-connect/share.go](./cc_connect_src/cmd/cc-connect/share.go)

也就是说：

- `codex_all` 本身只是一个很薄的 wrapper
- `cw` 负责把你的输入翻译成 `cc-connect share ...`
- 真正的共享 slot、切号、resume、lease 逻辑都在 `share.go`

之前的问题点在于：

- repo 里虽然有 `tooling/remote_control/bin/codex_all`
- 但把它变成“全局可用命令”的动作只做在本机 `~/.bashrc`
- 这一步不属于仓库内容，所以别人拉取后不能靠文档独立完成配置

现在这部分已经补成仓库内步骤，见下面的“1.7 安装本地命令到 PATH”。

## 1. 本地构建与配置

### 1.1 提交边界

应该提交：

- `tooling/remote_control/cc_connect_src/` 下的源码修改
- `tooling/remote_control/` 下的脚本、模板、文档
- 不含密钥的模板配置

不要提交：

- `tooling/remote_control/vendor/go/`
- `tooling/remote_control/vendor/bin/cc-connect*`
- `tooling/remote_control/config/*.local.toml`
- `tooling/remote_control/config/*.local.yaml`
- 任何包含 `app_secret`、`open_id`、私有路径的本地配置

### 1.2 关键目录

- 源码：
  - [cc_connect_src](./cc_connect_src)
- 构建脚本：
  - [build_patched_cc_connect.sh](./scripts/build_patched_cc_connect.sh)
  - [install_user_commands.sh](./scripts/install_user_commands.sh)
- wrapper：
  - [cc-connect](./bin/cc-connect)
  - [codex_all](./bin/codex_all)
  - [cw](./bin/cw)
- 模板：
  - [cc_connect.local.example.toml](./config/templates/cc_connect.local.example.toml)
  - [cc_connect_feishu_codex.example.toml](./config/templates/cc_connect_feishu_codex.example.toml)
- 本地配置：
  - [cc_connect.local.toml](./config/cc_connect.local.toml)

### 1.3 当前 workspace 的本地配置重点

推荐把运行态固定成 repo-local：

- `data_dir = "<workspace-root>/.cc-connect"`

这意味着：

- 共享 slot
- lease
- local slot binding
- provider cooldown

都会落在当前仓库自己的 `.cc-connect/` 下，而不是全局 `~/.cc-connect`。

### 1.4 从模板生成本地配置

```bash
cp tooling/remote_control/config/templates/cc_connect.local.example.toml \
  tooling/remote_control/config/cc_connect.local.toml
```

如果你本地已经有 `tooling/remote_control/config/cc_connect.local.toml`，
不要直接覆盖。更稳的做法是基于现有文件原地修改：

1. 先保留你现有的密钥、`allow_from`、`admin_from`、`CODEX_HOME`
2. 再对照模板和下面这份 checklist 把 workspace 相关字段改对

建议重点检查：

- `data_dir = "<workspace-root>/.cc-connect"`
- `projects.name = "<workspace-name>"`
- `projects.agent.options.work_dir = "<workspace-root>"`
- 每个 `[[commands]].work_dir = "<workspace-root>"`
- 如果当前 clone 只服务一个 workspace：
  - 删除 `mode = "multi-workspace"`
  - 删除 `base_dir`

可以直接这样做一轮自检：

```bash
CURRENT_WORKSPACE="$(git rev-parse --show-toplevel)"
WORKSPACE_NAME="$(basename "$CURRENT_WORKSPACE")"

rg -n 'data_dir = |name = |mode = |base_dir = |work_dir = ' \
  tooling/remote_control/config/cc_connect.local.toml
```

至少需要填这些字段：

- `data_dir = "<workspace-root>/.cc-connect"`
- `projects.name = "<workspace-name>"`
- `admin_from`
- `allow_from`
- `app_id`
- `app_secret`
- 每个 provider 的 `CODEX_HOME`
- `projects.agent.options.work_dir = "<workspace-root>"`
- `[[commands]].work_dir = "<workspace-root>"`

如果你是“每个 git clone 都单独初始化”的使用方式：

- 不要保留模板里的 `mode = "multi-workspace"`
- 不要保留模板里的 `base_dir`
- 一个 clone 对应一个 `projects.name`
- `work_dir` 和 `data_dir` 都应指向当前 workspace

改完已有 `cc_connect.local.toml` 后，后续步骤不变：

1. `tooling/remote_control/scripts/build_patched_cc_connect.sh`
2. `tooling/remote_control/scripts/install_user_commands.sh --shell-init`
3. 重启 `tooling/remote_control/bin/cc-connect -config tooling/remote_control/config/cc_connect.local.toml`

### 1.5 本地构建 patched cc-connect

```bash
cd "$(git rev-parse --show-toplevel)"
tooling/remote_control/scripts/build_patched_cc_connect.sh
```

脚本行为：

- 优先使用 `tooling/remote_control/vendor/go/bin/go`
- 否则回退到系统 `go`
- 从 `cc_connect_src/` 构建 patched binary
- 输出到 `tooling/remote_control/vendor/bin/cc-connect-harness-patched-linux-amd64`

### 1.6 启动

```bash
cd "$(git rev-parse --show-toplevel)"
tooling/remote_control/bin/cc-connect -config tooling/remote_control/config/cc_connect.local.toml
```

`tooling/remote_control/bin/cc-connect` 是 wrapper：

- 优先执行本地 patched binary
- 如果没有 patched binary，再回退到官方预编译 binary

### 1.7 安装本地命令到 PATH

如果你希望在任意新开的终端里直接使用：

- `codex_all`
- `cw`

不要依赖手工把 shell function 写进 `~/.bashrc`。  
更稳的方式是执行仓库内安装脚本：

```bash
cd "$(git rev-parse --show-toplevel)"
tooling/remote_control/scripts/install_user_commands.sh --shell-init
```

这个脚本会把以下命令安装到 `~/.local/bin/`：

- `codex_all`
- `cw`

这个命令还会：

- 把 `codex_all` 和 `cw` 链接到 `~/.local/bin/`
- 在 `~/.profile` 和 `~/.bashrc` 中补一段最小 PATH 配置（如果原来没有）

如果当前 shell 还找不到命令，先执行：

```bash
export PATH="$HOME/.local/bin:$PATH"
```

之后重新开一个 shell 即可。

如果你想换安装目录，也可以临时覆盖：

```bash
BIN_DIR="$HOME/bin" tooling/remote_control/scripts/install_user_commands.sh
```

如果你只想安装命令链接，不想自动补 shell 初始化，也可以不带 `--shell-init`：

```bash
tooling/remote_control/scripts/install_user_commands.sh
```

这一步补上之后，别人拉取仓库时就不需要复制你的私有 `~/.bashrc` 配置了。

## 2. 飞书 MVP 接入

### 2.1 推荐接法

推荐结构是：

- `cc-connect` 负责飞书接入、workspace、session、provider 管理
- `harness_remote.sh` / `harness_remote.py` 负责 `/home` 与 `/ai`

关键脚本：

- [harness_remote.sh](./scripts/harness_remote.sh)
- [harness_remote.py](./scripts/harness_remote.py)

### 2.2 当前推荐命令映射

- `/home`
  - `cc-connect` 内建工作台卡片，内部调用 `summary --json`
- `/ai ...`
  - 走 `harness_remote.sh ai {{args}}`

### 2.3 MVP 目标

当前飞书 MVP 目标是先跑通：

- 飞书聊天入口
- workspace 绑定
- `/home` 工作台卡片
- `/help auto`
- `/ai status / pause / resume / stop`
- Codex provider 切换

### 2.4 菜单建议

建议菜单项：

- `工作台` -> `/home`
- `Workspace` -> `/workspace`
- `会话` -> `/help session`
- `自动迭代` -> `/help auto`
- `帮助` -> `/help`

### 2.5 飞书接入顺序

1. 本地确认 `tooling/remote_control/scripts/harness_remote.sh summary` 能跑
2. 本地确认 `cc-connect` 的 `/home` 能响应
3. 再验证 `/help auto`
4. 再验证 `/ai status`
5. 再去飞书开放平台配置菜单

## 3. 共享会话模型

### 3.1 当前目标

当前阶段解决的是：

- 同一 workspace 下，不同本地账号之间可以续同一批 Codex 会话
- 远程聊天和本地手动使用可以续同一条 Codex 会话
- `auto_iterate` 不参与这套共享会话

### 3.2 状态模型

当前共享模型是：

- `workspace -> slot -> session_id`

说明：

- 不再强制有一个“主会话”
- 每个共享会话有自己的 `slot`
- `slot` 记录最新 `session_id`、provider、`CODEX_HOME`

核心实现：

- [shared_slots.go](./cc_connect_src/core/shared_slots.go)
- [engine_shared.go](./cc_connect_src/core/engine_shared.go)

### 3.3 远程默认共享

远程聊天现在默认走共享会话：

- 普通消息会自动确保当前 chat 已绑定 slot
- `/new` 会创建一个新的共享 slot
- `/shared list|new|use|status|release|detach` 可显式管理 slot

### 3.4 本地默认共享

本地手动应该走：

- `codex_all`
- `cw`

要直接在任意终端输入这两个命令，先完成“1.7 安装本地命令到 PATH”。

当前行为：

- `codex_all`
  - 优先续当前 workspace 的本地绑定 slot
  - 没有绑定时创建新 slot
- `codex_all s003`
  - 续指定 slot
- `codex_all "train debug"`
  - 新建一个带标题的 slot
- `codex_all next`
  - 自动切到另一个账号，并续同一个本地 slot

本地入口实现：

- [share.go](./cc_connect_src/cmd/cc-connect/share.go)
- [cw](./bin/cw)
- [codex_all](./bin/codex_all)

### 3.5 跨账号 transcript 可见性

进入交互式 Codex 之前，系统会：

- 扫描所有已配置 provider 的 `CODEX_HOME`
- 找到当前 workspace 下的会话 transcript
- 把 transcript 镜像到当前激活账号的 `CODEX_HOME`

效果：

- 切账号后仍能续同一条会话
- 进入原生 Codex 终端后，`/resume` 也能看到这些会话

对应实现：

- [codex.go](./cc_connect_src/agent/codex/codex.go)

### 3.6 本地切号

`codex_all next` 的当前逻辑是：

- 读取当前 workspace 的本地 slot 绑定
- 将当前 provider 记入 cooldown
- 根据 priority 和 cooldown 选择另一个 provider
- 在新 provider 上续同一个 slot

边界：

- 这不是 quota 预测
- 不能保证下一个账号一定没有 limit
- 它是一个实用的自动轮换器

### 3.7 lease 语义

当前 lease 规则：

- 一个 `workspace + slot` 同时只允许一个活跃持有者
- 默认 lease TTL 是 1 小时
- `release` 表示显式让出

因此：

- 本地和远程可以接力共享
- 但不应同时驱动同一个 slot

额外保护：

- 已死亡的本地 PID lease 会自动清理

### 3.8 当前限制

- `auto_iterate` 不会加入共享会话体系
- 本地 `next` 是启发式 failover，不是真实 quota 探测
- shared slot 不适合本地和远程同时写
- 本地从另一个进程 `release` 某个 slot，通常需要 `--force`

## 4. 当前推荐日常用法

本地：

- 进入当前共享会话：`codex_all`
- 切到别的账号：`codex_all next`
- 指定共享会话：`codex_all s003`

远程：

- 直接正常发消息
- 开新线：`/new`
- 看当前 slot：`/shared status`
- 看整个 workspace 的 slot：`/shared list`

自动流程：

- 继续单独使用 `auto_iterate`
- 不要把 `auto_iterate` 和 shared slot 混用

## 5. 代码与测试定位

关键代码：

- slot / lease / local binding：
  - [shared_slots.go](./cc_connect_src/core/shared_slots.go)
- 远程默认共享：
  - [engine_shared.go](./cc_connect_src/core/engine_shared.go)
- 本地共享 CLI：
  - [share.go](./cc_connect_src/cmd/cc-connect/share.go)
- 交互式 catalog 同步：
  - [codex.go](./cc_connect_src/agent/codex/codex.go)

关键测试：

- [shared_slots_test.go](./cc_connect_src/core/shared_slots_test.go)
- [share_test.go](./cc_connect_src/cmd/cc-connect/share_test.go)
- [session_home_test.go](./cc_connect_src/agent/codex/session_home_test.go)
