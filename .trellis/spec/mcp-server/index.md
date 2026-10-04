# MCP Server 层（`deapctl/mcp_server.py`）

stdio JSON-RPC 桥，给不能直接跑 CLI 的 Agent 用。**工具即 CLI 子命令的薄封装**，
不在 server 层做业务逻辑、重试或输出改写。

## 结构

- `TOOLS` 静态表：`deap_*` 名 + description + inputSchema。
- `_tool_to_argv(name, args)` → CLI argv；`_cli()` 以
  `python -m deapctl --cdp-url <cdp> ...` subprocess 执行，`timeout=600`。
- `run_stdio` 最小 MCP 循环：`initialize` / `tools/list` / `tools/call` /
  `notifications/initialized` / `ping`；未知 method → `-32601`；无 `id`（notification）不回复。
- 工具输出 = CLI stdout **原文**（envelope JSON 塞进 `content[].text`），不加封装。

## 规则

- 新增 CLI 命令时决定是否暴露 MCP：需要则 `TOOLS` 和 `_tool_to_argv` **两处同步**；
  inputSchema 的 `required` 与 CLI 位置参数一一对应，可选参数给默认值映射。
- 破坏性工具（delete 类）按 CLI 语义要求布尔参数 → argv 拼 `--yes`。
- 长操作（`workflow apply` / `debug`）受 600s subprocess 超时限制；
  预计可能超时的工具在 description 里说明。
- server 自身退出返回 envelope dict（`ok_exit`），保持 stdout 契约一致。
