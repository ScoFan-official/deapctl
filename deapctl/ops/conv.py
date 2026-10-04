"""对话配置：欢迎语、引导问题、输入框提示语、快捷按钮 CRUD。"""
import json

from ..envelope import OpError, ok
from .agent import open_editor


def _goto_conv(sess, name):
    open_editor(sess, name)
    if not sess.b.click_text("对话配置"):
        raise OpError("SELECTOR_MISS", "找不到「对话配置」页签")
    sess.b.wait(1800)


def _fields(sess):
    """返回对话配置页关键输入控件的定位表达式字典。"""
    return {
        "welcome": "__deap.deepVisible('textarea').find(e=>(e.placeholder||'').includes('开场'))",
        "tips": "__deap.deepVisible('textarea').find(e=>(e.placeholder||'').includes('把问题'))",
        "guides": "__deap.deepVisible('input').filter(e=>(e.placeholder||'').includes('引导问题'))",
    }


def conv_get(sess, name):
    _goto_conv(sess, name)
    f = _fields(sess)
    data = sess.b.ev(f"""(()=>{{
      const w={f['welcome']}; const tp={f['tips']}; const gs={f['guides']};
      const btns=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e))
        .map(e=>((e.innerText||'').trim().split('\\n')[0]));
      return {{welcome:w?w.value:'',tips:tp?tp.value:'',guides:gs.map(g=>g.value||''),quick_btns:btns}}
    }})()""")
    return ok({"agent": name, **data})


def welcome_set(sess, name, text):
    _goto_conv(sess, name)
    f = _fields(sess)
    r = sess.b.ev(f"(()=>{{const e={f['welcome']}; if(!e) return null; __deap.fillIn(e,{json.dumps(text)}); return e.value.length}})()")
    if r is None:
        raise OpError("SELECTOR_MISS", "找不到欢迎语输入框")
    return _finish_save(sess, name, "welcome")


def tips_set(sess, name, text):
    _goto_conv(sess, name)
    f = _fields(sess)
    r = sess.b.ev(f"(()=>{{const e={f['tips']}; if(!e) return null; __deap.fillIn(e,{json.dumps(text)}); return e.value.length}})()")
    if r is None:
        raise OpError("SELECTOR_MISS", "找不到输入框提示语")
    return _finish_save(sess, name, "tips")


def guides_set(sess, name, questions):
    """questions: list[str]，最多3条。"""
    _goto_conv(sess, name)
    f = _fields(sess)
    for i, q in enumerate(list(questions[:3]) + [""] * 3):
        sess.b.ev(f"(()=>{{const gs={f['guides']}; if(gs[{i}]) __deap.fillIn(gs[{i}],{json.dumps(q)})}})()")
    return _finish_save(sess, name, "guides")


def _finish_save(sess, name, what):
    if not sess.b.click_text("保存"):
        raise OpError("SELECTOR_MISS", "找不到「保存」按钮")
    sess.b.wait(2500)
    saved = sess.b.has_text("保存成功") or sess.b.has_text("已保存")
    return ok({"agent": name, "saved": saved}, f"{what} 已更新" if saved else "未确认保存提示")


def qbtn_list(sess, name):
    _goto_conv(sess, name)
    items = sess.b.ev("""(()=>{const a=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e));
      return a.map(e=>(e.innerText||'').trim().split('\\n'))})()""")
    return ok({"agent": name, "quick_btns": [{"name": x[0], "kind": x[1] if len(x) > 1 else ""} for x in items],
               "count": len(items)})


def _open_add_form(sess):
    r = sess.b.ev("""(()=>{const e=[...document.querySelectorAll('div')].find(x=>__deap.vis(x)&&(x.innerText||'').trim().startsWith('添加（')&&(x.className||'').includes('cursor-pointer'));
      if(!e) return null; __deap.clickEl(e); return true})()""")
    if not r:
        raise OpError("SELECTOR_MISS", "找不到快捷按钮「添加」入口")
    sess.b.wait(1500)
    if not sess.b.has_text("添加快捷按钮"):
        raise OpError("SELECTOR_MISS", "添加表单未出现")


def _modal(sess):
    return "[...document.querySelectorAll('div')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes('快捷按钮')&&(e.innerText||'').includes('确定')).sort((a,b)=>a.contains(b)?-1:1)[0]"


def _fill_modal(sess, name, text):
    """填名称 + 类型=预设输入 + 预设文本。"""
    m = _modal(sess)
    # 名称 = 第一个 text input (placeholder 请输入, 0/30)
    r = sess.b.ev(f"""(()=>{{const m={m}; if(!m) return 'no-modal';
      const name=[...m.querySelectorAll('input[type=text]')].find(e=>(e.placeholder||'').includes('请输入'));
      if(!name) return 'no-name'; __deap.fillIn(name,{json.dumps(name)}); return 'ok'}})()""")
    if r != "ok":
        raise OpError("SELECTOR_MISS", f"表单名称框异常 {r}")
    # 类型 → 预设输入 (radio value=FillInput 或其文本)
    sess.b.ev(f"""(()=>{{const m={m}; const r=[...m.querySelectorAll('input[type=radio]')].find(e=>e.value==='FillInput');
      if(r){{const lab=r.closest('label')||r.parentElement; __deap.clickEl(lab); return 'radio'}}
      const t=[...m.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='预设输入'&&e.children.length<3);
      if(t) __deap.clickEl(t); return 'text'}})()""")
    sess.b.wait(800)
    # 预设输入内容是 Slate contenteditable：真实点击聚焦 + keyboard.type
    r = sess.b.ev(f"""(()=>{{const m={m};
      const ed=[...m.querySelectorAll('[data-slate-editor=true],[contenteditable=true]')].find(e=>__deap.vis(e));
      if(!ed) return 'no-editor';
      const b=ed.getBoundingClientRect(); return [b.x+b.width/2,b.y+b.height/2]}})()""")
    if not isinstance(r, list):
        raise OpError("SELECTOR_MISS", f"预设输入编辑器未找到 {r}")
    sess.b.click_xy(r[0], r[1])
    sess.b.wait(300)
    sess.b.type(text)
    sess.b.wait(400)
    c = sess.b.ev(f"""(()=>{{const m={m}; const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='确定');
      if(!btn) return null; __deap.clickEl(btn); return true}})()""")
    if not c:
        raise OpError("SELECTOR_MISS", "确定按钮未找到")
    sess.b.wait(1500)


def qbtn_add(sess, name, btn_name, text):
    _goto_conv(sess, name)
    _open_add_form(sess)
    _fill_modal(sess, btn_name, text)
    items = sess.b.ev("""(()=>{const a=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e));
      return a.map(e=>(e.innerText||'').trim().split('\\n')[0])})()""")
    if btn_name not in items:
        raise OpError("CREATE_FAILED", "确定后列表未见新按钮", data={"buttons": items})
    return _finish_save(sess, name, f"quick-btn {btn_name}")


def qbtn_delete(sess, name, btn_name, yes=False):
    if not yes:
        raise OpError("USAGE", f"删除快捷按钮 '{btn_name}' 需 --yes")
    _goto_conv(sess, name)
    r = sess.b.ev(f"""(()=>{{const items=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e));
      const it=items.find(e=>((e.innerText||'').trim().split('\\n')[0])==={json.dumps(btn_name)});
      if(!it) return 'nf';
      it.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      const del=[...it.querySelectorAll('.shortcut-actions *')].filter(e=>String(e.className||'').includes('red'));
      if(!del.length) return 'no-del';
      __deap.clickEl(del[del.length-1].tagName==='svg'?del[del.length-1].closest('span,button,div')||del[del.length-1]:del[del.length-1]);
      return 'clicked'}})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"删除图标未找到 ({r})")
    sess.b.wait(1200)
    # 可能的确认弹窗
    sess.b.confirm_modal()
    sess.b.wait(1200)
    items = sess.b.ev("""(()=>{const a=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e));
      return a.map(e=>(e.innerText||'').trim().split('\\n')[0])})()""")
    gone = btn_name not in items
    return _finish_save(sess, name, f"quick-btn {btn_name} 删除") if gone else \
        ok({"agent": name, "deleted": False}, "删除未生效", hint="可能需手动处理确认弹窗")


def qbtn_update(sess, name, btn_name, new_name=None, text=None):
    _goto_conv(sess, name)
    r = sess.b.ev(f"""(()=>{{const items=[...document.querySelectorAll('.shortcut-item')].filter(e=>__deap.vis(e));
      const it=items.find(e=>((e.innerText||'').trim().split('\\n')[0])==={json.dumps(btn_name)});
      if(!it) return 'nf';
      it.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      const ed=[...it.querySelectorAll('.shortcut-actions *')].filter(e=>String(e.className||'').includes('blue'));
      if(!ed.length) return 'no-edit';
      const el=ed[ed.length-1].closest('span,button,div')||ed[ed.length-1];
      __deap.clickEl(el); return 'clicked'}})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"编辑图标未找到 ({r})")
    sess.b.wait(1500)
    _fill_modal(sess, new_name or btn_name, text or "")
    return _finish_save(sess, name, f"quick-btn {btn_name} 更新")


def route(sess, sub, args):
    if sub == "welcome":
        if args.sub2 == "get":
            return conv_get(sess, args.agent)
        return welcome_set(sess, args.agent, args.text)
    if sub == "tips":
        return tips_set(sess, args.agent, args.text)
    if sub == "guides":
        return guides_set(sess, args.agent, [x.strip() for x in args.qs.split("|") if x.strip()])
    if sub == "quick-btn":
        if args.sub2 == "list":
            return qbtn_list(sess, args.agent)
        if args.sub2 == "add":
            return qbtn_add(sess, args.agent, args.name, args.text)
        if args.sub2 == "update":
            return qbtn_update(sess, args.agent, args.name, args.new_name, args.text)
        if args.sub2 == "delete":
            return qbtn_delete(sess, args.agent, args.name, args.yes)
    raise OpError("USAGE", f"未知 conv 子命令 {sub}")
