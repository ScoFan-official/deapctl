"""deapctl 命令入口。全部命令输出统一 envelope JSON。"""
import argparse
import sys
import traceback

from .envelope import OpError, emit, err_result
from .session import Session, cmd_login, cmd_status

DEFAULT_CDP = "http://127.0.0.1:9222"


def _parser():
    p = argparse.ArgumentParser(prog="deapctl",
                                description="DEAP 控制台自动化 CLI（草稿域操作，不提供发布）")
    p.add_argument("--cdp-url", default=DEFAULT_CDP)
    p.add_argument("--browser", help="浏览器可执行文件路径（Chromium 系均可）")
    p.add_argument("--format", choices=["json", "pretty"], default="json")
    p.add_argument("--debug-dom", help="失败时把页面文本/DOM摘要写到该文件")
    sub = p.add_subparsers(dest="cmd")

    sub.add_parser("login", help="拉起专用浏览器（Chromium 系）并等待登录")
    sub.add_parser("status", help="检查 CDP 连接与登录态")

    a = sub.add_parser("agent")
    asub = a.add_subparsers(dest="sub")
    asub.add_parser("list")
    g = asub.add_parser("get"); g.add_argument("name")
    c = asub.add_parser("create"); c.add_argument("name"); c.add_argument("--desc", default=""); c.add_argument("--dept", default=None)
    d = asub.add_parser("delete"); d.add_argument("name"); d.add_argument("--yes", action="store_true")
    pe = asub.add_parser("persona"); pes = pe.add_subparsers(dest="sub2")
    pes.add_parser("get").add_argument("name")
    s = pes.add_parser("set"); s.add_argument("name"); s.add_argument("--file"); s.add_argument("--text"); s.add_argument("--append", action="store_true")
    asub.add_parser("save").add_argument("name")

    cv = sub.add_parser("conv")
    cvs = cv.add_subparsers(dest="sub")
    w = cvs.add_parser("welcome"); ws = w.add_subparsers(dest="sub2")
    ws.add_parser("get").add_argument("agent")
    x = ws.add_parser("set"); x.add_argument("agent"); x.add_argument("--text", required=True)
    t = cvs.add_parser("tips"); ts = t.add_subparsers(dest="sub2")
    tx = ts.add_parser("set"); tx.add_argument("agent"); tx.add_argument("--text", required=True)
    g = cvs.add_parser("guides"); gs = g.add_subparsers(dest="sub2")
    gx = gs.add_parser("set"); gx.add_argument("agent"); gx.add_argument("--qs", required=True, help="引导问题，| 分隔，最多3条")
    qb = cvs.add_parser("quick-btn"); qs = qb.add_subparsers(dest="sub2")
    qs.add_parser("list").add_argument("agent")
    qa = qs.add_parser("add"); qa.add_argument("agent"); qa.add_argument("name"); qa.add_argument("text")
    qu = qs.add_parser("update"); qu.add_argument("agent"); qu.add_argument("name"); qu.add_argument("--new-name"); qu.add_argument("--text")
    qd = qs.add_parser("delete"); qd.add_argument("agent"); qd.add_argument("name"); qd.add_argument("--yes", action="store_true")

    kn = sub.add_parser("knowledge")
    ks = kn.add_subparsers(dest="sub")
    ks.add_parser("list").add_argument("agent")
    ka = ks.add_parser("attach"); ka.add_argument("agent"); ka.add_argument("name")
    kd = ks.add_parser("detach"); kd.add_argument("agent"); kd.add_argument("name"); kd.add_argument("--yes", action="store_true")

    mc = sub.add_parser("mcp")
    ms = mc.add_subparsers(dest="sub")
    ms.add_parser("catalog").add_argument("agent")
    ms.add_parser("list").add_argument("agent")
    ma = ms.add_parser("attach"); ma.add_argument("agent"); ma.add_argument("name")
    md = ms.add_parser("detach"); md.add_argument("agent"); md.add_argument("name"); md.add_argument("--yes", action="store_true")

    wf = sub.add_parser("workflow")
    ws2 = wf.add_subparsers(dest="sub")
    ws2.add_parser("list").add_argument("agent")
    wc = ws2.add_parser("create"); wc.add_argument("agent"); wc.add_argument("name"); wc.add_argument("--desc", default=""); wc.add_argument("--examples", default="")
    wm = ws2.add_parser("meta"); wm.add_argument("agent"); wm.add_argument("name"); wm.add_argument("--new-name"); wm.add_argument("--desc"); wm.add_argument("--examples")
    wd = ws2.add_parser("delete"); wd.add_argument("agent"); wd.add_argument("name"); wd.add_argument("--yes", action="store_true")
    wcp = ws2.add_parser("copy"); wcp.add_argument("agent"); wcp.add_argument("name"); wcp.add_argument("--new-name", dest="new_name", default=None)
    we = ws2.add_parser("enable"); we.add_argument("agent"); we.add_argument("name")
    wdi = ws2.add_parser("disable"); wdi.add_argument("agent"); wdi.add_argument("name")
    wsa = ws2.add_parser("save"); wsa.add_argument("agent"); wsa.add_argument("name")
    wch = ws2.add_parser("check"); wch.add_argument("agent"); wch.add_argument("name")
    wde = ws2.add_parser("debug"); wde.add_argument("agent"); wde.add_argument("name"); wde.add_argument("--params", default="{}"); wde.add_argument("--timeout", type=int, default=120)
    wr = ws2.add_parser("runs"); wr.add_argument("agent"); wr.add_argument("name")
    ap = ws2.add_parser("apply"); ap.add_argument("agent"); ap.add_argument("name"); ap.add_argument("-f", "--file", required=True); ap.add_argument("--force", action="store_true")

    nd = sub.add_parser("node", help="工作流编辑器内节点操作")
    ns = nd.add_subparsers(dest="sub")
    nl = ns.add_parser("list"); nl.add_argument("agent"); nl.add_argument("workflow")
    ni = ns.add_parser("insert"); ni.add_argument("agent"); ni.add_argument("workflow"); ni.add_argument("type", help="如 向大模型提问/循环/条件分支/新增记录"); ni.add_argument("--after", type=int, default=-1, help="插入点：第几个'+'位（0起，-1=最后）")
    nde = ns.add_parser("delete"); nde.add_argument("agent"); nde.add_argument("workflow"); nde.add_argument("node", help="序号如'2.'或标题")
    npa = ns.add_parser("param-add"); npa.add_argument("agent"); npa.add_argument("workflow"); npa.add_argument("name"); npa.add_argument("--desc", default=""); npa.add_argument("--optional", action="store_true"); npa.add_argument("--type", default="文本")
    nc = ns.add_parser("config", help="按 JSON spec 配置节点"); nc.add_argument("agent"); nc.add_argument("workflow"); nc.add_argument("node"); nc.add_argument("--spec", required=True, help='如 {"type":"llm","model":"通义千问3.0-max","question_vars":["听记原文"],"prompt":"..."}')

    sc = sub.add_parser("scaffold", help="场景层：一条命令装配草稿智能体")
    sc.add_argument("--name", required=True); sc.add_argument("--desc", default="")
    sc.add_argument("--persona-file"); sc.add_argument("--knowledge"); sc.add_argument("--mcp", default="")

    sub.add_parser("mcp-server", help="以 stdio MCP server 运行（供不支持CLI的Agent接入）")

    return p


def dispatch(args):
    c, sub = args.cmd, getattr(args, "sub", None)
    if c == "login":
        return cmd_login(args.cdp_url, browser=args.browser)
    if c == "status":
        return cmd_status(args.cdp_url)

    sess = Session(args.cdp_url, browser=getattr(args, "browser", None))
    try:
        sess.ensure_login()
        if c == "agent":
            from .ops import agent
            return agent.route(sess, sub, args)
        if c == "conv":
            from .ops import conv
            return conv.route(sess, sub, args)
        if c == "knowledge":
            from .ops import knowledge
            return knowledge.route(sess, sub, args)
        if c == "mcp":
            from .ops import mcps
            return mcps.route(sess, sub, args)
        if c == "workflow":
            from .ops import workflow
            return workflow.route(sess, sub, args)
        if c == "node":
            from .ops import wfnode
            return wfnode.route(sess, sub, args)
        if c == "scaffold":
            from .recipes import scaffold
            return scaffold.run(sess, args)
        if c == "mcp-server":
            from .mcp_server import run_stdio
            return run_stdio(args.cdp_url)
        raise OpError("USAGE", f"未知命令 {c}")
    finally:
        sess.close()


def main(argv=None):
    args = _parser().parse_args(argv)
    if not args.cmd:
        _parser().print_help()
        sys.exit(2)
    try:
        res = dispatch(args)
    except OpError as e:
        res = err_result(e)
        if getattr(args, "debug_dom", None):
            try:
                s = Session(args.cdp_url, browser=getattr(args, "browser", None))
                open(args.debug_dom, "w", encoding="utf-8").write(s.b.text(20000))
                s.close()
            except Exception:
                pass
    except Exception as e:
        res = {"ok": False, "code": "INTERNAL", "message": f"{type(e).__name__}: {e}",
               "data": {}, "hint": "加 --debug-dom out.txt 抓页面状态复现"}
        traceback.print_exc(file=sys.stderr)
    emit(res, pretty=(args.format == "pretty"))
