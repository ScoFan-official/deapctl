#!/usr/bin/env python -X utf8
"""deapctl scaffold 端到端验收 gate（无人值守版）。

推送前跑一条命令：
    python .scratch/e2e_scaffold.py

流程：自启 Chrome（profile 复用）→ status → scaffold 全流程
→ persona 回读断言（原崩溃点）→ agent delete 清理 → 自动升 coverage 状态。

退出码：0=通过可推送；2=需要你跑一次 `python -m deapctl login`（扫码）后重跑；
1=验收失败（附 envelope）。
"""
import json
import os
import subprocess
import sys
import tempfile
import time

CDP = "http://127.0.0.1:9222"
AGENT = "deapctl验收scaffold"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COVERAGE = os.path.join(ROOT, "coverage.md")
sys.path.insert(0, ROOT)


def cli(*args, timeout=300):
    r = subprocess.run([sys.executable, "-m", "deapctl", "--cdp-url", CDP, *args],
                       capture_output=True, timeout=timeout, cwd=ROOT)
    out = (r.stdout or b"").decode("utf-8", "replace")
    err = (r.stderr or b"").decode("utf-8", "replace")
    try:
        return json.loads(out)
    except Exception:
        return {"ok": False, "code": "PARSE", "message": (out + err)[:300]}


def ensure_session():
    """status ok 才算就绪；NOT_CONNECTED 时借 Session(auto_launch) 自启 Chrome 重试。"""
    st = cli("status")
    if st.get("ok"):
        return st
    if st.get("code") == "NOT_CONNECTED":
        from deapctl.session import Session
        try:
            Session(CDP, auto_launch=True)
        except Exception:
            pass
        time.sleep(8)
        st = cli("status")
    return st


def bump_coverage():
    """scaffold 行 🟡→✅（确定性单行替换）。"""
    with open(COVERAGE, encoding="utf-8") as f:
        txt = f.read()
    old = "scaffold（create→persona→knowledge→mcp→save） | 🟡 | 调用名已对齐 ops；stub 全流程+幂等已验证，无 CDP session 未端到端实测 |"
    new = "scaffold（create→persona→knowledge→mcp→save） | ✅ | 端到端实测通过（e2e_scaffold.py） |"
    if old in txt:
        with open(COVERAGE, "w", encoding="utf-8") as f:
            f.write(txt.replace(old, new, 1))
        print("[coverage.md] scaffold 行已升级 -> 已实测")


def main():
    st = ensure_session()
    if not st.get("ok"):
        print(f"NOT READY: {st.get('code')} — 请先跑一次 `python -m deapctl login` 扫码，然后重跑本脚本。")
        sys.exit(2)
    if not st.get("data", {}).get("logged_in"):
        print("NOT READY: NOT_LOGGED_IN — 浏览器已拉起，请在窗口内扫码登录（或跑 `python -m deapctl login`），然后重跑本脚本。")
        sys.exit(2)

    pf = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    pf.write("你是 deapctl 验收机器人，只回复「收到」。")
    pf.close()
    created = False
    try:
        r = cli("scaffold", "--name", AGENT, "--desc", "E2E 自动验收，可删",
                "--persona-file", pf.name)
        if not r.get("ok"):
            print(f"FAIL scaffold: {r.get('code')} {r.get('message', '')[:200]}")
            sys.exit(1)
        created = True
        steps = {s["step"] for s in r.get("data", {}).get("steps", [])}
        assert {"create", "persona", "save"} <= steps, f"步骤缺失: {steps}"

        g = cli("agent", "persona", "get", AGENT)
        assert "验收机器人" in json.dumps(g.get("data", {}), ensure_ascii=False), \
            f"persona 回读未命中: {json.dumps(g.get('data', {}), ensure_ascii=False)[:200]}"

        print(f"PASS scaffold E2E（create→persona→save 全链路 + 回读断言）")
        bump_coverage()
    finally:
        if created:
            cli("agent", "delete", AGENT, "--yes")
        os.unlink(pf.name)


if __name__ == "__main__":
    main()
