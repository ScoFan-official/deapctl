# Ops 层（`deapctl/ops/*`）

每个文件对应 DEAP 的一个功能域，对外只暴露 `route(sess, sub, args)`。
选择器/输入/弹层的底层规则在 `runtime/dom-toolkit.md`；DEAP 界面套路在 `ops/ui-patterns.md`。

## 模块解剖（所有 ops 文件同构）

```python
def _goto_xxx(sess, name):       # open_editor + 点页签 + b.wait(≈1800)
def do_something(sess, ...):     # 定位 → 动作 → wait → 回读校验 → ok() 或 OpError
def route(sess, sub, args):      # 子命令分发；未知子命令 OpError("USAGE", ...)
```

进智能体编辑器统一走 `ops/agent.py` 的 `open_editor(sess, name)`：
`name` 传名称或 uuid 均可（含 `-` 且长度 >30 按 uuid 处理），导航后等「人设/工作流」文本。
新功能域的入口照抄 `_goto_conv` / `_goto_knowledge` 的形状。

## 铁律

- **动作后必须回读**再报成功，不信 toast/弹窗文案：
  create 后重列（`agent.py` `create_agent`）、attach 后重读挂载（`mcps.py` `attach`）、
  delete 后查消失（`workflow.py` `delete`）。
- 定位失败 → `OpError("SELECTOR_MISS", "找不到「X」", hint)`，hint 指 `--debug-dom` 或核对命令。
- 幂等：先查重，命中 `ok` + `code:"ALREADY"`；破坏性操作 `--yes` 在最前拦截。
- 返回值 `data` 带调用方需要的后验状态（新列表、`saved` 标记、uuid）。

## 文件分工

| 文件 | 负责 |
|---|---|
| `agent.py` | 智能体列表/导航/新建/删除/persona/save；`open_editor` 供其他模块复用 |
| `conv.py` | 对话配置页：欢迎语/提示语/引导问题/快捷按钮 CRUD |
| `knowledge.py` | 知识集挂载（goto → 搜索弹层勾选 → 回读） |
| `mcps.py` | MCP 目录与挂载（与 knowledge 同构） |
| `workflow.py` | 工作流卡片级：list/create/meta/enable/copy/delete + `open_wf_editor` |
| `wfnode.py` | 编辑器画布：`WfEditor` 类——nodes/insert/delete/param/变量绑定/各节点类型配置 |
| `wfrun.py` | 编辑器运行面：save / check / debug / runs |

工作流编辑器分两个文件：**画布结构操作在 wfnode，运行/检查在 wfrun**，
新增编辑器能力按职责落位，不要塞错文件。

## Quality Check

- [ ] 重复 UI 模式先查 [ui-patterns.md](ui-patterns.md)，不新造轮子
- [ ] 每条写路径都有回读断言
- [ ] `route()` 末尾是 `OpError("USAGE", f"未知 xxx 子命令 {sub}")`
- [ ] 新增/变更能力同步 `verify_all.py` + `coverage.md`（verification/index.md）
