# Envelope 输出契约与错误码

每条命令 stdout 只输出一个 JSON：`{ok, code, message, data, hint?}`。
`emit()` 退出码：ok → 0，`code=="USAGE"` → 2，其余失败 → 3。
定义见 `deapctl/envelope.py`；边界兜底见 `deapctl/cli.py` `main()`。

## 规则

- 成功：`ok(data, message, hint?)`；`data` 放调用方（agent）要消费的机器可读状态
  （列表、uuid、saved 标记、回读结果）。
- 失败：`raise OpError(code, message, hint, data?)`，由 `cli.py` 统一转 `err_result`。
  `hint` = 给调用方的下一步行动（该跑什么命令/怎么排查），不是重复解释错误。
- `OpError("USAGE", ...)` 用于参数缺失、需 `--yes` 确认、未知子命令（exit 2）。
- 不要手动 catch-all：未捕获异常由 `main()` 兜底成 `INTERNAL` + traceback 到 stderr。
- 幂等命中：先 `ok(...)` 再 `res["code"] = "ALREADY"`（ops/mcps.py `attach`、
  ops/workflow.py `create`/`enable`）。
- 禁止在 ops/recipes 里 print 或写 stdout；`--format pretty` 由 `emit` 统一处理。

## 实际使用的 code 表（以代码为准，改词汇表时同步本表与 README）

| code | 含义 | 出处示例 |
|---|---|---|
| `OK` | 成功 | `envelope.ok` |
| `ALREADY` | 幂等命中、已是目标状态（ok:true） | `ops/mcps.py` `attach`，`ops/workflow.py` |
| `USAGE` | 参数缺失 / 需 --yes / 未知子命令 | `ops/agent.py` `delete_agent`，各 `route()` |
| `NOT_CONNECTED` | CDP 不可达 | `session.py` `Session.__init__`、`cmd_status` |
| `NOT_LOGGED_IN` | DEAP 未登录 | `session.py` `ensure_login` |
| `NO_CHROME` | 找不到 Chrome 可执行文件 | `session.py` `_launch` |
| `TIMEOUT` | 登录/启动等待超时 | `session.py` |
| `NOT_FOUND` | 目标对象不存在 | `ops/agent.py` `_find` |
| `SELECTOR_MISS` | UI 找不到预期控件（改版最常见） | 全 ops 层 |
| `CREATE_FAILED` | 提交后回读未生效 | `ops/agent.py` `create_agent`、`ops/conv.py` `qbtn_add` |
| `EXISTS` | 目标已存在且未 `--force` | `recipes/wf_apply.py` |
| `VAR_TYPE_MISMATCH` | 变量面板按类型过滤、叶子不可选 | `ops/wfnode.py` `_bind_record_field` |
| `INTERNAL` | 未捕获异常兜底 | `cli.py` `main` |

注意：README「错误码」一节列的 `LOGIN_REQUIRED`/`CONFIRM_REQUIRED` 在代码中
实际实现为 `NOT_LOGGED_IN` 与 `USAGE`（--yes 拦截）。以本表为准。
