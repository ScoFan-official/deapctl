# scaffold 引用不存在的 ops 函数名，整条命令不可跑

Status: promoted → .trellis/tasks/10-03-scaffold-ops-call-fix
Category: bug

## 现象

`python -m deapctl scaffold --name X` 必崩，两处缺陷：

1. `ag.list_agents(sess)` 返回 envelope dict（`ok({"agents": [...]})`），
   scaffold.py 直接 `[a["name"] for a in ag.list_agents(sess)]` 迭代 dict
   拿到的是字符串键 → `TypeError`，在 create 查重步骤就崩。
2. `ag.set_persona` / `ag.save` 在 `ops/agent.py` 中不存在（真实函数名
   `persona_set` / `save_agent`）→ `AttributeError` → INTERNAL envelope。

## 复现

- 静态：`hasattr(ag,'set_persona') == False`、`hasattr(ag,'save') == False`
  （已验证 2026-10-03）。
- 动态：任意 `scaffold` 调用，第一步 list 查重即 TypeError。

## 修复方向（spec 已写明）

对齐 `.trellis/spec/shell/index.md`「已知悬空实现」与
`.trellis/spec/recipes/index.md`「已知缺陷」：取 `["data"]["agents"]` 查重、
`persona_set`（可直接传 `file=`）、`save_agent`；顺带核对
`knowledge.attach` / `mcps.attach` 形参顺序（均为 `(sess, name, x_name)`，已对得上）。
