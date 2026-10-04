"""场景层：一条命令装配草稿智能体（create→persona→welcome→knowledge→mcp）。"""
from ..envelope import ok
from ..ops import agent as ag
from ..ops import knowledge, mcps


def run(sess, args):
    name = args.name
    steps = []

    # 幂等：已存在则跳过创建
    names = [a["name"] for a in ag.list_agents(sess)["data"]["agents"]]
    if name in names:
        steps.append({"step": "create", "skipped": "already-exists"})
    else:
        ag.create_agent(sess, name, desc=args.desc)
        steps.append({"step": "create", "ok": True})

    if args.persona_file:
        ag.persona_set(sess, name, file=args.persona_file)
        steps.append({"step": "persona", "ok": True})

    if args.knowledge:
        knowledge.attach(sess, name, args.knowledge)
        steps.append({"step": "knowledge", "ok": args.knowledge})

    for m in [x.strip() for x in (args.mcp or "").split(",") if x.strip()]:
        mcps.attach(sess, name, m)
        steps.append({"step": "mcp", "ok": m})

    ag.save_agent(sess, name)
    steps.append({"step": "save", "ok": True})
    return ok({"agent": name, "steps": steps})
