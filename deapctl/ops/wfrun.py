"""工作流编辑器运行面：save / check / debug / runs。"""
import json
import time

from ..envelope import OpError, ok
from .workflow import open_wf_editor


def _click_header_item(sess, text):
    r = sess.b.ev(f"""(()=>{{const e=[...document.querySelectorAll('[class*=headerItem],[class*=header-item],[class*=tab]')].filter(x=>__deap.vis(x)&&(x.innerText||'').trim()==={json.dumps(text)}).pop()
        ||[...document.querySelectorAll('*')].filter(x=>__deap.vis(x)&&(x.innerText||'').trim()==={json.dumps(text)}&&x.children.length<4).pop();
      if(!e) return 'nf'; __deap.clickEl(e); return 'clicked'}})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", f"顶栏「{text}」未找到")
    sess.b.wait(1200)


def _ensure_editor(sess, agent, wf):
    t = sess.b.text()
    if "检查清单" in t and "调试" in t:
        return
    open_wf_editor(sess, agent, wf)


def save(sess, agent, wf):
    _ensure_editor(sess, agent, wf)
    r = sess.b.ev("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='保存');
      if(!b) return 'nf'; __deap.clickEl(b); return 'clicked'})()""")
    if r != "clicked":
        raise OpError("SELECTOR_MISS", "找不到「保存」")
    sess.b.wait(1500)
    sess.b.ev("""(()=>{const e=[...document.querySelectorAll('*')].find(x=>__deap.vis(x)&&(x.innerText||'').trim()==='仅保存'&&x.children.length<4);if(e)__deap.clickEl(e)})()""")
    sess.b.wait(1500)
    return ok({"agent": agent, "workflow": wf, "saved": True})


def check(sess, agent, wf):
    _ensure_editor(sess, agent, wf)
    _click_header_item(sess, "检查清单")
    sess.b.wait(1500)
    # 检查结果在面板/弹层：条目或「通过」
    r = sess.b.ev("""(()=>{const pans=[...document.querySelectorAll('[class*=popover],[class*=panel],[class*=drawer],[class*=modal],[class*=check]')].filter(e=>__deap.vis(e)&&(e.innerText||'').length>5);
      const p=pans.sort((a,b)=>(a.innerText||'').length-(b.innerText||'').length)[0];
      const t=(p||document.body).innerText||'';
      const lines=t.split('\\n').map(x=>x.trim()).filter(Boolean);
      const issues=lines.filter(l=>/不能为空|未|缺少|错误|失效|异常/.test(l)&&l.length<80);
      return {txt:lines.slice(0,40),issues:issues.slice(0,20)}})()""")
    issues = r.get("issues", [])
    clean = [i for i in issues if "未发布" not in i]
    return ok({"agent": agent, "workflow": wf,
               "passed": len(clean) == 0, "issues": clean,
               "raw": r.get("txt", [])[:25]})


def _fill_debug_params(sess, params: dict):
    """调试面板参数：按 label 匹配输入框，逐个填。"""
    for k, v in params.items():
        r = sess.b.ev(f"""(()=>{{const scope=document;
          const ins=[...scope.querySelectorAll('input,textarea,[contenteditable=true]')].filter(e=>__deap.vis(e));
          const t=ins.find(e=>{{let n=e;for(let i=0;i<8&&n;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim().split('\\n')[0]==={json.dumps(k)});if(sib)return true;n=n.parentElement}}return false}});
          if(!t) return 'nf';
          const b=t.getBoundingClientRect();
          if(t.tagName==='INPUT'||t.tagName==='TEXTAREA'){{__deap.fillIn(t,{json.dumps(str(v))});return 'filled'}}
          t.focus(); return [b.x+b.width/2,b.y+b.height/2]}})()""")
        if isinstance(r, list):
            sess.b.click_xy(r[0], r[1]); sess.b.wait(200)
            sess.b.type(str(v)); sess.b.wait(200)


def debug(sess, agent, wf, params=None, timeout=120):
    _ensure_editor(sess, agent, wf)
    _click_header_item(sess, "调试")
    sess.b.wait(1500)
    params = params or {}
    if params:
        _fill_debug_params(sess, params)
        sess.b.wait(500)
    # 点击「调试」/「开始调试」执行按钮
    r = sess.b.ev("""(()=>{const b=[...document.querySelectorAll('button')].filter(e=>__deap.vis(e)&&['调试','开始调试','运行','执行'].includes((e.innerText||'').trim()));
      if(!b.length) return 'nf'; __deap.clickEl(b[b.length-1]); return 'run'})()""")
    if r != "run":
        raise OpError("SELECTOR_MISS", "调试执行按钮未找到")
    # 等待运行结果（画布上会出「运行成功/失败」或执行详情）
    deadline = time.time() + timeout
    status = "running"
    while time.time() < deadline:
        sess.b.wait(3000)
        t = sess.b.text()
        if "运行成功" in t or "执行成功" in t:
            status = "success"
            break
        if "运行失败" in t or "执行失败" in t or "报错" in t:
            status = "failed"
            break
    # 抓执行详情（输出参数/各节点状态）
    detail = sess.b.ev("""(()=>{const t=document.body.innerText.split('\\n').map(x=>x.trim()).filter(Boolean);
      const i=t.findIndex(l=>l.includes('执行详情')||l.includes('输出参数'));
      return i>=0?t.slice(i,i+60):t.slice(-40)})()""")
    return ok({"agent": agent, "workflow": wf, "status": status,
               "detail": detail})


def runs(sess, agent, wf):
    _ensure_editor(sess, agent, wf)
    _click_header_item(sess, "执行记录")
    sess.b.wait(2000)
    rows = sess.b.ev("""(()=>{const t=document.body.innerText.split('\\n').map(x=>x.trim()).filter(Boolean);
      const i=t.findIndex(l=>l==='执行记录');
      return i>=0?t.slice(i,i+50):t.slice(0,50)})()""")
    return ok({"agent": agent, "workflow": wf, "recent": rows})


def route(sess, sub, args):
    if sub == "save":
        return save(sess, args.agent, args.name)
    if sub == "check":
        return check(sess, args.agent, args.name)
    if sub == "debug":
        params = json.loads(args.params) if getattr(args, "params", None) else {}
        return debug(sess, args.agent, args.name, params, getattr(args, "timeout", 120))
    if sub == "runs":
        return runs(sess, args.agent, args.name)
    raise OpError("USAGE", f"未知 wfrun 子命令 {sub}")
