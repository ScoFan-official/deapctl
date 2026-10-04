# Shell 层（`deapctl/cli.py` 命令面）

argparse 三级子命令（`cmd` → `sub` → `sub2`）→ `dispatch()` →
ops/recipes 模块的 `route(sess, sub, args)`。全部输出走 envelope（runtime/envelope.md）。

## 结构

- 全局参数：`--cdp-url`、`--format json|pretty`、`--debug-dom <file>`（OpError 时抓页面文本）。
- `login` / `status` 直连 `session.py` 函数，不进 `Session`。
- 其余命令统一：建 `Session` → `ensure_login()` → `route()` → `finally sess.close()`。
- dispatch 内 **lazy import** ops/recipes 模块——`--help` 和参数错误路径
  不付 playwright 启动成本，新命令照做（`deapctl/cli.py` `dispatch`）。
- `mcp-server` 也会先建 `Session` + `ensure_login`（登录门禁），之后 stdio 循环里
  每次工具调用另起 `python -m deapctl` subprocess、各自建 Session。

## 新增一条命令的步骤

1. `_parser()` 加 subparser，沿用现有命名分层：领域（`agent/conv/knowledge/mcp/workflow/node/scaffold`）→ 动作 → 子动作。
2. `dispatch()` 加分支：lazy import → `route(sess, sub, args)`。
3. 目标模块 `route()` 分发到具体函数；返回 `ok(...)`，失败 `OpError`。
4. 破坏性命令加 `--yes`，函数体第一行校验（`ops/agent.py` `delete_agent`）。
5. 用户可见的能力同步三处：`README.md` 用法、`verify_all.py` 矩阵、`coverage.md` 表。
6. 需要 MCP 暴露时：`mcp_server.py` 的 `TOOLS` + `_tool_to_argv` 两处同步（见 mcp-server/index.md）。

## 已接线历史（防止重复排查）

- `conv tips set` / `conv guides set` 已接上（ops 实现原本就完整，
  缺的只是 parser + route）。`--qs` 用 `|` 分隔，与 `--examples` 约定一致。
- `recipes/scaffold.py` 调用名已对齐（任务 10-03-scaffold-ops-call-fix）。

## Quality Check

- [ ] 未知子命令落 `OpError("USAGE", ...)`
- [ ] 可选参数用 `getattr(args, "x", None)` 兜底（dispatch/route 已有先例）
- [ ] 新命令的 help 文本写明参数语义（insert 的 `--after`、config 的 `--spec` 是范例）
