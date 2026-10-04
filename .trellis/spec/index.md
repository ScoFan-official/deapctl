# deapctl Spec 索引

deapctl 是通过 Chrome CDP 驱动钉钉 DEAP 控制台（https://deap.dingtalk.com）的自动化 CLI。
所有操作停留在**草稿域**——不提供发布能力（刻意设计，见 README.md）。

源码是单 Python 包 `deapctl/`（无单元测试目录；验收走 `verify_all.py` 端到端矩阵）。
文档语言与代码注释一致：中文叙述 + 英文标识符。

## 按改动面选读

| 改动位置 | 必读 |
|---|---|
| `deapctl/envelope.py`、错误码、输出格式 | [runtime/envelope.md](runtime/envelope.md) |
| `deapctl/session.py`（CDP / 登录 / profile） | [runtime/session.md](runtime/session.md) |
| `deapctl/browser.py`、任何 `sess.b.*` 调用、选择器 | [runtime/dom-toolkit.md](runtime/dom-toolkit.md) |
| `deapctl/cli.py`、新增命令 | [shell/index.md](shell/index.md) |
| `deapctl/ops/` 任一操作模块 | [ops/index.md](ops/index.md) + [ops/ui-patterns.md](ops/ui-patterns.md) |
| `deapctl/recipes/`（scaffold、workflow apply） | [recipes/index.md](recipes/index.md) |
| `deapctl/mcp_server.py`、MCP 工具表 | [mcp-server/index.md](mcp-server/index.md) |
| 验收、coverage.md、--debug-dom、回归 | [verification/index.md](verification/index.md) |

各层 `index.md` 内含 **Pre-Development Checklist** 与 **Quality Check**。

## 工作流契约（agent 流程）

- `agents/` — mattpocock 技能接入 Trellis 的机器契约：先读 `agents/index.md`，其中 `issue-tracker.md` 是权威。
- `guides/` — 思考清单（code-reuse / cross-layer / mp-integration）。

## 全项目不变量（任何层都适用）

1. **stdout 只出 envelope JSON**。诊断/堆栈一律走 stderr 或异常（runtime/envelope.md）。
2. **草稿域限定**：不新增发布/上线类命令；草稿域不可用的能力返回明确错误而非半实现（coverage.md「实验面」）。
3. **破坏性操作必须 `--yes`**：函数体第一行 `OpError("USAGE", ...)` 拦截（ops/agent.py `delete_agent`）。
4. **幂等**：create/attach/enable 先查已存在，命中返回 `ok` + `code:"ALREADY"`（ops/mcps.py `attach`）。
5. **选择器语义优先**：文本/placeholder/label 结构 > `[class*=前缀]` > 坐标兜底（runtime/dom-toolkit.md）。
