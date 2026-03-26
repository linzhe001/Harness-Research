# Feishu MVP 接入说明

本文档说明如何用当前仓库里的 remote wrapper 快速接出一个可用的飞书 MVP。

目标是先跑通：

- 飞书聊天入口
- multi-workspace
- 内建 `/home` 工作台卡片
- `/ai status / tail / pause / resume / stop`
- Codex 账号切换

而不是一开始就重做一套新的聊天平台层。

## 1. 前提

你需要：

- 一个可运行的 `cc-connect` 实例
- 飞书应用凭证
- 当前仓库中的 `tooling/remote_control/`
- 当前仓库中的 `tooling/remote_control/cc_connect_src/`

关键原因：

- 自定义 exec command 在 `multi-workspace` 模式下，必须能落到当前绑定 workspace
- 这个能力依赖本次补的 workspace-aware custom command 路由 patch

当前 setup 只依赖本仓库内的内容。

## 2. 推荐接法

使用：

- `cc-connect` 负责飞书接入、workspace/session/provider 管理
- `tooling/remote_control/scripts/harness_remote.sh` 负责 `/home` 的数据源和 `/ai`

命令映射：

- `/home` -> `cc-connect` 内建工作台卡片，内部调用 `harness_remote.sh summary --json`
- `/ai ...` -> `harness_remote.sh ai {{args}}`

## 3. 配置样板

参考：

- [config/cc_connect.local.toml](./config/cc_connect.local.toml)
- [config/templates/cc_connect_feishu_codex.example.toml](./config/templates/cc_connect_feishu_codex.example.toml)

重点配置项：

- `mode = "multi-workspace"`
- `base_dir = "/path/to/workspaces"`
- `[[commands]] name = "ai"`
- 飞书平台配置
- Codex providers / `CODEX_HOME`

## 4. 菜单建议

飞书固定菜单建议配置为：

- `工作台` -> `/home`
- `Workspace` -> `/workspace`
- `会话` -> `/help session`
- `自动迭代` -> `/help auto`
- `帮助` -> `/help`

## 5. 当前能力边界

这个 MVP 方案当前能解决：

- 每个飞书聊天入口绑定一个 workspace
- 在聊天里正常使用 Codex
- 在聊天里调用真正的 `/home` 工作台卡片
- 在聊天里通过 `/help workspace` / `/help auto` 查看分组命令卡片
- 在聊天里通过 `/ai` 控制 auto-iterate

这个 MVP 方案当前还没解决：

- 上下文短提示卡
- 单聊天无缝切 Claude / Codex agent

这些属于后续阶段。

## 6. 推荐上线顺序

1. 先在单个测试 workspace 上跑通 `/home`
2. 再验证 `/help auto`
3. 再验证 `/ai status`
4. 再验证 `/ai pause / resume / stop`
5. 再验证 workspace bind / switch
6. 最后再配置飞书菜单

## 7. 飞书应该如何连接

推荐先走 `cc-connect` 自带的飞书接入流程，再把菜单绑到 `/home` 和 `/help auto`。

### 7.1 最快路径

如果你已经有 `cc-connect` 可执行文件，优先用：

```bash
cc-connect feishu setup --project harness-research
```

如果你已经有现成的 `app_id` / `app_secret`，也可以用：

```bash
cc-connect feishu setup --project harness-research --app cli_xxx:sec_xxx
```

这条路径的好处是：

- 自动把飞书平台配置写回 `config.toml`
- 默认按长连接模式接入
- 不需要公网 IP

### 7.2 手动连接步骤

如果你想手动配置，按下面做：

1. 在飞书开放平台创建企业自建应用  
   官方文档入口：<https://open.feishu.cn/document/>

2. 在应用里启用机器人能力

3. 申请并确认最少权限：
   - 接收单聊消息
   - 接收群聊消息
   - 读取消息内容
   - 以应用身份发消息

4. 在事件订阅中启用长连接模式  
   这是 V1 推荐方式，因为：
   - 不需要公网 IP
   - 不需要 HTTPS 回调
   - 本地开发最省事

5. 在 `cc-connect` 配置中填入：
   - `app_id`
   - `app_secret`
   - `allow_from`
   - `enable_feishu_card = true`

6. 启动 `cc-connect`

如果你的配置文件就在当前目录：

   ```bash
   tooling/remote_control/bin/cc-connect
   ```

   如果你放在其他位置：

   ```bash
   tooling/remote_control/bin/cc-connect -config /path/to/config.toml
   ```

7. 在飞书里搜索 bot 或把 bot 拉进群聊

### 7.3 菜单怎么绑

飞书 bot 菜单不是代码里自动创建的，通常需要在飞书开放平台后台配置。

建议配置 5 个菜单项，并把 `event_key` 直接写成命令：

- `工作台` -> `/home`
- `Workspace` -> `/workspace`
- `会话` -> `/help session`
- `自动迭代` -> `/help auto`
- `帮助` -> `/help`

原因：

- `cc-connect` 已支持把飞书菜单点击事件当作 slash command 分发
- 你这次加的 `/home` 和 `/ai` 正好可以直接承接这些入口

### 7.4 菜单和卡片按钮各自负责什么

- 飞书菜单：负责高频入口
- `/home` 卡片：负责当前 workspace 概览和推荐下一步
- `/help`：负责完整命令分组
- `/help auto`：负责 auto-iterate 控制分组
- `/ai ...`：负责真正的 auto-iterate 控制

### 7.5 推荐你实际操作的顺序

1. 先确认 `tooling/remote_control/scripts/harness_remote.sh summary` 本地能跑
2. 再确认 `cc-connect` 里的 `/home` 能响应
3. 再确认 `/help auto` 能响应
4. 再确认 `/ai status` 能响应
5. 再去飞书后台配菜单
6. 最后再开始做更复杂的卡片和提示自动发送
