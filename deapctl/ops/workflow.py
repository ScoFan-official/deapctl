"""工作流卡片级操作：list/create/meta/delete/copy/enable + 编辑器打开。

编辑器内节点操作在 wfnode.py；画布保存/检查/调试在 wfrun.py。
"""
import json

from ..envelope import OpError, ok
from .agent import open_editor

_ITEM = ".edit-skills-content-body-item"
_NAME = ".edit-skill-content-body-left-info-name"


def goto_wf_tab(sess, name):
    open_editor(sess, name)
    if not sess.b.click_text("工作流"):
        raise OpError("SELECTOR_MISS", "找不到「工作流」页签")
    sess.b.wait(1800)


def _cards(sess):
    return sess.b.ev(f"""(()=>{{const items=[...document.querySelectorAll('{_ITEM}')].filter(e=>__deap.vis(e));
      return items.map(it=>{{const name=(it.querySelector('{_NAME}')||{{}}).innerText||'';
        const sw=it.querySelector('.dtd-switch,[role=switch]');
        const enabled=sw?(sw.getAttribute('aria-checked')==='true'||sw.className.includes('checked')||(sw.className.includes('dtd-switch')&&sw.className.includes('true'))||sw.className.includes('-checked')):null;
        const desc=((it.innerText||'').split('\\n').map(x=>x.trim()).filter(Boolean));
        const d=desc.find(l=>l!==name&&l!=='工作流'&&l.length>5)||'';
        return {{name:name.trim(),desc:d,enabled}}}})}})()""")


def list_cards(sess, name):
    goto_wf_tab(sess, name)
    return ok({"agent": name, "workflows": _cards(sess)})


def _card_btn(sess, wf_name, idx):
    """点卡片上第 idx 个图标按钮：0=编辑 1=复制 2=删除。"""
    r = sess.b.ev(f"""(()=>{{const it=[...document.querySelectorAll('{_ITEM}')].filter(e=>__deap.vis(e))
      .find(e=>((e.querySelector('{_NAME}')||{{}}).innerText||'').trim()==={json.dumps(wf_name)});
      if(!it) return 'nf';
      it.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      const btns=[...it.querySelectorAll('button')].filter(e=>__deap.vis(e));
      const b=btns[{idx}]; if(!b) return 'no-btn';
      __deap.clickEl(b); return 'clicked'}})()""")
    return r


def _fill_form(sess, name, desc, examples):
    """新建/编辑工作流弹窗：名称 input + 描述 textarea + 示例问题 inputs。"""
    modal = "[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop()"
    r = sess.b.ev(f"""(()=>{{const m={modal}; if(!m) return 'no-modal';
      const nm=[...m.querySelectorAll('input')].find(e=>(e.placeholder||'').includes('工作流的名称'));
      const ds=[...m.querySelectorAll('textarea')].find(e=>__deap.vis(e));
      if(!nm) return 'no-name';
      if({json.dumps(name)}) __deap.fillIn(nm,{json.dumps(name)});
      if(ds&&{json.dumps(desc)}!==null) __deap.fillIn(ds,{json.dumps(desc or '')});
      return 'filled'}})()""")
    if r != "filled":
        raise OpError("SELECTOR_MISS", f"工作流表单填写失败 {r}")
    sess.b.wait(500)
    if examples:
        ex_js = json.dumps(list(examples))
        sess.b.ev(f"""(()=>{{const m={modal};
          const exs=[...m.querySelectorAll('input')].filter(e=>__deap.vis(e)&&(e.placeholder||'').includes('示例'));
          const vals={ex_js};
          exs.forEach((e,i)=>{{if(vals[i])__deap.fillIn(e,vals[i])}}); return exs.length}})()""")
        sess.b.wait(300)


def create(sess, agent, wf_name, desc="", examples=None, open_editor_after=False):
    goto_wf_tab(sess, agent)
    cur = [c["name"] for c in _cards(sess)]
    if wf_name in cur:
        res = ok({"agent": agent, "workflow": wf_name, "existed": True}, "已存在（幂等）")
        res["code"] = "ALREADY"
        return res
    r = sess.b.ev("""(()=>{const btn=[...document.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='添加工作流');
      if(!btn) return null; __deap.clickEl(btn); return true})()""")
    if not r:
        raise OpError("SELECTOR_MISS", "找不到「添加工作流」")
    sess.b.wait(1500)
    r = sess.b.ev("""(()=>{const m=[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop();
      const t=[...m.querySelectorAll('div')].find(e=>e.children.length===0&&(e.innerText||'').trim()==='新建工作流');
      if(!t) return 'nf'; __deap.clickEl(t.parentElement); return 'clicked'})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"「新建工作流」项未找到 {r}")
    sess.b.wait(1500)
    _fill_form(sess, wf_name, desc, examples)
    c = sess.b.ev("""(()=>{const m=[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop();
      const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='确定');
      if(!btn) return null; __deap.clickEl(btn); return true})()""")
    if not c:
        raise OpError("SELECTOR_MISS", "确定按钮未找到")
    sess.b.wait(3500)
    # 创建后通常直接进入编辑器
    in_editor = bool(sess.b.ev("""(()=>{const t=document.body.innerText;return t.includes('检查清单')||t.includes('节点1')||t.includes('调试')})()"""))
    if not in_editor:
        goto_wf_tab(sess, agent)
        names = [c["name"] for c in _cards(sess)]
        if wf_name not in names:
            raise OpError("CREATE_FAILED", "提交后列表未出现新工作流")
    return ok({"agent": agent, "workflow": wf_name, "existed": False,
               "in_editor": in_editor}, "工作流已创建")


def meta(sess, agent, wf_name, desc=None, examples=None, new_name=None):
    goto_wf_tab(sess, agent)
    r = _card_btn(sess, wf_name, 0)
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"卡片「编辑」按钮未找到 {r}")
    sess.b.wait(1800)
    _fill_form(sess, new_name, desc, examples)
    c = sess.b.ev("""(()=>{const m=[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop();
      const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='确定');
      if(!btn) return null; __deap.clickEl(btn); return true})()""")
    if not c:
        raise OpError("SELECTOR_MISS", "确定按钮未找到")
    sess.b.wait(2500)
    names = [c["name"] for c in _cards(sess)]
    final = new_name or wf_name
    return ok({"agent": agent, "workflow": final, "exists": final in names})


def enable(sess, agent, wf_name, on=True):
    goto_wf_tab(sess, agent)
    cards = _cards(sess)
    card = next((c for c in cards if c["name"] == wf_name), None)
    if not card:
        raise OpError("NOT_FOUND", f"工作流 '{wf_name}' 不存在")
    if card["enabled"] == on:
        res = ok({"agent": agent, "workflow": wf_name, "enabled": on}, "已是目标状态（幂等）")
        res["code"] = "ALREADY"
        return res
    r = sess.b.ev(f"""(()=>{{const it=[...document.querySelectorAll('{_ITEM}')].filter(e=>__deap.vis(e))
      .find(e=>((e.querySelector('{_NAME}')||{{}}).innerText||'').trim()==={json.dumps(wf_name)});
      const sw=it.querySelector('.dtd-switch,[role=switch]'); if(!sw) return 'no-sw';
      __deap.clickEl(sw); return 'clicked'}})()""")
    sess.b.wait(1200)
    # 可能有确认弹窗
    sess.b.ev("""(()=>{const m=[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop();
      if(m){const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&['确定','确认','启用','停用'].includes((e.innerText||'').trim()));if(btn)__deap.clickEl(btn)}})()""")
    sess.b.wait(1500)
    after = _cards(sess)
    c2 = next((c for c in after if c["name"] == wf_name), None)
    return ok({"agent": agent, "workflow": wf_name,
               "enabled": c2["enabled"] if c2 else None},
              "开关已切换" if (c2 and c2["enabled"] == on) else "状态未按预期变更")


def copy(sess, agent, wf_name, new_name=None):
    goto_wf_tab(sess, agent)
    r = _card_btn(sess, wf_name, 1)
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"卡片「复制」按钮未找到 {r}")
    sess.b.wait(1500)
    # 若弹命名框则填 new_name
    modal = "[...document.querySelectorAll('.dtd-modal')].filter(e=>__deap.vis(e)).pop()"
    m = sess.b.ev(f"(()=>{{const m={modal}; return m?(m.innerText||'').slice(0,50):null}})()")
    if m:
        if new_name:
            sess.b.ev(f"""(()=>{{const m={modal};const i=[...m.querySelectorAll('input')].find(e=>__deap.vis(e));if(i)__deap.fillIn(i,{json.dumps(new_name)})}})()""")
        sess.b.ev(f"""(()=>{{const m={modal};const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&['确定','复制','创建'].includes((e.innerText||'').trim()));if(btn)__deap.clickEl(btn);return true}})()""")
        sess.b.wait(2500)
    goto_wf_tab(sess, agent)
    names = [c["name"] for c in _cards(sess)]
    target = new_name or f"{wf_name}"
    dup = len(names) != len(set(names)) or (new_name and new_name in names)
    return ok({"agent": agent, "copied_from": wf_name, "workflows": names},
              "复制完成" if (new_name in names if new_name else len(names) > 0) else "请人工核对")


def delete(sess, agent, wf_name, yes=False):
    if not yes:
        raise OpError("USAGE", f"删除工作流 '{wf_name}' 需 --yes")
    goto_wf_tab(sess, agent)
    cards = _cards(sess)
    if not any(c["name"] == wf_name for c in cards):
        raise OpError("NOT_FOUND", f"工作流 '{wf_name}' 不存在")
    r = _card_btn(sess, wf_name, 2)
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"卡片「删除」按钮未找到 {r}")
    sess.b.wait(1200)
    sess.b.confirm_modal()
    sess.b.wait(2000)
    names = [c["name"] for c in _cards(sess)]
    return ok({"agent": agent, "workflow": wf_name, "deleted": wf_name not in names})


def open_wf_editor(sess, agent, wf_name):
    """卡片 btns[0]（编辑工作流图标）→ 画布编辑器。"""
    goto_wf_tab(sess, agent)
    r = _card_btn(sess, wf_name, 0)
    if r != "clicked":
        raise OpError("NOT_FOUND", f"工作流 '{wf_name}' 不存在 ({r})")
    sess.b.wait(3500)
    in_editor = bool(sess.b.ev("""(()=>{const t=document.body.innerText;
      return t.includes('检查清单')&&(t.includes('保存')||t.includes('调试'))})()"""))
    if not in_editor:
        raise OpError("SELECTOR_MISS", "未进入编辑器", "--debug-dom 查看当前页")
    return True


def route(sess, sub, args):
    if sub == "list":
        return list_cards(sess, args.agent)
    if sub == "create":
        ex = getattr(args, "example", None) or getattr(args, "examples", None)
        if isinstance(ex, str):
            ex = [x for x in ex.split("|") if x.strip()]
        return create(sess, args.agent, args.name, args.desc, ex)
    if sub == "meta":
        return meta(sess, args.agent, args.name, getattr(args, "desc", None),
                    getattr(args, "examples", None), getattr(args, "new_name", None))
    if sub == "enable":
        return enable(sess, args.agent, args.name, True)
    if sub == "disable":
        return enable(sess, args.agent, args.name, False)
    if sub == "copy":
        return copy(sess, args.agent, args.name, getattr(args, "new_name", None))
    if sub == "delete":
        return delete(sess, args.agent, args.name, getattr(args, "yes", False))
    if sub in ("save", "check", "debug", "runs"):
        from . import wfrun
        return wfrun.route(sess, sub, args)
    if sub == "apply":
        from ..recipes import wf_apply
        return wf_apply.run(sess, args)
    raise OpError("USAGE", f"未知 workflow 子命令 {sub}")
