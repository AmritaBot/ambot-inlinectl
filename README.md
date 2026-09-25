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

列出当前所有可用子命令及其来源：

```shell
ambot cmds
```

## 命令

### `ambot run`

启动 bot。

```shell
ambot run
```

### `ambot run_in_sub`

在子进程中启动 bot（等效于 `ambot run`，但通过新进程运行）。

```shell
ambot run_in_sub
ambot run-in-sub   # 下划线与连字符可互换
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

## 注册子命令

`ambot` 的根命令是惰性解析的，第三方包可以往里挂自己的子命令，挂上之后直接
`ambot <你的命令>` 即可，无需修改本仓库。

### 方式一：entry point（推荐，跨包）

在插件包的 `pyproject.toml` 里声明：

```toml
[project.entry-points."ambot.commands"]
doctor = "my_pkg.cli:doctor"
```

`doctor` 即命令名。指向的对象可以是：

- 一个 `click.Command`（`click.Group` 亦可）
- 一个零参可调用对象，返回 `click.Command`、命令序列，或 `None`
  （返回 `None` 表示它已自行调用 `register_command()`）

单个 entry point 对应单个命令时，命令名以 entry point 名为准；返回多个命令时，
各自使用命令自身的名称。

#### 声明 `full_load`：目标需要完整插件环境

entry point 的值支持标准 extras 语法。声明 `full_load` 后，该命令在
`ambot --help` / `ambot cmds` 里**只出现名称、不触发加载**；真正被调用时才会：

1. 写入 `AMBOT_COMMAND_CONTEXT=1` 环境变量
2. 执行 `amrita.init()` + `amrita.load_plugins()`
3. 再 `ep.load()` 目标

适用于目标模块位于插件包内、且该包 import 期依赖插件加载器上下文
（例如 `nonebot.require(...)`）的场景 —— 这类模块在 `ambot` 解析参数阶段
直接加载必然失败。`full_load` 的 entry point 以 entry point 名作为命令名
（约定单个命令）。

```toml
[project.entry-points."ambot.commands"]
memory = "my_pkg.cli:memory [full_load]"
```

插件可以读取 `AMBOT_COMMAND_CONTEXT` 判断自己是被 `ambot <cmd>` 拉起来的、
而非在跑 bot，从而跳过启动期的交互式检查（否则维护命令会被自己的启动检查
挡在门外）。

### 方式二：进程内注册

```python
import click
from ambot_inlinectl import command, register_command


@command("doctor")
def doctor():
    """Check project health."""
    click.echo("ok")


# 等价写法
register_command(click.Command("doctor", callback=doctor))
```

要覆盖 ambot 自带命令（如 `run`）时需显式声明，否则自带命令优先命中：

```python
@command("run", replace=True)
def my_run(): ...
```

重复注册同名命令会抛 `ValueError`（显式传空名称同样报错）；加载失败的
entry point 只会告警并跳过，不影响其余命令。两个 entry point 声明了同一个
命令名时，按 `(名称, 目标)` 排序取先出现的一个并告警，结果不依赖安装顺序。

用 `unregister_command()` 注销后，被它覆盖的自带命令会恢复。

## pyproject.toml 配置

`ambot plugin add/remove` 会自动维护 `[tool.amrita.plugins]` 列表，供 `amrita.load_plugins()` 在启动时读取：

```toml
[tool.amrita]
plugins = [
]
```

## 许可证

MIT
