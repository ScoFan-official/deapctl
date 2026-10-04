# Recipes 层（`deapctl/recipes/*`）

声明式复合操作：把 ops 层原子命令编排成「一条命令」。recipes **只编排不新造 UI 逻辑**——
定位/输入/弹层细节仍归 ops。

- `scaffold.py` — 一条命令装配草稿智能体：create → persona → welcome/knowledge → mcp → save
- `wf_apply.py` — spec.json → 整条工作流：meta/params/nodes → insert+config → save + check

## 契约

- 输入 = 文件/参数，输出 = 单条 envelope：`ok({..., "steps"|"applied": [...]})`，每步留痕。
- **幂等可重跑**：已存在则跳过（scaffold）或要求 `--force` 删除重建（apply → `EXISTS`）。
- 失败让 `OpError` 冒泡，不承诺半成品状态；重跑靠幂等恢复。
- spec DSL 文档就维护在 `wf_apply.py` docstring；改 DSL 同步 docstring + `examples/*.json`。

## workflow apply 专属规则

- `spec.nodes` 按「视觉从上到下」书写；`type_map` 把
  `llm/loop/record/condition/end` 映射到节点面板中文名。
- `loop.children` 同样按视觉顺序写，执行器内部 `reversed()` 插入
  （编辑器落顶部约束，见 ops/ui-patterns.md）。
- `end` 节点不插入（画布自带），只 `config_end(pairs)` 绑输出变量。
- apply 末尾强制 `ed.save()` + `wfrun.check()`，结果写进 envelope 的 `data.check`——
  调用方据此判断是否配全。

## 已修复缺陷

`scaffold.py` 曾引用不存在的 `ag.set_persona` / `ag.save` 且未解包
`list_agents()` 的 envelope——2026-10 已对齐 `persona_set` / `save_agent` /
`["data"]["agents"]`（任务 10-03-scaffold-ops-call-fix）。提醒：ops 层函数
一律返回 envelope dict，recipes 调用后取 `["data"]` 才是业务数据。
