"""知识集挂载管理。"""
import json

from ..envelope import OpError, ok
from .agent import open_editor


def _goto_knowledge(sess, name):
    open_editor(sess, name)
    if not sess.b.click_text("知识"):
        raise OpError("SELECTOR_MISS", "找不到「知识」页签")
    sess.b.wait(1800)


def list_attached(sess, name):
    _goto_knowledge(sess, name)
    r = sess.b.ev("""(()=>{const all=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes('个文档')&&(e.innerText||'').length<150);
      const deep=all.filter(e=>!all.find(c=>c!==e&&e.contains(c)));
      const names=[];
      for(const e of deep){let n=e;for(let i=0;i<4&&n;i++){const ls=(n.innerText||'').trim().split('\\n').map(x=>x.trim());
        const nm=ls.find(l=>!/^[\\d,\\s]+个?文档/.test(l)&&!/^[\\d,\\s]+$/.test(l)&&!['添加知识集','设置','知识'].includes(l));
        if(nm){names.push(nm);break}n=n.parentElement}}
      return names.filter((v,i,a)=>a.indexOf(v)===i)})()""")
    return ok({"agent": name, "attached": r})


def attach(sess, name, kn_name):
    _goto_knowledge(sess, name)
    cur = list_attached(sess, name)["data"]["attached"]
    if any(kn_name in x for x in cur):
        return ok({"agent": name, "attached": cur}, f"'{kn_name}' 已挂载（幂等）", hint=None) | {"code": "ALREADY"}
    if not sess.b.click_text("添加知识集"):
        raise OpError("SELECTOR_MISS", "找不到「添加知识集」")
    sess.b.wait(2000)
    # picker 弹层：搜索/勾选目标行后确定
    sess.b.ev(f"""(()=>{{const m=__deap.layers()[0]; if(!m) return;
      const s=[...m.querySelectorAll('input')].find(e=>__deap.vis(e)&&(e.placeholder||'').includes('搜索'));
      if(s){{__deap.fillIn(s,{json.dumps(kn_name)})}} }})()""")
    sess.b.wait(1500)
    r = sess.b.ev(f"""(()=>{{const m=__deap.layers()[0]; if(!m) return 'no-modal';
      const rows=[...m.querySelectorAll('tr,[class*=item],[class*=row],li')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes({json.dumps(kn_name)}));
      if(!rows.length) return 'no-row';
      const row=rows[0];
      const cb=row.querySelector('input[type=checkbox],input[type=radio],.dtd-checkbox,[class*=checkbox]');
      __deap.clickEl(cb||row); return 'clicked'}})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"知识集 '{kn_name}' 未在弹层中找到 ({r})")
    sess.b.wait(800)
    c = sess.b.ev("""(()=>{const m=__deap.layers()[0];const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&['确定','添加','完成'].includes((e.innerText||'').trim()));if(!btn)return null;__deap.clickEl(btn);return true})()""")
    sess.b.wait(2000)
    after = list_attached(sess, name)["data"]["attached"]
    done = any(kn_name in x for x in after)
    return ok({"agent": name, "attached": after, "added": done},
              f"'{kn_name}' 挂载成功" if done else "已提交但列表未回显")


def detach(sess, name, kn_name, yes=False):
    if not yes:
        raise OpError("USAGE", f"解除挂载 '{kn_name}' 需 --yes")
    _goto_knowledge(sess, name)
    r = sess.b.ev(f"""(()=>{{const els=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes({json.dumps(kn_name)})&&(e.innerText||'').length<120);
      const row=els.sort((a,b)=>a.contains(b)?1:-1)[0];
      if(!row) return 'nf';
      row.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      return 'hovered'}})()""")
    if r == "nf":
        raise OpError("NOT_FOUND", f"未挂载 '{kn_name}'")
    sess.b.wait(800)
    # 找行内 删除/移除/解绑 入口
    sess.b.ev(f"""(()=>{{const els=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&['删除','移除','解绑','解除'].includes((e.innerText||'').trim()));
      if(els[0]) __deap.clickEl(els[0])}})()""")
    sess.b.wait(1200)
    sess.b.confirm_modal()
    sess.b.wait(1500)
    after = list_attached(sess, name)["data"]["attached"]
    return ok({"agent": name, "detached": not any(kn_name in x for x in after)})


def route(sess, sub, args):
    if sub == "list":
        return list_attached(sess, args.agent)
    if sub == "attach":
        return attach(sess, args.agent, args.name)
    if sub == "detach":
        return detach(sess, args.agent, args.name, args.yes)
    raise OpError("USAGE", f"未知 knowledge 子命令 {sub}")
