# node config 变量绑定 SELECTOR_MISS（疑似回归/flake）

**Status**: fixed（2026-10-04，搜索直达替代 expand/scroll）
**Date**: 2026-10-03
**Source**: verify_all.py 全量回归（31/32 通过，唯一失败）

## 现象

```
node config deapctl测试机 验收测试流 2. --spec
  {"type":"llm","model":"通义千问3.0-max","question_vars":["听记原文"],...}
→ SELECTOR_MISS 变量 '听记原文' 未选中
```

## 复现路径

verify_all.py 顺序：`node param-add 听记原文`（✅ 创建成功）→ `node insert 向大模型提问 --after 1`（✅）→ `node config ... 2.`（✗ 绑定失败）。

变量是 **param-add 后几秒**立即绑定的——疑似 picker-pane_ 变量面板未刷新，或
`pick_var` 的文本过滤没等到新变量出现（时序问题）。

## 矛盾点

coverage.md 标 `llm config` 变量绑定 ✅（之前测通过）→ 回归或间歇性。

## 建议排查方向（diagnosing-bugs）

红命令就是 verify_all.py 该行，已可重复。候选：
1. `wfnode.pick_var` 在展开 `picker-pane_` 后先读列表再断言，加短重试等待变量出现；
2. 抽屉重开时变量面板缓存了旧列表——`param-add` 后是否需要重新打开节点抽屉；
3. `--debug-dom` 抓失败瞬间页面文本看面板里到底有没有「听记原文」。

## 环境

bundled Chromium（playwright chromium-1234），profile 已登录。
与本次 confirm_modal/session 改动无关——node config 不走确认弹窗路径。

## 修复记录（2026-10-04）

**根因**：`pick_var`/`_bind_record_field` 靠「展开折叠组 + 滚动虚拟化树」遍历
变量面板找叶子，渲染时序不稳定，4 轮尝试内叶子可能未渲染 → 间歇性漏选。

**修复**：picker-pane_ 内自带 `input.dtd-search-bar-input` 搜索框
（"搜索关键字或变量名称"），搜索是权威过滤。两处选择循环改为：
精确匹配 → 有搜索框则 fillIn 变量名直达 → 已搜索仍无 = 变量缺失/类型过滤，
带 `no-leaf-searched:` + 剩余标题报错；无搜索框才回退 expand/scroll。
picked 后清空搜索框防残留过滤。

**验证**：复测机 param-add → insert → config 绑 `听记原文` ✅；
不存在变量报错信息改善为「已用面板搜索过滤确认不在列表中」。

