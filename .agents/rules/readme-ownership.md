---
trigger: glob
description: "README.md 的维护规范：Antigravity 负责 README，改动必须与代码、spec 和 coverage 同步"
globs: "README.md, README*"
---

# README.md 维护规范（Antigravity 负责）

本仓库 README 由 Antigravity 维护。修改时遵守：

## 结构与语言

- 全文中文叙述 + 英文标识符/命令，与 `coverage.md`、docstring 风格一致。
- 现有章节：用法（按命令域分组的 bash 块）→ 设计要点 → 错误码 → 已知边界。新内容归入对应章节，不新增同级章节除非是新能力面。

## 同步义务（改 README 前必查）

- 命令面必须与 `deapctl/cli.py` 的 parser 一致：子命令名、位置参数、`--flag` 拼写逐字核对。
- 错误码一节以 `.trellis/spec/runtime/envelope.md` 的 code 表为准（README 当前列的
  `LOGIN_REQUIRED`/`CONFIRM_REQUIRED` 与代码实际的 `NOT_LOGGED_IN`/`USAGE` 不一致，
  修订时对齐到代码真实值）。
- 能力状态描述与 `coverage.md` 的 ✅/🟡/⚪ 标记一致；README 不承诺 🟡/⚪ 能力已稳定。
- 「已知边界」中的刻意限制（无发布能力、草稿域限定）**不可删除或弱化**——这是设计决策。

## 不写进 README 的东西

- Trellis/工作流/agent 协作细节（属 `AGENTS.md` 和 `.trellis/spec/`）。
- 未实现的路线图功能；已知缺陷写「已知边界」而非正文流程。
