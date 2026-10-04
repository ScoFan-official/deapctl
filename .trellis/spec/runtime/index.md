# Runtime 层（envelope / session / browser）

`deapctl/` 根下三个共享模块，每条命令都经过它们：

- `deapctl/envelope.py` — 统一输出契约 `{ok, code, message, data, hint}` + `OpError` + exit code
- `deapctl/session.py` — CDP 连接、专用 Chrome profile、登录态探测、`Session` 生命周期
- `deapctl/browser.py` — `__deap` JS 工具集 + `B` 操作面（查询 / 点击 / 填充 / 弹层）

## Pre-Development Checklist

- [ ] 输出格式、新增/调整错误码 → [envelope.md](envelope.md)
- [ ] 连接不上、登录流程、Chrome 启动、profile → [session.md](session.md)
- [ ] 页面定位、点击、输入、弹层作用域、等待节奏 → [dom-toolkit.md](dom-toolkit.md)

## Quality Check

- [ ] 没有向 stdout 写 envelope 以外的东西（print / logging 默认 handler 都不行）
- [ ] 失败路径是 `OpError(code, message, hint)`，不是裸 dict / print / sys.exit
- [ ] 新选择器遵守「语义优先」并在失败时抛 `SELECTOR_MISS` + 可行动 hint
- [ ] 复用 `sess.b.*` 操作面；ops 里不直接写 `page.evaluate` 长逻辑
