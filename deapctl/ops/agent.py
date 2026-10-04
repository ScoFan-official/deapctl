"""智能体级操作：list/get/create/delete/persona/save。"""
import json

from ..envelope import OpError, ok

LIST_HASH = "#/agent/agent_management"
EDIT_HASH = "#/agent/agent_management_create_agent?agentUuid="


def goto_list(sess):
    if "agent_management" not in sess.page.url or "create_agent" in sess.page.url:
        sess.page.goto("https://deap.dingtalk.com/" + LIST_HASH, wait_until="domcontentloaded")
    sess.b.wait(2000)
    if not sess.b.has_text("新建智能体"):
        sess.b.wait_text("新建智能体", 10000)


def _rows_js():
    return """(()=>{const trs=[...document.querySelectorAll('tr')].filter(e=>__deap.vis(e));
      return trs.map(tr=>{const tds=[...tr.querySelectorAll('td')].map(td=>(td.innerText||'').trim());
        return tds.length>=5?tds:null}).filter(Boolean)})()"""


def list_agents(sess):
    goto_list(sess)
    rows = sess.b.ev(_rows_js())
    out = []
    for tds in rows:
        if len(tds) < 5 or "智能体" in tds[0]:
            continue
        parts = tds[0].split("\n", 1)
        out.append({"name": parts[0].strip(), "desc": parts[1].strip() if len(parts) > 1 else "",
                    "dept": tds[1] if len(tds) > 1 else "",
                    "owner": tds[2] if len(tds) > 2 else "",
                    "status": tds[3] if len(tds) > 3 else "",
                    "uuid": tds[5] if len(tds) > 5 else ""})
    return ok({"agents": out, "count": len(out)})


def _find(sess, name):
    goto_list(sess)
    rows = sess.b.ev(_rows_js())
    for tds in rows:
        if len(tds) >= 6 and tds[0].split("\n")[0].strip() == name:
            return tds[5].strip()
    raise OpError("NOT_FOUND", f"智能体 '{name}' 不存在",
                  "deapctl agent list 查看现有智能体")


def open_editor(sess, name):
    """导航到指定智能体编辑器。name 可为名称或 uuid。"""
    uuid = name if "-" in name and len(name) > 30 else _find(sess, name)
    sess.page.goto("https://deap.dingtalk.com/" + EDIT_HASH + uuid,
                   wait_until="domcontentloaded")
    sess.b.wait(3500)
    if not (sess.b.has_text("人设") and sess.b.has_text("工作流")):
        sess.b.wait_text("人设", 15000)
    return uuid


def get_agent(sess, name):
    uuid = open_editor(sess, name)
    t = sess.b.text(3000)
    first = t.split("\n")[0] if t else ""
    return ok({"name": name, "uuid": uuid, "editor_title": first, "url": sess.page.url})


def _save_button(sess):
    r = sess.b.click_text("保存")
    if not r:
        raise OpError("SELECTOR_MISS", "找不到「保存」按钮")
    sess.b.wait(2500)
    return sess.b.has_text("保存成功") or sess.b.has_text("已保存")


_PERSONA_TA = """[...document.querySelectorAll('textarea')].filter(e=>__deap.vis(e))
      .sort((a,b)=>b.getBoundingClientRect().height-a.getBoundingClientRect().height)[0]"""


def persona_get(sess, name):
    open_editor(sess, name)
    _click_tab(sess, "人设")
    v = sess.b.ev(f"(()=>{{const ta={_PERSONA_TA}; return ta?ta.value:null}})()")
    return ok({"name": name, "persona": v})


def persona_set(sess, name, text=None, file=None, append=False):
    if file:
        text = open(file, encoding="utf-8").read()
    if not text:
        raise OpError("USAGE", "persona set 需要 --text 或 --file")
    open_editor(sess, name)
    _click_tab(sess, "人设")
    cur = sess.b.ev(f"(()=>{{const ta={_PERSONA_TA}; return ta?ta.value:null}})()")
    if cur is None:
        raise OpError("SELECTOR_MISS", "找不到人设文本框")
    new = (cur.rstrip() + "\n" + text) if append else text
    r = sess.b.ev(f"""(()=>{{const ta={_PERSONA_TA};
      __deap.fillIn(ta,{json.dumps(new)}); return ta.value.length}})()""")
    saved = _save_button(sess)
    return ok({"name": name, "persona_len": len(text), "saved": saved},
              "人设已更新" if saved else "已写入但未确认保存提示")


def _click_tab(sess, name):
    if not sess.b.click_text(name):
        raise OpError("SELECTOR_MISS", f"找不到页签「{name}」")
    sess.b.wait(1500)


def save_agent(sess, name):
    open_editor(sess, name)
    saved = _save_button(sess)
    return ok({"name": name, "saved": saved})


def create_agent(sess, name, desc="", dept=None):
    goto_list(sess)
    rows = sess.b.ev(_rows_js())
    for tds in rows:
        if tds and tds[0].split("\n")[0].strip() == name:
            return ok({"name": name, "uuid": tds[5].strip(), "existed": True},
                      "已存在同名智能体（幂等返回）")
    r = sess.b.ev("""(()=>{const btn=[...document.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='新建智能体');
      if(!btn) return null; __deap.clickEl(btn); return true})()""")
    if not r:
        raise OpError("SELECTOR_MISS", "找不到「新建智能体」按钮")
    sess.b.wait(2000)
    modal = "[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop()"
    r = sess.b.ev(f"""(()=>{{const m={modal}; if(!m) return 'no-modal';
      const nm=[...m.querySelectorAll('input')].find(e=>(e.placeholder||'').includes('名字'));
      const ds=[...m.querySelectorAll('textarea')].find(e=>__deap.vis(e));
      const dp=[...m.querySelectorAll('input')].find(e=>{{let n=e.parentElement;while(n&&n!==m){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim()==='归属部门');if(sib)return true;n=n.parentElement}}return false}});
      if(!nm) return 'no-name';
      __deap.fillIn(nm,{json.dumps(name)});
      if(ds) __deap.fillIn(ds,{json.dumps(desc)});
      return dp?'dept-field':'no-dept'}})()""")
    if r == "no-modal":
        raise OpError("SELECTOR_MISS", "新建弹窗未出现")
    if r == "no-name":
        raise OpError("SELECTOR_MISS", "弹窗内找不到名称输入框")
    if dept and r == "dept-field":
        _pick_dept(sess, modal, dept)
    sess.b.wait(600)
    c = sess.b.ev(f"""(()=>{{const m={modal}; const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='确定');
      if(!btn) return null; __deap.clickEl(btn); return true}})()""")
    if not c:
        raise OpError("SELECTOR_MISS", "确定按钮未找到")
    sess.b.wait(4500)
    goto_list(sess)
    uuid = None
    try:
        uuid = _find(sess, name)
    except OpError:
        pass
    if not uuid:
        raise OpError("CREATE_FAILED", "提交后列表未见新智能体", "检查控制台弹窗报错")
    return ok({"name": name, "uuid": uuid, "existed": False}, "草稿智能体已创建")


def _pick_dept(sess, modal, dept):
    """归属部门选择器：点击输入框 → 弹层里点匹配项。"""
    import json as _j
    sess.b.ev(f"""(()=>{{const m={modal};
      const dp=[...m.querySelectorAll('input')].find(e=>{{let n=e.parentElement;while(n&&n!==m){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim()==='归属部门');if(sib)return true;n=n.parentElement}}return false}});
      if(dp){{const h=dp.closest('div')||dp; __deap.clickEl(dp)}}}})()""")
    sess.b.wait(1200)
    sess.b.ev(f"""(()=>{{const layer=__deap.layers().pop(); const scope=layer||document;
      const hit=[...scope.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={_j.dumps(dept)}&&e.children.length<4);
      if(hit[0]) __deap.clickEl(hit[0])}})()""")
    sess.b.wait(800)


def delete_agent(sess, name, yes=False):
    if not yes:
        raise OpError("USAGE", f"删除 '{name}' 需 --yes 确认", "该操作不可恢复")
    goto_list(sess)
    uuid = _find(sess, name)
    # 行内「删除」操作
    r = sess.b.ev(f"""(()=>{{const trs=[...document.querySelectorAll('tr')].filter(e=>__deap.vis(e));
      const tr=trs.find(t=>(t.innerText||'').includes({json.dumps(name)}));
      if(!tr) return 'no-row';
      tr.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      const links=[...tr.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==='删除');
      if(!links.length) return 'no-del';
      __deap.clickEl(links[links.length-1]); return 'clicked'}})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"行内删除入口未找到 ({r})")
    sess.b.wait(1500)
    c = sess.b.confirm_modal()
    if c is None:
        raise OpError("SELECTOR_MISS", "删除确认弹窗/肯定按钮未命中")
    sess.b.wait(2500)
    rows = sess.b.ev(_rows_js())
    gone = not any(tds and tds[0].split("\n")[0].strip() == name for tds in rows)
    return ok({"name": name, "uuid": uuid, "deleted": gone},
              "已删除" if gone else "删除请求已提交但行仍在")


def route(sess, sub, args):
    if sub == "list":
        return list_agents(sess)
    if sub == "get":
        return get_agent(sess, args.name)
    if sub == "create":
        return create_agent(sess, args.name, args.desc, getattr(args, "dept", None))
    if sub == "delete":
        return delete_agent(sess, args.name, args.yes)
    if sub == "persona":
        if args.sub2 == "get":
            return persona_get(sess, args.name)
        if args.sub2 == "set":
            return persona_set(sess, args.name, text=args.text, file=args.file, append=args.append)
    if sub == "save":
        return save_agent(sess, args.name)
    raise OpError("USAGE", f"未知 agent 子命令 {sub}")
