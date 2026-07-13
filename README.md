# ambot-inlinectl

AmritaBot 内联管理工具 — 在项目目录内通过 `ambot` 命令行管理 AmritaBot 的插件、数据库和运行。

## 安装

```shell
pip install ambot-inlinectl
```

## 使用

```shell
ambot <命令>
```

## 命令

### `ambot run`

启动 bot。

```shell
ambot run
```

### `ambot run-in-sub`

在子进程中启动 bot（等效于 `ambot run`，但通过新进程运行）。

```shell
ambot run-in-sub
```

### `ambot nb <参数...>`

透传调用 nb-cli。自动加载 Amrita 框架后再执行原生命令。

```shell
ambot nb --help
ambot nb plugin list
```

### `ambot orm <参数...>`

透传调用 nonebot-plugin-orm CLI。自动加载 Amrita 框架和 ORM 插件后执行。

```shell
ambot orm upgrade
ambot orm migrate
```


### `ambot plugin list`

嗅探环境中所有已安装的插件：

- `amrita_plugin_*` — pip 安装的 Amrita 插件
- `nonebot_plugin_*` — pip 安装的 NoneBot 插件
- `plugins/` 目录 — 本地 Amrita 插件
- `src/plugins/` 目录 — 本地 NoneBot 插件

```shell
ambot plugin list
```

### `ambot plugin add <包名>`

安装插件并注册到 `pyproject.toml` 的 `[tool.amrita.plugins]`：

- 调用 `uv add` 安装包
- 将包名追加到 `[tool.amrita.plugins]` 列表

```shell
ambot plugin add nonebot_plugin_orm
ambot plugin add amrita_plugin_example
```

### `ambot plugin remove <包名>`

卸载插件并从 `[tool.amrita.plugins]` 移除：

- 调用 `uv remove` 卸载包
- 将包名从 `[tool.amrita.plugins]` 列表中移除

```shell
ambot plugin remove nonebot_plugin_orm
```

## pyproject.toml 配置

`ambot plugin add/remove` 会自动维护 `[tool.amrita.plugins]` 列表，供 `amrita.load_plugins()` 在启动时读取：

```toml
[tool.amrita]
plugins = [
]
```

## 许可证

MIT
