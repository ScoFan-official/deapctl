"""deapctl stdio MCP server — 给不支持 CLI 的 Agent 用。

协议：JSON-RPC over stdio（MCP 规范最小集：initialize/tools/list/tools/call）。
工具即 deapctl 子命令的薄封装，统一返回 envelope JSON 文本。
"""
import json
import subprocess
import sys

TOOLS = [
    {"name": "deap_status", "description": "检查 CDP 连接与登录态", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "deap_agent_list", "description": "列出全部智能体", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "deap_agent_get", "description": "读智能体详情", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
    {"name": "deap_agent_create", "description": "创建草稿智能体（不发布）", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "desc": {"type": "string"}}, "required": ["name"]}},
    {"name": "deap_persona_set", "description": "写人设/系统提示词", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}, "text": {"type": "string"}}, "required": ["name", "text"]}},
    {"name": "deap_welcome_set", "description": "写欢迎语", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "text": {"type": "string"}}, "required": ["agent", "text"]}},
    {"name": "deap_workflow_list", "description": "列工作流卡片", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}}, "required": ["agent"]}},
    {"name": "deap_workflow_create", "description": "建工作流并进编辑器", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "name": {"type": "string"}, "desc": {"type": "string"}}, "required": ["agent", "name"]}},
    {"name": "deap_workflow_apply", "description": "按 spec 文件声明式建/改工作流", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "name": {"type": "string"}, "file": {"type": "string"}, "force": {"type": "boolean"}}, "required": ["agent", "name", "file"]}},
    {"name": "deap_workflow_debug", "description": "调试运行工作流", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "name": {"type": "string"}, "params": {"type": "object"}}, "required": ["agent", "name"]}},
    {"name": "deap_node_list", "description": "列工作流编辑器节点", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "workflow": {"type": "string"}}, "required": ["agent", "workflow"]}},
    {"name": "deap_node_insert", "description": "插入节点（类型如 向大模型提问/循环/新增记录）", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "workflow": {"type": "string"}, "type": {"type": "string"}, "after": {"type": "integer"}}, "required": ["agent", "workflow", "type"]}},
    {"name": "deap_node_config", "description": "按 JSON spec 配节点（llm/loop/record/end）", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "workflow": {"type": "string"}, "node": {"type": "string"}, "spec": {"type": "object"}}, "required": ["agent", "workflow", "node", "spec"]}},
    {"name": "deap_node_param_add", "description": "给工作流触发节点加输入参数", "inputSchema": {"type": "object", "properties": {"agent": {"type": "string"}, "workflow": {"type": "string"}, "name": {"type": "string"}, "desc": {"type": "string"}, "optional": {"type": "boolean"}}, "required": ["agent", "workflow", "name"]}},
]


def _cli(args, cdp):
    cmd = [sys.executable, "-m", "deapctl", "--cdp-url", cdp] + args
    r = subprocess.run(cmd, capture_output=True, timeout=600)
    out = (r.stdout or b"").decode("utf-8", "replace").strip()
    return out or (r.stderr or b"").decode("utf-8", "replace").strip()


def _tool_to_argv(name, a):
    m = {
        "deap_status": ["status"],
        "deap_agent_list": ["agent", "list"],
        "deap_agent_get": ["agent", "get", a["name"]],
        "deap_agent_create": ["agent", "create", a["name"], "--desc", a.get("desc", "")],
        "deap_persona_set": ["agent", "persona", "set", a["name"], "--text", a["text"]],
        "deap_welcome_set": ["conv", "welcome", "set", a["agent"], "--text", a["text"]],
        "deap_workflow_list": ["workflow", "list", a["agent"]],
        "deap_workflow_create": ["workflow", "create", a["agent"], a["name"], "--desc", a.get("desc", "")],
        "deap_workflow_apply": ["workflow", "apply", a["agent"], a["name"], "-f", a["file"]] + (["--force"] if a.get("force") else []),
        "deap_workflow_debug": ["workflow", "debug", a["agent"], a["name"], "--params", json.dumps(a.get("params", {}), ensure_ascii=False)],
        "deap_node_list": ["node", "list", a["agent"], a["workflow"]],
        "deap_node_insert": ["node", "insert", a["agent"], a["workflow"], a["type"], "--after", str(a.get("after", -1))],
        "deap_node_config": ["node", "config", a["agent"], a["workflow"], a["node"], "--spec", json.dumps(a["spec"], ensure_ascii=False)],
        "deap_node_param_add": ["node", "param-add", a["agent"], a["workflow"], a["name"], "--desc", a.get("desc", "")] + (["--optional"] if a.get("optional") else []),
    }
    return m.get(name)


def run_stdio(cdp_url):
    """最小 MCP stdio 循环。"""
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        try:
            req = json.loads(line)
        except Exception:
            continue
        rid, method, params = req.get("id"), req.get("method"), req.get("params") or {}
        if method == "initialize":
            res = {"protocolVersion": "2024-11-05",
                   "capabilities": {"tools": {}},
                   "serverInfo": {"name": "deapctl", "version": "0.1.0"}}
        elif method == "tools/list":
            res = {"tools": TOOLS}
        elif method == "tools/call":
            argv = _tool_to_argv(params.get("name"), params.get("arguments") or {})
            out = _cli(argv, cdp_url) if argv else json.dumps(
                {"ok": False, "code": "USAGE", "message": "unknown tool"}, ensure_ascii=False)
            res = {"content": [{"type": "text", "text": out}]}
        elif method in ("notifications/initialized", "ping"):
            if rid is None:
                continue
            res = {}
        else:
            if rid is None:
                continue
            res = None
        if rid is not None:
            reply = {"jsonrpc": "2.0", "id": rid}
            if res is None:
                reply["error"] = {"code": -32601, "message": f"method {method} not found"}
            else:
                reply["result"] = res
            sys.stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return ok_exit()


def ok_exit():
    return {"ok": True, "code": "OK", "message": "mcp server exited", "data": {}}
