# deapctl — 钉钉 DEAP 控制台自动化 CLI

**deapctl** 通过 Chromium 系浏览器 CDP（Chrome DevTools Protocol）驱动已登录的钉钉企业智能体平台控制台（[https://deap.dingtalk.com](https://deap.dingtalk.com)），将「创建/配置智能体、编排工作流、挂载 MCP 与知识库」等**仅管理后台界面支持、官方开放平台 API 暂未提供**的操作，封装为机器可调用的结构化 CLI 与 MCP 服务。

面向 AI Agent（如 Claude Code、Cursor、Devin 等自动化代理）设计：
- **机器友好**：所有命令统一采用标准 JSON Envelope 格式输出，自带结构化退出码契约。
- **状态可靠**：语义化稳定错误码与故障自愈提示，核心配置操作支持幂等。
- **安全约束**：**严格限制在草稿域（Draft Scope）**，刻意不提供发布（Publish）能力，确保生产发布必须由人工确认。

> **全局参数**：
> - `--browser <exe>`（或通过 `DEAPCTL_BROWSER` 环境变量）：指定浏览器可执行文件路径；
> - `--cdp-url <url>`：CDP 连接地址（默认 `http://127.0.0.1:9222`，注意使用 IP 而非 `localhost`）；
> - `--format {json,pretty}`：输出格式，默认 `json`，交互调试时可选用 `pretty`；
> - `--debug-dom <file>`：操作失败时将当前页面的文本与 DOM 摘要转储至指定文件，便于排查界面改版。

## 用法

```bash
# 会话（专用 profile 存储于 ~/.deapctl/profile，扫码登录一次长期有效）
# 支持 Chromium 系浏览器：--browser <exe> / DEAPCTL_BROWSER / 自动探测 / Playwright bundled Chromium
python -m deapctl login            # 首次：拉起专用浏览器（Chromium 系）并等待扫码登录
python -m deapctl status           # 自检 CDP 连接与控制台登录态

# 智能体管理
python -m deapctl agent list
python -m deapctl agent create "研发效能助手" --desc "研发团队日常效能助手" --dept "技术效能部"
python -m deapctl agent persona set "研发效能助手" --file persona.md
python -m deapctl agent delete "临时测试智能体" --yes   # 破坏性操作须加 --yes

# 对话与交互配置
python -m deapctl conv welcome set "研发效能助手" --text "你好！我是研发效能助手，可协助你查询流程与拆解工作任务。"
python -m deapctl conv tips set "研发效能助手" --text "输入会议纪要或需求说明，为你自动提取行动项"
python -m deapctl conv guides set "研发效能助手" --qs "如何申请发布窗口|生产故障报障流程|研发规范指引"
python -m deapctl conv quick-btn add "研发效能助手" "待办拆解" "请帮我把以下会议记录拆解为可执行的待办任务"

# 知识库与 MCP 插件挂载
python -m deapctl knowledge list "研发效能助手"
python -m deapctl mcp attach "研发效能助手" "钉钉待办"

# 工作流（卡片级操作）
python -m deapctl workflow create "研发效能助手" "会议纪要待办拆解" --desc "提取会议记录中的行动项并生成任务清单"
python -m deapctl workflow enable|disable|save|check|runs "研发效能助手" "会议纪要待办拆解"
python -m deapctl workflow debug "研发效能助手" "会议纪要待办拆解" --params '{"会议纪要":"1. 张三周五前完成接口设计 2. 李四负责编写单元测试"}'

# 工作流（节点级操作，进入画布编辑器）
python -m deapctl node list "研发效能助手" "会议纪要待办拆解"
python -m deapctl node insert "研发效能助手" "会议纪要待办拆解" "向大模型提问" --after 1
python -m deapctl node param-add "研发效能助手" "会议纪要待办拆解" "会议纪要" --desc "会议原始记录文本"
python -m deapctl node config "研发效能助手" "会议纪要待办拆解" "向大模型提问" --spec '{
  "type":"llm","model":"通义千问3.0-max",
  "question_vars":["会议纪要"],"prompt":"你是任务拆解助手，请从文本中提炼行动项…",
  "json_mode":"{\"任务清单\":[{\"任务标题\":\"x\",\"负责人\":\"y\"}]}"}'

# 声明式编排：基于 JSON Spec 一键装配整条工作流（支持 Spec Git 版本化）
python -m deapctl workflow apply "研发效能助手" "任务确认入表" -f examples/confirm-to-table.json --force

# 场景脚手架：一条命令创建并装配草稿智能体
python -m deapctl scaffold --name "研发效能助手" --desc "研发团队日常效能助手" --persona-file persona.md --mcp "钉钉待办,AI表格"

# 协议桥接：供不支持直接运行 CLI 的 Agent 走 stdio MCP
python -m deapctl mcp-server    # tools/list 暴露 deap_* 同名操作能力
```

## 设计要点（为什么难，怎么解的）

- **登录态持久化**：使用独立专用的用户数据目录（`~/.deapctl/profile`），首次扫码登录后 Chromium 共享会话，长期免登。浏览器路径支持五层自动探测与回退机制：`--browser` 命令行参数 → `DEAPCTL_BROWSER` 环境变量 → 常见安装路径（Chrome / Edge / Brave / Chromium）→ Windows 注册表 App Paths → Playwright 自带 Chromium（`playwright install chromium`）。系统未检测到可用浏览器时会自动利用 Playwright 内置 Chromium 兜底拉起。
- **Slate.js 富文本编辑**：控制台中的人设、欢迎语、提示词等输入框基于 Slate.js（`contenteditable`）构建，常规 DOM `fill()` 赋值无法触发内部状态更新。必须通过真实鼠标 `mouse.click` 聚焦激活，再配合 `keyboard.type` 键入字符。
- **变量芯片与选择面板**：输入框旁的变量插入按钮（`⊕`）需真实鼠标物理点击触发（合成事件无法激活浮层面板）；且**必须先聚焦编辑区再点击 `⊕`**，否则面板呈空状态。面板内的虚拟化变量树支持动态滚动与组展开；叶子项选择采用事件派发触发（规避侧边抽屉遮挡导致的物理点击命中偏移）。
- **循环节点倒序插入**：在 DEAP 流程画布中向循环体容器内添加子节点时，新节点默认置于容器最顶端。因此声明式 spec 中的子节点定义推荐按直观的执行顺序书写，执行器在解析插入时会自动倒序操作以保证拓扑顺序一致。
- **强类型变量过滤**：变量选择面板按字段数据类型进行严格过滤（如日期字段只展示日期时间变量、人员字段只展示人员对象），类型不匹配时将拦截并抛出 `VAR_TYPE_MISMATCH` 错误码。
- **枚举属性固定字面值**：任务优先级、状态等枚举下拉字段在控制台不支持直接绑定动态变量，在配置中需使用 `fixed` 写入固定字面值。
- **原生检查清单体检**：`workflow check` 命令直接读取控制台原生的「检查清单」面板，能够可靠捕获未配置的空节点、失效引用变量等配置漏洞。

## 错误码

所有命令均向标准输出（stdout）输出统一的 JSON Envelope 结构：

```json
{
  "ok": true,
  "code": "OK",
  "message": "操作成功",
  "data": {},
  "hint": "可选的下一步排查或操作指引"
}
```

进程退出码（Exit Code）遵循确定性契约：
- `0`：操作成功（`ok: true`）
- `2`：命令行参数错误、缺少必填项或未传 `--yes` 确认（`code: "USAGE"`）
- `3`：各类运行时异常或业务逻辑失败（`ok: false`）

Envelope `code` 规范定义如下：

| code | 含义与常见场景 |
|---|---|
| `OK` | 操作成功执行 |
| `ALREADY` | 幂等命中，当前状态已满足预期（`ok: true`） |
| `USAGE` | 参数缺失、破坏性操作未携带 `--yes`，或输入了未知子命令 |
| `NOT_CONNECTED` | 无法连接到浏览器 CDP 端口（请先运行 `python -m deapctl login`） |
| `NOT_LOGGED_IN` | DEAP 控制台尚未登录或登录态已失效 |
| `NO_CHROME` | 宿主机未找到可用的 Chromium 系浏览器（五层探测均未命中） |
| `TIMEOUT` | 等待登录扫码或页面元素加载超时 |
| `NOT_FOUND` | 指定的智能体、工作流、节点或变量不存在 |
| `SELECTOR_MISS` | 控制台 UI 找不到预期控件（多见于界面改版），建议配合 `--debug-dom <file>` 排查现场 |
| `CREATE_FAILED` | 创建或提交后界面回读未生效 |
| `EXISTS` | 目标对象已存在，且未指定 `--force` 参数 |
| `VAR_TYPE_MISMATCH` | 变量类型不兼容（如将文本变量绑定至人员/日期类型字段） |
| `INTERNAL` | 未捕获的内部异常兜底 |

## 已知边界

- **仅限草稿域（刻意设计，不提供发布能力）**：所有配置操作均停留在草稿状态，不提供线上发布（Publish）指令。生产发布必须由人工在控制台确认并操作，确保变更可审计与受控。
- **不承载业务数据读写**：AI 表格等具体业务数据的增删改查属于数据接口范畴，不属于控制台配置自动化范围。
- **界面结构依赖**：底层依赖 DEAP 控制台的前端 DOM 结构。若平台控制台发生 UI 改版，可能导致选择器失配；可通过追加 `--debug-dom <file>` 导出当前页面文本与 DOM 现场以便排查与适配。
- **控制台预览区沙箱限制**：在 DEAP 编辑器的调试预览面板中，部分平台内置 MCP 插件（如钉钉待办、通讯录等）受平台沙箱机制限制无法直接交互，但在工作流节点中编排运行正常。
