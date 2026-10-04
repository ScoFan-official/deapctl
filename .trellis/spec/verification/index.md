# 验证与覆盖面

本仓库**没有离线单元测试**——所有验证都是对真实已登录 DEAP 后台的端到端操作。

前置条件：`python -m deapctl status` 返回 `ok:true`（否则先 `python -m deapctl login` 扫码）。

## 验收矩阵 `verify_all.py`

```bash
python verify_all.py [--agent 名字] [--keep]
```

- subprocess 逐条跑 `python -m deapctl`，解析 envelope 断言 `ok`；
  另有两处回读断言（persona / quick-btn）。
- 覆盖全命令面：status → agent → conv → 挂载读 → workflow 卡片 → 节点 → 收尾清理。
- 默认在专用测试智能体 `deapctl测试机` 上跑并跑完删除；`--keep` 保留供排查。
- **改任何 ops/recipes 行为后至少跑一遍；新增命令必须往矩阵里加行**——
  它是仓库唯一的回归网。

## `coverage.md`

- 每条能力的实测状态：✅ 端到端实测 / 🟡 部分实测 / ⚪ 未验证。
- 代码变更让能力状态变化时同步更新；新能力新增行。
- 末节「硬知识」= 改版后再调参考的实测结论；新踩的 selector 坑沉淀到这一节
  （同时把可复用写法写回 `spec/ops/ui-patterns.md`）。

## `--debug-dom`

所有命令支持 `--debug-dom <file>`：`OpError` 时把当前页文本（top 20000 字）写入文件。
`SELECTOR_MISS` / DEAP 前端改版排查的第一步；让用户报 bug 时带上这个参数复现。

## TDD 在本仓库的落地

- 「红」= `verify_all.py` 新增行失败，或 `--debug-dom` 复现的 `SELECTOR_MISS`/断言失败。
- 「绿」= 该命令 envelope `ok:true` 且回读断言通过。
- 没有 mock 层——不要为了可测性抽象 ops；真实后台就是测试环境，
  测试对象是专用草稿智能体，操作全在草稿域（无发布风险）。
