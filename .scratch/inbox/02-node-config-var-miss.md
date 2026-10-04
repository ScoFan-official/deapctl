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

**真根因（两层叠加）**：

1. **节点未持久化**：`insert_node`/`insert_into_loop`/`delete_node` 都不调
   `save()`——改动只活在画布内存态。`param_add` 开抽屉再 save 时编辑器
   从持久态重渲染，未保存的插入节点被丢弃 → 后续 `find_node` 报 NOT_FOUND，
   或误命中同序号包装节点开错抽屉（第一次 verify_all 的"变量未选中"很可能
   就是 LLM 节点丢失后 "2." 命中了「就执行/指定操作」包装节点、面板里
   自然没有该变量——误诊为 pick_var 时序问题）。
   **修复**：三个节点变更操作末尾补 `self.save()`；verify_all 节点选择器
   从硬编码 "2." 改为标题 "向大模型提问"（画布上无编号包装节点占位、
   序号会漂移，标题选择器才稳）。

2. **pick_var 遍历脆弱（顺带修复）**：原靠 expand/scroll 遍历虚拟化树
   找叶子。picker-pane_ 自带 `input.dtd-search-bar-input` 搜索框，搜索是
   权威过滤——改为搜索直达；搜后仍无 = 变量缺失/类型不匹配，报错带上下文；
   无搜索框才回退 expand/scroll；picked 后清空搜索框。

**验证**：复测机 insert → param-add → config 绑 `听记原文` 全链路 ✅
（param-add 的 save 后 LLM 节点仍在画布）；不存在变量报错信息改善。

