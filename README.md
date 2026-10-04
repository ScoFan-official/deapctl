# deapctl — DEAP 控制台自动化 CLI

通过 Chromium 系浏览器 CDP 驱动已登录的 DEAP 控制台（https://deap.dingtalk.com），
把「创建/修改智能体、配置工作流」这类**只有管理界面能做、API KEY 做不了**
的操作封装成机器可消费的命令。面向 AI Agent：全量 JSON envelope 输出、
稳定错误码、幂等设计。**不提供发布能力**——所有操作停留在草稿域。

> **全局参数**：`--browser <exe>`（或 `DEAPCTL_BROWSER` 环境变量）指定浏览器可执行文件；
> `--cdp-url`（默认 `http://127.0.0.1:9222`，注意不是 `localhost`）覆盖 CDP 地址。

## 用法

```bash
# 会话（专用 profile ~/.deapctl/profile，扫码一次长期有效）
# 支持 Chromium 系浏览器：--browser <exe> / DEAPCTL_BROWSER / 自动探测 / Playwright bundled Chromium
python -m deapctl login            # 首次：拉起专用浏览器（Chromium 系）并等待登录
python -m deapctl status           # 自检 CDP + 登录态

# 智能体
python -m deapctl agent list
python -m deapctl agent create "周报助手" --desc "..." --dept "AI应用实验室"
python -m deapctl agent persona set "周报助手" --file persona.md
python -m deapctl agent delete "测试机" --yes   # 破坏性操作须 --yes

# 对话配置
python -m deapctl conv welcome set "周报助手" --text "你好，我可以…"
python -m deapctl conv tips set "周报助手" --text "试试问我"
python -m deapctl conv guides set "周报助手" --qs "帮我整理周报|今天有什么会|待办有哪些"
python -m deapctl conv quick-btn add "周报助手" "听记拆解" "把这段听记拆解成任务"

# 挂载
python -m deapctl knowledge list "周报助手"
python -m deapctl mcp attach "周报助手" "钉钉待办"

# 工作流（卡片级）
python -m deapctl workflow create "周报助手" "听记任务拆解" --desc "..."
python -m deapctl workflow enable|disable|save|check|runs "周报助手" "听记任务拆解"
python -m deapctl workflow debug "周报助手" "听记任务拆解" --params '{"听记原文":"..."}'

# 工作流（节点级，进编辑器）
python -m deapctl node list "周报助手" "听记任务拆解"
python -m deapctl node insert "周报助手" "听记任务拆解" "向大模型提问" --after 1
python -m deapctl node param-add "周报助手" "听记任务拆解" "听记原文" --desc "粘贴的听记文本"
python -m deapctl node config "周报助手" "听记任务拆解" "2." --spec '{
  "type":"llm","model":"通义千问3.0-max",
  "question_vars":["听记原文"],"prompt":"你是任务拆解助手…",
  "json_mode":"{\"任务清单\":[{\"任务标题\":\"x\",\"负责人\":\"y\"}]}"}'

# 声明式：一条命令建整条工作流（spec 可 git 化）
python -m deapctl workflow apply "周报助手" "任务确认入表" -f examples/confirm-to-table.json --force

# 场景层：一条命令装配草稿智能体
python -m deapctl scaffold --name "周报助手" --desc "..." --persona-file persona.md --mcp "钉钉待办,AI表格"

# 降级通道：不支持 CLI 的 Agent 走 stdio MCP
python -m deapctl mcp-server    # tools/list 暴露 deap_* 同名能力
```

## 设计要点（为什么难，怎么解的）

- **登录态**：专用 profile（`~/.deapctl/profile`）由 Chromium 系浏览器共享，扫码一次长期有效。浏览器解析五层兜底：`--browser` 参数 → `DEAPCTL_BROWSER` 环境变量 → 常见安装路径（Chrome/Edge/Brave/Chromium）→ Windows 注册表 App Paths → Playwright bundled Chromium（`playwright install chromium` 一次即永备）；浏览器不存在时自动用 bundled Chromium 兜底启动。
- **Slate 富文本**：人设/欢迎语/提示词是 contenteditable，`fill()` 无效——必须真实 `mouse.click` 聚焦 + `keyboard.type`。
- **变量芯片**：字段旁 `⊕` 需真实鼠标点击（合成事件不开面板）；且**必须先点编辑区聚焦再点 ⊕**，否则面板空渲染。叶子在虚拟化树里，支持滚动/展开组；叶子点击用 dispatch（真实点击被抽屉遮挡）。
- **循环子节点**：编辑器里往循环体加节点**总是落在顶部**，多子节点请倒序写入 spec.children。
- **类型过滤**：变量面板按字段类型过滤（日期字段只列日期时间变量、人员字段只列人员对象）——绑定失败时报 `VAR_TYPE_MISMATCH`。
- **枚举字段**：优先级/状态是枚举，不能绑变量，用 `fixed` 写字面值。
- **检查清单**：`workflow check` 读真实「检查清单」面板，会报出空节点/失效变量。

## 错误码

| code | 含义 |
|---|---|
| `OK` | 成功 |
| `ALREADY` | 幂等命中、已是目标状态（`ok:true`） |
| `USAGE` | 参数缺失 / 需 `--yes` / 未知子命令（exit 2） |
| `NOT_CONNECTED` | CDP 不可达（先运行 `deapctl login`） |
| `NOT_LOGGED_IN` | DEAP 未登录 |
| `NO_CHROME` | 找不到 Chromium 系浏览器（五层兜底均失败） |
| `TIMEOUT` | 登录/启动等待超时 |
| `NOT_FOUND` | 目标对象不存在 |
| `SELECTOR_MISS` | UI 找不到预期控件，改版最常见——配 `--debug-dom <file>` 抓现场 |
| `CREATE_FAILED` | 提交后回读未生效 |
| `EXISTS` | 目标已存在且未 `--force` |
| `VAR_TYPE_MISMATCH` | 变量面板按类型过滤、叶子不可选 |
| `INTERNAL` | 未捕获异常兜底 |

## 已知边界

- 无发布命令（刻意的）。
- AI 表格数据读写不属于这里（用 `dws aitable`）。
- DEAP 前端改版会让选择器失效：失败加 `--debug-dom dump.txt` 交回排查。
- 调试预览里钉钉待办/通讯录 MCP 不可直调（平台限制，非本工具问题）。
- `node config` 变量绑定存在时序性 `SELECTOR_MISS`：`param-add` 后立即绑定时变量面板可能未刷新，已知问题而非工具性错误（见 `.scratch/inbox/02-node-config-var-miss.md`）。
