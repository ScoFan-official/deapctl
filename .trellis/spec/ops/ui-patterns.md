# DEAP UI 模式速查（实测沉淀）

ops 层反复出现的界面套路。新功能先在这里找现成写法；踩出新坑把结论补进
`coverage.md`「硬知识」，并把可复用写法加回本文件。

## 悬停显形（hover-reveal）

行内操作按钮先 `dispatchEvent(new MouseEvent('mouseover',{bubbles:true}))` 再查控件：

- 智能体行内「删除」：`ops/agent.py` `delete_agent`
- 快捷按钮编辑/删除图标（按 className 含 `blue`/`red` 区分）：`ops/conv.py`
- 工作流卡片图标按钮 `_card_btn(sess, wf, idx)`：0=编辑 1=复制 2=删除（`ops/workflow.py`）

## 确认弹窗兜底

**一律走 `sess.b.confirm_modal(labels=None)`**（`browser.py`）——别在 ops 里手写弹窗点击。
它内置 DEAP 肯定按钮文案全集（含复合文案如 `确定删除`），倒序扫 `layers()` 取最顶层
（同文档多次确认会堆叠同名 modal 实例），返回被点按钮文本或 `None`。

调用约定分两种，按操作后果选：
- **确认必须发生**（删除类）：检查返回值，`None` → `SELECTOR_MISS`（`agent.delete_agent`）。
- **弹窗可有可无**（可能的确认）：忽略返回值，靠后续回读验证（`conv.qbtn_delete`）。

血泪 2026-10：删除智能体的确认按钮文案是 `确定删除`，旧 allowlist
`['确定','删除','是']` 全 miss 且返回值未检查——请求提交了但 modal 没关，
行删不掉还返回 `ok:true`（`deleted:false`）。**确认点击的返回值不可静默吞掉**。

## 弹层 / 抽屉作用域

| 层 | 取法 |
|---|---|
| 表单弹窗 | `[...document.querySelectorAll('.dtd-modal')].filter(vis).pop()` |
| 节点配置抽屉 | `[class*=drawer-panel-body-v2]` 最后可见者（`wfnode.DRAWER`） |
| 变量面板 | `[class*=picker-pane_]` 最后可见者 |
| AI 表格文档选择 | **可能在 iframe**：遍历 `page.frames` 逐个 evaluate（`wfnode._pick_base`），非 iframe 兜底回主文档 |

层内「label → 控件」定位：从 label 文本节点向上爬 ≤8 层找兄弟 input/textarea/switch/
`[class*=addIcon]`。`WfEditor._drawer_fields()` 是通用盘点器——**新节点类型接入前
先调它打印抽屉布局**，再写专用配置函数。

## 控件类型对照

| 控件 | 正确写法 |
|---|---|
| 单选/选项卡 | 点 label 或包裹元素，不点 input 本身（`conv._fill_modal` 的 FillInput 分支） |
| `dtd-select` 下拉 | 点搜索输入框开层 → 全局按文本选 option（`wfnode.select_option`） |
| `.dtd-switch` 开关 | 先判 `aria-checked`/class checked 再决定点不点（`workflow.enable`） |
| Slate `[contenteditable]` | `click_xy` 聚焦 → `b.type`（`conv._fill_modal`、`wfnode.fill_slate`） |
| 变量绑定 | `pick_var(label, 叶子名)`：聚焦 → ⊕ → `picker-pane_` → **优先 `input.dtd-search-bar-input` 搜索直达**（搜索是权威过滤；搜后仍无 = 变量缺失/类型不匹配，勿再 expand/scroll——虚拟化树渲染时序不稳曾致间歇漏选，见 .scratch/inbox/02）；无搜索框才回退展开/滚动 → dispatch 叶；picked 后清空搜索框 |
| 枚举/固定值字段 | 不能绑变量——`fixed` 写字面值；select 型先点开再选文本（`wfnode._set_record_field_literal`） |

## 画布操作（`wfnode.py`）

- 节点 = `[class*=node-wrap-box]`，innerText 以「序号./标题」开头；
  插入点 = `[class*=add-node-btn]`（连线中点 "+"，坐标点击）。
- 节点点击用 `click_xy`；抽屉未开时按坐标找元素 dispatch 重试一次（`open_drawer` 已封装）。
- **循环体插入总落顶部**——多子节点必须倒序写入（`insert_into_loop` docstring 即契约）。
- 新插入节点定位：`wf_apply._find_new_node` 按 label 文本取最后匹配。
- 「保存」是拆分按钮：点完检查「仅保存」子项兜底（`WfEditor.save` / `wfrun.save`）。
- **序号选择器不稳定**：画布上存在无编号前缀的包装节点（如起始区的「就执行/指定操作」占位框占 2 号位但 innerText 无 "2."），插入后序号还会漂移——自动化一律用标题匹配（`find_node` 支持 `s in n["text"]`），脚本勿硬编码 "2." 这类序号。

## 已实测结论（改版后再调参考）

1. 循环内容必须绑「对象数组」类型变量 → 上游 LLM 节点需开 JSON 模式产出真数组。
2. 变量面板按类型过滤；绑定失败报 `VAR_TYPE_MISMATCH`。
3. 主动触发只收已发布技能 → 草稿域 `UNSUPPORTED_IN_DRAFT`；不提供发布命令（刻意）。
4. 调试预览里钉钉待办/通讯录 MCP 不可直调——平台限制，不是本工具 bug（README「已知边界」）。
