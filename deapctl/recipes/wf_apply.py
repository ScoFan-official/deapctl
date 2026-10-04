"""workflow apply：声明式 spec → 整条工作流。

spec.json 结构：
{
  "meta": {"desc": "...", "examples": ["..."]},
  "params": [{"name":"听记原文","desc":"...","required":true,"type":"文本"}],
  "nodes": [
    {"type":"llm","model":"通义千问3.0-max",
     "question_vars":["听记原文"],"prompt":"...",
     "json_mode":"{\\"任务清单\\":[{\\"任务标题\\":\\"x\\"}]}",
     "outputs":[{"name":"任务清单","desc":"","type":"对象数组"}]},
    {"type":"loop","array":"任务清单","children":[
      {"type":"record","base":"实验室秘书试点","table":"任务分工",
       "fields":{"目标":"任务标题"},"fixed":{"状态":"待认领","优先级":"中"}},
      {"type":"llm","model":"...","question_vars":["本次循环数据"],"prompt":"...","outputs":[...]}
    ]},
    {"type":"end","pairs":[{"name":"写入清单","var":"任务清单"}]}
  ]
}

循环 children 注意：编辑器内加节点总是落在循环体顶部，因此 spec 里
children 按「视觉从上到下」书写，apply 内部倒序插入。
"""
import json

from ..envelope import OpError, ok
from ..ops import workflow as wf
from ..ops.wfnode import WfEditor


def run(sess, args):
    spec = json.load(open(args.file, encoding="utf-8"))
    agent, name = args.agent, args.name

    existing = [c["name"] for c in wf.list_cards(sess, agent).get("data", {}).get("workflows", [])]
    if name in existing:
        if not args.force:
            raise OpError("EXISTS", f"工作流 '{name}' 已存在", "加 --force 覆盖（删除后重建）")
        wf.delete(sess, agent, name, yes=True)

    wf.create(sess, agent, name,
              desc=spec.get("meta", {}).get("desc", ""),
              examples=spec.get("meta", {}).get("examples"))
    ed = WfEditor(sess, agent, name)
    # create 已在编辑器内；确保
    try:
        ed.nodes()
    except Exception:
        ed = WfEditor(sess, agent, name)

    log = []
    for p in spec.get("params", []):
        ed.param_add(p["name"], p.get("desc", ""),
                     p.get("required", True), p.get("type", "文本"))
        log.append({"param": p["name"], "ok": True})

    for i, n in enumerate(spec.get("nodes", [])):
        _apply_node(ed, n, after=-1, log=log)

    ed.save()
    chk = ed_check(sess, agent, name)
    return ok({"agent": agent, "workflow": name, "applied": log,
               "check": chk.get("data", {})})


def _apply_node(ed, spec, after, log):
    """插入并按类型配置一个节点。循环节点递归处理 children（倒序）。"""
    t = spec.get("type")
    type_map = {"llm": "向大模型提问", "loop": "循环", "record": "新增记录",
                "condition": "条件分支", "end": None}
    if t == "end":
        ed.config_end(spec.get("pairs", []))
        log.append({"node": "end", "ok": True})
        return
    label = type_map.get(t, t)
    ed.insert_node(after, label)
    log.append({"node": label, "inserted": True})
    # 新节点序号 = 插入点+1（简化：取 nodes() 里新出现的）
    nodes = ed.nodes()
    node_no = _find_new_node(nodes, label)
    if t == "llm":
        ed.config_llm(node_no, model=spec.get("model"),
                      question_vars=spec.get("question_vars"),
                      prompt=spec.get("prompt"),
                      outputs=spec.get("outputs"),
                      json_mode=spec.get("json_mode"))
    elif t == "loop":
        ed.bind_loop(node_no, spec["array"])
        # children 倒序插入（编辑器内 add 落顶部）
        for child in reversed(spec.get("children", [])):
            _apply_loop_child(ed, node_no, child, log)
    elif t == "record":
        ed.config_record(node_no, base=spec.get("base"), table=spec.get("table"),
                         fields=spec.get("fields"), fixed=spec.get("fixed"))


def _apply_loop_child(ed, loop_no, spec, log):
    """往循环体里插一个子节点：点循环内部的 '+'。"""
    t = spec.get("type")
    label = {"llm": "向大模型提问", "record": "新增记录"}.get(t, t)
    ed.insert_into_loop(loop_no, label)
    nodes = ed.nodes()
    node_no = _find_new_node(nodes, label)
    if t == "llm":
        ed.config_llm(node_no, model=spec.get("model"),
                      question_vars=spec.get("question_vars"),
                      prompt=spec.get("prompt"), outputs=spec.get("outputs"))
    elif t == "record":
        ed.config_record(node_no, base=spec.get("base"), table=spec.get("table"),
                         fields=spec.get("fields"), fixed=spec.get("fixed"))
    log.append({"loop_child": label, "ok": True})


def _find_new_node(nodes, label):
    """nodes() 返回 [{text:'2./向大模型提问/...',x,y,...}]，取最后一个匹配。"""
    cands = [n for n in nodes if label.split("/")[0] in (n.get("text") or "")]
    if not cands:
        raise OpError("SELECTOR_MISS", f"新插入的 '{label}' 节点未找到")
    return cands[-1]["text"].split(".")[0] + "."


def ed_check(sess, agent, name):
    from ..ops import wfrun
    class A:  # 轻量 args 壳
        pass
    a = A(); a.agent = agent; a.name = name; a.params = None
    return wfrun.check(sess, agent, name)
