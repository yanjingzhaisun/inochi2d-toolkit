# inochi2d-toolkit

[English](README.md) (canonical) · **中文** · [日本語](README.ja.md)

> 英文 README 是标准入口，本文件跟随它。若两者出现偏差，以英文为准——请提 pull request，而不是让两份悄悄分叉。

读取、校验并（逐步）**生成 Inochi2D puppet**：对人类和脚本是 CLI，对 agent 是 MCP server。两个表面都是同一套 core 的薄壳，不会悄悄分叉。

Inochi2D 没有官方插件/IPC 接口，它的编辑器（Inochi Creator）是一个 GUI 程序。本工具走另一条路：**puppet 格式本身是开放的**——一个 `TRNSRTS` 容器，里面装一份 JSON payload 加纹理——因此绑骨可以在文件层生成与检查，编辑器只需要用来**看**结果。

## 状态

诚实规矩（继承自我们的 pipeline lab）：每项能力都标注**已实现 / 计划中**。未实现的会直接报错退出，不假装能用。

| 能力 | 状态 | 做什么 |
| --- | --- | --- |
| `new` | 已实现 | 写一个最小且结构合法的 0.8 puppet |
| `inspect` | 已实现 | 读 puppet 并打印结构（节点、参数、纹理），支持 `--json`/`--tree` |
| `verify` | 已实现 | 读 → 写 → 读 的 round-trip，**外加**结构校验 |
| `textures` | 已实现 | 导出内嵌纹理 |
| `from-layers` | 计划中 | 分层图 → 已绑骨的 puppet（生成网格 + 参数绑定） |
| `render` | 计划中 | 无头渲染存 PNG（经 Creator bridge） |
| `bridge` | 计划中 | 在工作站上安装/刷新 Creator 控制桥 |

`inochi2d status` 从代码里打印同一张表。

## 范围（本仓假设什么、不假设什么）

- **目标：Inochi2D 的 v0_8 payload。** 不是 Live2D 管线。早前 2D 傀儡工作的指导意见可复用，那条管线不复用。
- **不依赖任何既有资产。** 本仓不依赖任何已存在的模型、绑骨、图层组或 3D 资产。写下本仓的那台工作站上
  没有可复用的东西，而我们手上那个 3D 资产只是中间产物，**明确不作参照**。
- **上游素材是开放依赖。** 立绘仍在制作中，其拆层尚未达标；因此 `from-layers` 会校验拿到的东西，而不是相信它。
- **人只做视觉审核。** 直到渲染出 PNG 为止的一切都应无人值守地跑完；审核者看图，不看文件。

## 安装

```bash
pip install .            # core：只用标准库
pip install '.[mcp]'     # + MCP server
pip install '.[rig]'     # + numpy/Pillow，供绑骨相关（计划中的）功能使用
```

## CLI

```bash
inochi2d new out.inx --name "Test Puppet"     # 最小 puppet
inochi2d inspect out.inx --tree               # 结构
inochi2d verify out.inx --warnings            # round-trip + 校验，出错退出码 1
inochi2d textures out.inx --out ./textures    # 导出纹理
inochi2d status                               # 能力表
```

回归语料（官方样例，下载而来、不提交进仓）：

```bash
python tools/fetch_examples.py    # examples/empty08.inx (702 B), examples/ada-static.inx (7.1 MB)
pytest -q
```

## MCP

```bash
python -m inochi2d_toolkit.mcp_server          # stdio
```

工具：`inochi_status`、`inochi_inspect`、`inochi_verify`、`inochi_extract_textures`、`inochi_new_minimal`。

注册到 MCP 客户端（以 Hermes 为例）：

```yaml
mcp_servers:
  inochi2d:
    command: /path/to/venv/bin/python
    args: [/path/to/inochi2d-toolkit/src/inochi2d_toolkit/mcp_server.py]
    enabled: true
```

## 设计

- **CLI 为主。** 能力只在 `src/inochi2d_toolkit/` 实现一次，暴露两次（`cli.py`、`mcp_server.py`）。MCP 层不含逻辑。
- **core 零依赖。** `inp.py` / `puppet.py` / `build.py` 只用标准库，所以同一份代码能跑在容器里、Windows 工作站上，
  或 MCP server 内部。
- **格式即接口。** 版本对齐很重要：本工具以 **v0_8** payload 为目标（`meta.version` = `v0.8.6`），对齐
  Inochi Creator 0.8.6。0.9 线重构了变形绑定并换了新容器（`INP2`）——见 `docs/architecture.md`。
- **先校验再相信。** 每条写路径都应紧跟一次 `verify`：纹比对到字节级、JSON 做 payload 深等，外加结构检查
  （uuid 唯一、mesh/uv 成对、索引与纹理 id 范围、绑定目标）。
- **接口一律英文。** 调用方能看见的东西全用英文——CLI 输出、`--help` 文本、MCP 工具描述、异常信息、日志——
  commit message 与 `docs/` 也是。只有 README 有译本，且以英文版为准；由 `tests/test_interface_language.py` 守住。

## 本工具依赖的格式事实

由逐字节读取两份官方样例得出（测试将其钉住）：

```
magic        8 bytes   "TRNSRTS\0"        （没错，就是这样）
json length  uint32    大端
json         N bytes   UTF-8，puppet payload
"TEX_SECT"   8 bytes   必需
tex count    uint32
texture*     每条：uint32 长度、uint8 编码（0=PNG, 1=TGA, 2=BC7）、payload
"EXT_SECT"   8 bytes   可选，厂商段
```

- 重新序列化官方那份 702 字节样例，能逐字节重现其内容（`tests/test_inp.py`）。
- `Part.textures` 是**固定长度的 3 槽数组**；未使用的槽填 `4294967295`（uint32 −1），与 `meta.thumbnailId`
  用的是同一个"此处为空"哨兵。不要把它当纹理索引读。
- `Part` 携带 `mesh`（`verts`/`uvs` 平铺成对、`indices`、`origin`）、`blend_mode`、`tint`、`screenTint`、
  `emissionStrength`、`mask_threshold`、`opacity`。
- 官方带纹理样例用的是 **TGA** 纹理——实际上 PNG 不是唯一编码。
- 官方导出器自己的输出校验为零问题；把它报成错的校验器就是错的（这条是测试）。

## 致谢 / 许可

MIT（见 `LICENSE`）——选它是因为识别度高，不是因为权限差异：MIT 与 BSD-2-Clause 授予的权利相同
（使用、修改、再分发、再许可、出售、闭源），两者都不是 copyleft，所以本仓的许可不受上游项目约束。

本工具独立开发，与 Inochi2D Project 无隶属关系。仓内**不含上游代码**：读写实现是依据格式自身行为写出的，
并用官方样例验证。Inochi2D、Inochi Creator、Inochi Session 是 Inochi2D Project 的 BSD-2-Clause 项目；
官方样例由 `tools/fetch_examples.py` 下载，**不随本仓分发**，因此仍归其原有许可。
