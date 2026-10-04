# deapctl 操作覆盖面（实测记录）

图例：✅ 端到端实测通过 · 🟡 代码就绪、部分实测 · ⚪ 未验证/实验面

## 会话
| 能力 | 状态 | 备注 |
|---|---|---|
| login / status | ✅ | 专用 profile + CDP 重连 |

## 智能体
| 能力 | 状态 | 备注 |
|---|---|---|
| list / get | ✅ | 列表列名+描述拆分 |
| create（含部门） | ✅ | 企业智能体类型 |
| delete --yes | 🟡 | 同删除确认弹窗 |
| persona get/set | ✅ | 空人设兼容（最大可见 textarea） |
| save | ✅ | |

## 对话配置
| 能力 | 状态 | 备注 |
|---|---|---|
| welcome get/set | ✅ | |
| tips set | ✅ | verify_all 实测通过（bundled Chromium） |
| guides set | ✅ | --qs `|` 分隔最多3条；verify_all 实测通过 |
| quick-btn list/add/delete | ✅ | 预设输入是 Slate，真实键入 |

## 挂载
| 能力 | 状态 | 备注 |
|---|---|---|
| knowledge list/attach/detach | 🟡 | list 实测；attach 流程与列表同源 |
| mcp catalog/list/attach/detach | 🟡 | catalog/list 实测 |

## 工作流（卡片）
| 能力 | 状态 | 备注 |
|---|---|---|
| list | ✅ | |
| create | ✅ | 建完进编辑器 |
| meta / copy / delete | 🟡 | copy 实测 |
| enable / disable | 🟡 | switch 定位 |
| save / check / runs | ✅ | check 真实检出「节点不能为空」 |
| debug --params | 🟡 | 参数按 label 匹配填充 |
| apply -f spec | 🟡 | spec 驱动全链路 |

## 工作流（节点）
| 能力 | 状态 | 备注 |
|---|---|---|
| node list / add-points | ✅ | |
| insert（顶层） | ✅ | |
| insert_into_loop | 🟡 | 落顶部，需倒序 |
| delete（⋯菜单） | ✅ | |
| param-add（触发节点） | ✅ | 名称/类型/默认值/说明/必填 |
| llm config（模型/问题变量/提示词/结构化输出/JSON模式） | ✅ | 模型/变量绑定/提示词 E2E 实测（10-04 修复 pick_var 搜索直达后复测）；结构化输出/JSON模式早前手工验证同路径 |
| loop bind（数组变量） | 🟡 | |
| record config（base/table/字段绑定/枚举字面值） | 🟡 | base 选择在 iframe，已处理 |
| end config | 🟡 | |

## 场景层（recipes）
| 能力 | 状态 | 备注 |
|---|---|---|
| scaffold（create→persona→knowledge→mcp→save） | ✅ | 端到端实测通过（e2e_scaffold.py，bundled Chromium 上跑通） |

## 实验面（结论）
| 项 | 结论 |
|---|---|
| 主动触发 | 只收已发布技能 → 草稿域 `UNSUPPORTED_IN_DRAFT` |
| 预览窗 MCP 直调 | 不可调（平台限制）；工作流内节点可用 |
| 发布 | 刻意不提供 |

## 硬知识（改版后再调参考）
1. 循环内容必须绑「对象数组」类型变量 → 上游 LLM 需开 JSON 模式产出真数组
2. 变量面板按类型过滤；人员字段只收人员对象，日期字段只收日期时间
3. ⊕ 图标需真实 mouse.click；且先聚焦 Slate 再点 ⊕（否则面板空）
4. 叶子选择用 dispatch（picker 被抽屉遮挡，elementFromPoint 命不中）
5. 循环内 add 落顶部 → spec.children 正序写、执行器倒序插
6. 保存按钮是拆分按钮，点「保存」后可能有「仅保存」子项兜底
