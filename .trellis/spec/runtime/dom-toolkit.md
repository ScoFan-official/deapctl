# DOM 工具层（`__deap` + `B`）

`deapctl/browser.py`。`install(page)` 向页面注入 `window.__deap` JS 工具集；
`B(page)` 是 Python 侧操作面。ops 层一律通过 `sess.b.*` 调用，
不要把长 JS 直接塞进 ops 的 `page.evaluate`——可复用的定位原语应该加到这里或 ops 的 ui-patterns。

## `__deap` 工具集（注入后页面内可用）

| 工具 | 用途 |
|---|---|
| `vis(e)` | 可见性判定（尺寸 ≥2px + visibility/display），所有查询后必过滤 |
| `deepAll / deepVisible(sel)` | 穿透 shadow DOM 的 querySelectorAll |
| `byText(txt, exact)` | 文本匹配并取**最深命中**（避免点到包文本的大容器） |
| `clickEl(e)` | dispatch 完整鼠标事件序列（合成点击） |
| `fillIn(e, val)` | React 受控输入：native setter + input/change + blur |
| `layers()` | 当前可见弹层（modal/drawer/dropdown/popover/tooltip），按 DOM 序 |
| `topText()` | `body.innerText` 前 4000 字（`b.text`/`has_text` 的数据源） |
| `chips(host)` | 容器内叶子文本提取（变量芯片/标签） |

`B` 侧方法：`ev(js)`、`click_xy(x,y)`（真实鼠标）、`click_text`、`click_el_js`、
`wait(ms)`、`wait_text(txt, timeout)`、`has_text`、`key`、`type(text)`、
`screenshot`、`scroll_el`。

## 选择器军规（优先级递减）

1. **语义优先**：innerText / placeholder / label 兄弟节点 / 结构位置（README「设计要点」同源）。
2. 类名只能用 `[class*=前缀]`——CSS-module 哈希后缀会变。已实测稳定前缀：
   `node-wrap-box`、`drawer-panel-body-v2`、`add-node-btn`、`picker-pane_`、
   `shortcut-item`、`inputVars`、`addIcon`；稳定全名 `.dtd-modal/.dtd-drawer/.dtd-switch`。
3. `click_xy` 坐标点击只做兜底——画布节点、⊕ 图标、Slate 聚焦这些
   dispatch 事件无效的场景才用。
4. 弹层内操作**先取层再局部查询**：`__deap.layers()` / `.dtd-modal` 取层 →
   `m.querySelectorAll(...)`。禁止全局搜，会被页面同名元素干扰
   （`ops/agent.py` `create_agent` 的 modal 作用域写法是范式）。

## 两种输入路径——选错即 bug

| 控件类型 | 正确路径 | 错误做法 |
|---|---|---|
| input / textarea（React 受控） | `__deap.fillIn(e, val)` | `b.type`（慢且可能触发校验异常） |
| Slate `[contenteditable]` | `click_xy` 真实聚焦 → `b.type(text)` | `fillIn`（Slate 不感知，README 已记） |

证据：`ops/conv.py` `_fill_modal`（预设输入是 Slate）、`ops/wfnode.py` `fill_slate`。

## 变量芯片 / picker 面板（踩过的坑，coverage.md「硬知识」同源）

- ⊕ 图标必须真实 `click_xy`，且**先点 Slate 编辑区聚焦再点 ⊕**，否则面板空渲染。
- 叶子在虚拟化树里：`switcher` 展开折叠组 + holder 滚动 + `clickEl` dispatch 选叶
  （真实点击被抽屉遮挡，`elementFromPoint` 命不中）。
- 面板按字段类型过滤（日期字段只列日期变量、人员字段只列人员对象）；
  找不到叶子 → `VAR_TYPE_MISMATCH`，不是 `SELECTOR_MISS`（`wfnode._bind_record_field`）。

## 等待节奏

动作后固定 `b.wait(ms)`：页签/弹层 1200–2000，表单提交 2500–3500，
`page.goto` 后 2000–3500。等异步内容出现用 `b.wait_text(txt, timeout)` 轮询，
不要裸 sleep 后直接断言。

## 失败协议

JS helper 返回短状态串（`'nf'` / `'no-modal'` / `'no-btn'` / `'no-row'`…），
ops 侧翻译成 `OpError("SELECTOR_MISS", "找不到「X」", hint)`，并把状态串带进 message。
不要静默 `return None` 让流程往下走。
