# Remote Control 构建与本地配置

这份说明解决 3 件事：

1. 哪些文件应该提交到 GitHub
2. 哪些文件只应该保留在本机
3. 怎样在本地构建 patched `cc-connect` 并生成可用配置

## 提交策略

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

## 推荐目录约定

- 内置 `cc-connect` 源码：`tooling/remote_control/cc_connect_src/`
- 模板：`tooling/remote_control/config/templates/`
- 本地生效配置：`tooling/remote_control/config/*.local.*`
- 本地 Go 工具链：`tooling/remote_control/vendor/go/`
- 本地 patched 二进制：`tooling/remote_control/vendor/bin/`

当前 setup 只依赖本仓库内的内容。

## 1. 生成本地配置

从模板开始：

```bash
cp tooling/remote_control/config/templates/cc_connect.local.example.toml \
  tooling/remote_control/config/cc_connect.local.toml
```

然后至少替换这些字段：

- `base_dir`
- `admin_from`
- `allow_from`
- `app_id`
- `app_secret`
- 每个 `CODEX_HOME`
- 两个 `work_dir`

当前推荐默认值已经写在模板里：

- `model = "gpt-5.4"`
- `reasoning_effort = "xhigh"`
- `preferred_models = ["gpt-5.4", "gpt-5.4-codex", "gpt-5.3-codex", "o3"]`
- `show_copyable_commands = false`

## 2. 本地构建 patched cc-connect

如果你的系统已经有 Go 1.25，可以直接用系统 Go。  
如果不想装全局 Go，可以把本地 Go 放到：

```text
tooling/remote_control/vendor/go/
```

然后运行：

```bash
tooling/remote_control/scripts/build_patched_cc_connect.sh
```

这个脚本会：

- 优先使用 `tooling/remote_control/vendor/go/bin/go`
- 否则回退到系统 `go`
- 在 `tooling/remote_control/cc_connect_src/` 中编译 patched binary
- 安装到 `tooling/remote_control/vendor/bin/cc-connect-harness-patched-linux-amd64`

## 3. 启动

```bash
tooling/remote_control/bin/cc-connect \
  -config tooling/remote_control/config/cc_connect.local.toml
```

`tooling/remote_control/bin/cc-connect` 是一个 wrapper：

- 优先使用 patched binary
- 如果本地没有 patched binary，再回退到官方预编译 binary

## 4. 给 AI 的配置任务模板

如果你想让 Codex / Claude / ChatGPT 帮你填本地配置，直接把下面这段贴给它：

```text
请基于 tooling/remote_control/config/templates/cc_connect.local.example.toml
生成 tooling/remote_control/config/cc_connect.local.toml。

要求：
1. 不要改模板文件，只生成 .local.toml
2. model 固定为 gpt-5.4
3. reasoning_effort 固定为 xhigh
4. preferred_models 保持 ["gpt-5.4","gpt-5.4-codex","gpt-5.3-codex","o3"]
5. 按 tooling/auto_iterate/config/accounts.local.yaml 填 CODEX_HOME
6. 飞书使用我的 app_id / app_secret / open_id
7. show_copyable_commands = false
8. 不要把任何 .local 文件加入 git
```

## 5. GitHub 发布建议

推荐做法：

- GitHub 仓库存源码、模板、文档
- GitHub Release 发编译好的二进制
- 用户本地只保留 `.local` 配置和工具链

不推荐做法：

- 把 `tooling/remote_control/vendor/go/` 整包提交
- 把本地编译好的 `cc-connect` 二进制直接提交到主分支
- 把含密钥的 `.local.toml` 提交到仓库
