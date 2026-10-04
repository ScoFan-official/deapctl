#!/usr/bin/env python -X utf8
"""scaffold.run 修复验证：用真实签名绑定的 stub 驱动全流程，不依赖 CDP 会话。

每个 stub 先用 inspect.signature(真实函数).bind 校验 scaffold 的调用实参
能绑定到真实签名（即调用名+形参顺序正确），再记录调用、返回 envelope。
"""
import inspect
import json
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, ".")
from deapctl.envelope import ok
from deapctl.ops import agent as ag, knowledge, mcps
from deapctl.recipes import scaffold

CALLS = []


def stub(mod, fname, ret):
    real = getattr(mod, fname)
    sig = inspect.signature(real)

    def fake(*a, **kw):
        sig.bind(*a, **kw)  # 实参必须能绑定真实签名
        CALLS.append((fname, a, kw))
        return ret

    setattr(mod, fname, fake)


def main():
    persona = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    persona.write("你是验收测试机器人。")
    persona.close()

    stub(ag, "list_agents", ok({"agents": [{"name": "别的智能体"}], "count": 1}))
    stub(ag, "create_agent", ok({"name": "验收测试", "uuid": "u-1"}))
    stub(ag, "persona_set", ok({"name": "验收测试", "saved": True}))
    stub(ag, "save_agent", ok({"name": "验收测试", "saved": True}))
    stub(knowledge, "attach", ok({"agent": "验收测试", "added": True}))
    stub(mcps, "attach", ok({"agent": "验收测试", "added": True}))

    args = SimpleNamespace(name="验收测试", desc="x", persona_file=persona.name,
                           knowledge="周报知识集", mcp="钉钉待办, AI表格")

    # 第一遍：全步骤新建
    res = scaffold.run(None, args)
    assert res["ok"] and res["data"]["agent"] == "验收测试", res
    kinds = [(s["step"], "ok" in s) for s in res["data"]["steps"]]
    print("run1 steps:", res["data"]["steps"])
    assert [s["step"] for s in res["data"]["steps"]] == ["create", "persona", "knowledge", "mcp", "mcp", "save"]

    # 第二遍：同名已存在 → create 幂等跳过
    CALLS.clear()
    stub(ag, "list_agents", ok({"agents": [{"name": "验收测试"}], "count": 1}))
    res2 = scaffold.run(None, args)
    print("run2 steps:", res2["data"]["steps"])
    assert res2["data"]["steps"][0] == {"step": "create", "skipped": "already-exists"}
    assert not any(c[0] == "create_agent" for c in CALLS), "已存在却调了 create_agent"

    # 第三遍：无可选参数 → 只 create+save
    res3 = scaffold.run(None, SimpleNamespace(name="新", desc="", persona_file=None,
                                              knowledge=None, mcp=""))
    assert [s["step"] for s in res3["data"]["steps"]] == ["create", "save"]

    print(json.dumps({"ok": True, "verified_calls": sorted({c[0] for c in CALLS})}, ensure_ascii=False))


if __name__ == "__main__":
    main()
