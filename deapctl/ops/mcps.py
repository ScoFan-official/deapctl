"""MCP 能力挂载管理。"""
import json

from ..envelope import OpError, ok
from .agent import open_editor


def _goto_mcp(sess, name):
    open_editor(sess, name)
    if not sess.b.click_text("MCP"):
        raise OpError("SELECTOR_MISS", "找不到「MCP」页签")
    sess.b.wait(1800)


# 已挂载区域：MCP 页签下「添加MCP」之后、「预览与测试」之前的卡片块
def _attached_names(sess):
    r = sess.b.ev("""(()=>{const cards=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes('MCP')&&(e.innerText||'').length>8&&(e.innerText||'').length<200);
      const items=cards.map(e=>(e.innerText||'').trim().split('\\n')[0])
        .filter(t=>t&&t!=='MCP'&&!t.startsWith('添加'));
      return items.filter((v,i,a)=>a.indexOf(v)===i)})()""")
    # 只保留像是 MCP 名的行（有「MCP」徽标的标题行）
    return [x for x in r if x]


def list_attached(sess, name):
    _goto_mcp(sess, name)
    return ok({"agent": name, "attached": _attached_names(sess)})


def catalog(sess, name):
    _goto_mcp(sess, name)
    if not sess.b.click_text("添加MCP"):
        raise OpError("SELECTOR_MISS", "找不到「添加MCP」")
    sess.b.wait(2000)
    items = sess.b.ev("""(()=>{const m=__deap.layers().find(e=>(e.innerText||'').length>100)||__deap.layers()[0];
      if(!m) return [];
      const cards=[...m.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').includes('MCP')&&(e.innerText||'').length>30);
      const titles=cards.map(e=>(e.innerText||'').trim().split('\\n')[0]);
      return titles.filter((v,i,a)=>a.indexOf(v)===i)})()""")
    # 关掉弹层
    sess.b.key("Escape")
    sess.b.wait(600)
    return ok({"agent": name, "catalog": items})


def attach(sess, name, mcp_name):
    _goto_mcp(sess, name)
    cur = _attached_names(sess)
    if any(mcp_name in x for x in cur):
        res = ok({"agent": name, "attached": cur}, f"'{mcp_name}' 已挂载（幂等）")
        res["code"] = "ALREADY"
        return res
    if not sess.b.click_text("添加MCP"):
        raise OpError("SELECTOR_MISS", "找不到「添加MCP」")
    sess.b.wait(2000)
    r = sess.b.ev(f"""(()=>{{const m=__deap.layers().find(e=>(e.innerText||'').length>100)||__deap.layers()[0];
      if(!m) return 'no-modal';
      const cards=[...m.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim().split('\\n')[0]==={json.dumps(mcp_name)}||(e.innerText||'').trim().startsWith({json.dumps(mcp_name)}+'\\n'));
      const card=cards.sort((a,b)=>a.contains(b)?1:-1)[0];
      if(!card) return 'no-card';
      const btn=[...card.querySelectorAll('button')].find(e=>__deap.vis(e)&&['添加','使用','安装'].includes((e.innerText||'').trim()));
      if(!btn) return 'no-btn';
      __deap.clickEl(btn); return 'clicked'}})()""")
    if r != "clicked":
        # 兜底：卡片内可能没有按钮，点击卡片本身
        raise OpError("SELECTOR_MISS", f"目录中 '{mcp_name}' 添加入口未找到 ({r})",
                      "deapctl mcp catalog <agent> 查看可用项")
    sess.b.wait(2500)
    # 可能有二次确认
    sess.b.ev("""(()=>{const m=__deap.layers()[0]; if(m){const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&['确定','添加','确认'].includes((e.innerText||'').trim()));if(btn)__deap.clickEl(btn)}})()""")
    sess.b.wait(2000)
    sess.b.key("Escape")
    sess.b.wait(800)
    _goto_mcp(sess, name)
    after = _attached_names(sess)
    done = any(mcp_name in x for x in after)
    return ok({"agent": name, "attached": after, "added": done},
              f"'{mcp_name}' 挂载成功" if done else "已提交但未回显")


def detach(sess, name, mcp_name, yes=False):
    if not yes:
        raise OpError("USAGE", f"解除挂载 '{mcp_name}' 需 --yes")
    _goto_mcp(sess, name)
    r = sess.b.ev(f"""(()=>{{const cards=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim().split('\\n')[0]==={json.dumps(mcp_name)});
      const card=cards.sort((a,b)=>a.contains(b)?1:-1)[0];
      if(!card) return 'nf';
      card.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
      return 'hovered'}})()""")
    if r == "nf":
        raise OpError("NOT_FOUND", f"未挂载 '{mcp_name}'")
    sess.b.wait(800)
    sess.b.ev("""(()=>{const els=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&['删除','移除','解绑','解除'].includes((e.innerText||'').trim()));if(els[0])__deap.clickEl(els[0])})()""")
    sess.b.wait(1200)
    sess.b.confirm_modal()
    sess.b.wait(1500)
    _goto_mcp(sess, name)
    after = _attached_names(sess)
    return ok({"agent": name, "detached": not any(mcp_name in x for x in after)})


def route(sess, sub, args):
    if sub == "catalog":
        return catalog(sess, args.agent)
    if sub == "list":
        return list_attached(sess, args.agent)
    if sub == "attach":
        return attach(sess, args.agent, args.name)
    if sub == "detach":
        return detach(sess, args.agent, args.name, args.yes)
    raise OpError("USAGE", f"未知 mcp 子命令 {sub}")
