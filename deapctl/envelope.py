"""统一输出契约: {ok, code, message, data, hint}"""
import json
import sys


class OpError(Exception):
    def __init__(self, code, message, hint=None, data=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.data = data or {}


def ok(data=None, message="", hint=None):
    return {"ok": True, "code": "OK", "message": message, "data": data or {},
            **({"hint": hint} if hint else {})}


def err_result(e: OpError):
    return {"ok": False, "code": e.code, "message": e.message,
            "data": e.data, **({"hint": e.hint} if e.hint else {})}


def emit(result, pretty=False):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if pretty:
        _pretty(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if result.get("ok") else (2 if result.get("code") == "USAGE" else 3))


def _pretty(result):
    if not result.get("ok"):
        print(f"[{result['code']}] {result['message']}", file=sys.stderr)
        if result.get("hint"):
            print(f"hint: {result['hint']}", file=sys.stderr)
        return
    if result.get("message"):
        print(result["message"])
    d = result.get("data")
    if isinstance(d, list):
        for row in d:
            print("  " + "  ".join(f"{k}={v}" for k, v in row.items()) if isinstance(row, dict) else f"  {row}")
    elif isinstance(d, dict):
        for k, v in d.items():
            print(f"  {k}: {json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (list, dict)) else v}")
    if result.get("hint"):
        print(f"hint: {result['hint']}")
