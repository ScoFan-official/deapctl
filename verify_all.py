#!/usr/bin/env python -X utf8
"""deapctl 验收矩阵：在测试智能体上自动跑全命令面，逐条断言 envelope。

用法: python verify_all.py [--agent deapctl测试机] [--keep]
      --keep 跑完不删除测试智能体
"""
import json
import subprocess
import sys
import time

AGENT = "deapctl测试机"
WF = "验收测试流"
CDP = "http://127.0.0.1:9222"

RESULTS = []


def run(args, expect_ok=True, note=""):
    cmd = [sys.executable, "-m", "deapctl", "--cdp-url", CDP] + args
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    try:
        res = json.loads(out)
    except Exception:
        res = {"ok": False, "code": "PARSE", "message": (out + err)[:300]}
    passed = res.get("ok") is expect_ok
    RESULTS.append((passed, " ".join(args[:2]), note or res.get("code", ""), res))
    mark = "PASS" if passed else "FAIL"
    print(f"[{mark}] {' '.join(args)}  -> {res.get('code')} {res.get('message','')[:60]}")
    return res


def main():
    keep = "--keep" in sys.argv
    # 0. 环境
    run(["status"])

    # 1. agent 面
    run(["agent", "list"])
    res = run(["agent", "create", AGENT, "--desc", "deapctl 验收矩阵专用，可删"])
    run(["agent", "get", AGENT])
    run(["agent", "persona", "set", AGENT, "--text", "你是验收测试机器人，简短回答。"])
    r = run(["agent", "persona", "get", AGENT])
    ok_val = "验收测试" in json.dumps(r.get("data", {}), ensure_ascii=False)
    RESULTS.append((ok_val, "persona 回读", "assert", r))
    print(f"[{'PASS' if ok_val else 'FAIL'}] persona 回读断言")
    run(["agent", "save", AGENT])

    # 2. 对话配置
    run(["conv", "welcome", "set", AGENT, "--text", "你好，我是验收机器人"])
    run(["conv", "tips", "set", AGENT, "--text", "试试问我"])
    run(["conv", "guides", "set", AGENT, "--qs", "帮我整理周报|今天有什么会|待办有哪些"])
    run(["conv", "quick-btn", "add", AGENT, "测试按钮", "点我测试"])
    r = run(["conv", "quick-btn", "list", AGENT])
    ok_val = "测试按钮" in json.dumps(r.get("data", {}), ensure_ascii=False)
    RESULTS.append((ok_val, "quick-btn 回读", "assert", r))
    print(f"[{'PASS' if ok_val else 'FAIL'}] quick-btn 回读断言")

    # 场景层（幂等路径：AGENT 已存在 → 跳过 create 直接 save）
    run(["scaffold", "--name", AGENT])

    # 3. 挂载读路径
    run(["knowledge", "list", AGENT])
    run(["mcp", "catalog", AGENT])
    run(["mcp", "list", AGENT])

    # 4. 工作流卡片级
    run(["workflow", "create", AGENT, WF, "--desc", "验收矩阵自动创建"])
    run(["workflow", "list", AGENT])
    run(["workflow", "check", AGENT, WF])
    run(["workflow", "disable", AGENT, WF])
    run(["workflow", "enable", AGENT, WF])

    # 5. 节点级
    run(["node", "list", AGENT, WF])
    run(["node", "param-add", AGENT, WF, "听记原文", "--desc", "粘贴的听记/纪要文本"])
    run(["node", "insert", AGENT, WF, "向大模型提问", "--after", "1"])
    run(["node", "config", AGENT, WF, "2.", "--spec",
         json.dumps({"type": "llm", "model": "通义千问3.0-max",
                     "question_vars": ["听记原文"],
                     "prompt": "把听记拆解为任务清单，输出 JSON。"}, ensure_ascii=False)])
    run(["workflow", "save", AGENT, WF])
    run(["workflow", "check", AGENT, WF])
    run(["workflow", "runs", AGENT, WF])

    # 6. 收尾
    if not keep:
        run(["workflow", "delete", AGENT, WF, "--yes"])
        run(["agent", "delete", AGENT, "--yes"])

    fails = [x for x in RESULTS if not x[0]]
    print(f"\n===== {len(RESULTS)-len(fails)}/{len(RESULTS)} 通过 =====")
    if fails:
        for _, cmd, _, r in fails:
            print("FAIL:", cmd, r.get("code"), r.get("message", "")[:120])
        sys.exit(1)


if __name__ == "__main__":
    main()
