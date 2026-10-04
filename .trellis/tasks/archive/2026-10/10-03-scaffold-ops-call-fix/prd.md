# 修复 scaffold 的 ops 调用名与 envelope 解包

## Goal

`deapctl/recipes/scaffold.py` 引用了不存在的 ops 函数且未按 envelope 契约解包
`list_agents` 返回值，导致 `python -m deapctl scaffold` 整条命令必崩。
按 spec（`.trellis/spec/shell/index.md`「已知悬空实现」、
`.trellis/spec/recipes/index.md`「已知缺陷」）对齐调用。

## Requirements

- `ag.list_agents(sess)` 返回 envelope dict，查重需取 `["data"]["agents"]` 再按 `name` 匹配。
- `ag.set_persona` → `ag.persona_set`（签名 `persona_set(sess, name, text=None, file=None, append=False)`）。
- `ag.save` → `ag.save_agent(sess, name)`。
- 顺带核对 `knowledge.attach(sess, name, kn_name)` 与 `mcps.attach(sess, name, mcp_name)` 形参顺序（已确认一致，仅核对）。
- stdout 契约是 envelope JSON：recipes 内不加 print，只返回 `ok({...,"steps":[...]})`。
- 只改 `deapctl/recipes/scaffold.py`；不新造 UI 逻辑、不改 ops 层。

## Acceptance Criteria

- [ ] `python -m deapctl scaffold --name X --desc x` 在 create 查重步骤不再 TypeError/AttributeError（无会话时止于 NOT_CONNECTED，属环境限制）。
- [ ] stub 驱动的 `scaffold.run` 全流程可跑通（create 幂等/persona/knowledge/mcp/save 五步留痕）。
- [ ] `coverage.md` 场景层补 scaffold 行并标注实测状态。
- [ ] 有已登录 session 时端到端跑通并清理；无 session 则在 coverage.md 注明未实测。

## Notes

- 复现证据：`.scratch/inbox/01-scaffold-ops-call-names.md`（已 promoted 到本任务）。
