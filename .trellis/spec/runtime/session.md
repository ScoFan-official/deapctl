# Session 与 CDP 连接

`deapctl/session.py`。每条命令一个独立 Session：
`dispatch()` 建 → `ensure_login()` → 分发给 ops/recipes → `finally: sess.close()`。
`close()` 只停 playwright 上下文，**不关闭浏览器**（登录态靠复用保住）。

## 连接模型

- 默认 `http://127.0.0.1:9222`（`DEFAULT_CDP`，`--cdp-url` 可覆盖）。
  **必须用 IPv4 字面量**：`localhost` 在 IPv6 优先的机器上会解析到 `::1`，
  Chromium 只听 127.0.0.1 → `ECONNREFUSED`；且代理环境下 ws 会被劫持挂死。
- `connect_over_cdp` 失败 → `OpError("NOT_CONNECTED", ..., "先运行 deapctl login")`。
- 只有 `login`（`auto_launch=True` / `cmd_login`）会拉起浏览器；普通命令**不自动拉起**。
- 浏览器解析 `_resolve_browser(explicit)`，五层兜底（2026-10 加）：
  ① `--browser` 参数 → ② `DEAPCTL_BROWSER` env → ③ `BROWSER_CANDIDATES`
  路径探测（Chrome/Edge/Brave/Chromium）→ ④ Windows 注册表 App Paths
  → ⑤ Playwright bundled Chromium（扫 `ms-playwright/chromium-*`，**不启动
  driver**——`Session.__init__` 已持有一个 playwright 实例，嵌套 start 会炸）。
  错误码仍叫 `NO_CHROME`（envelope 契约），语义已是「Chromium 系浏览器」。
- 专用 profile：`~/.deapctl/profile`（`profile_dir()`），扫码一次长期有效；
  不要指向用户日常 Chrome 的 profile。

## 页面选择与视口

- `_find_deap_page`：已开页面中优先取 URL 含 `#/agent` 的 `deap.dingtalk.com` 页；
  找不到则新开页 `goto(DEAP_URL)`。
- 固定 viewport `1424×900`：画布坐标点击（wfnode）依赖稳定布局，**不要改**。
- `ensure_login` 是文本启发式：页面含「新建智能体/智能体」且无「扫码」即放行；
  否则 `NOT_LOGGED_IN`。新页面形态下登录判定失效时改这里。

## `__deap` 存活范围（隐式不变量）

`B.__init__` 时 `install(page)` 注入一次 `window.__deap`。DEAP 是 SPA，
全部 `page.goto("#/...")` 都是**同文档 hash 跳转**，JS 上下文不重建，`__deap` 一直活着——
这是 ops 层不重复 install 就能工作的原因。

若未来出现整页 reload 的导航，`__deap` 会消失：此时 `b.text()` 有兜底仍能读文本，
但 `__deap.vis/clickEl/fillIn` 会全挂。症状 = 大量 `SELECTOR_MISS`/JS 异常，
修法 = 重新 `install(page)`（`deapctl/browser.py`）。iframe 弹层不走 `__deap`，
用 `page.frames` 逐个 evaluate（wfnode `_pick_base` 是范式）。

## 改动注意

- `cmd_login` 是独立流程（自带 playwright ctx + 轮询扫码文案），不要复用 `Session`；
  其 `browser` 参数透传 `--browser` / `DEAPCTL_BROWSER` 的显式指定。
- 加会话级能力（如新登录判定、profile 迁移）时，同步 `cmd_status` 的输出字段。
