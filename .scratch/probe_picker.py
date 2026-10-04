"""探针：打开 wftest 节点3抽屉，点问题字段⊕，dump picker-pane 结构。"""
import sys, json
sys.path.insert(0, ".")
from deapctl.session import Session
from deapctl.ops.wfnode import WfEditor, DRAWER

s = Session()
try:
    ed = WfEditor(s, "deapctl复测机", "wftest")
    ed.open_drawer("3.")
    # 复刻 pick_var 前半段：聚焦编辑区 + 点⊕
    r = s.b.ev(f"""(()=>{{const d={DRAWER};
      const areas=[...d.querySelectorAll('[class*=inputVars]')].filter(e=>__deap.vis(e));
      const target=areas.find(a=>{{let n=a;for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==a&&!c.contains(a)&&(c.innerText||'').trim().startsWith('问题'));if(sib)return true;n=n.parentElement}}return false}})||areas[0];
      if(!target) return 'no-field';
      const ed2=target.querySelector('[data-slate-editor=true]');
      const ic=target.querySelector('[class*=addIcon],[class*=varsPicker] [role=img]');
      if(!ic) return 'no-icon';
      const eb=ed2?ed2.getBoundingClientRect():null;
      const b=ic.getBoundingClientRect();
      return {{icon:{{x:b.x+b.width/2,y:b.y+b.height/2}},editor:eb?{{x:eb.x+eb.width/2,y:eb.y+eb.height/2}}:null}}}})()""")
    print("icon_pos:", r)
    if isinstance(r, dict):
        if r.get("editor"):
            s.b.click_xy(r["editor"]["x"], r["editor"]["y"])
            s.b.wait(600)
        s.b.click_xy(r["icon"]["x"], r["icon"]["y"])
        s.b.wait(1500)
    # dump picker-pane 结构
    info = s.b.ev("""(()=>{const ps=[...document.querySelectorAll('[class*="picker-pane_"]')].filter(e=>__deap.vis(e));
      const p=ps.pop();
      if(!p) return 'no-panel';
      const inputs=[...p.querySelectorAll('input')].map(e=>({ph:e.placeholder||'',cls:(e.className||'').slice(0,60)}));
      const titles=[...p.querySelectorAll('[class*=pane-item-title],.dtd-tree-title span,.dtd-tree-node-content-wrapper')]
        .filter(e=>__deap.vis(e)).map(e=>(e.innerText||'').trim()).filter(Boolean);
      const groups=[...p.querySelectorAll('.dtd-tree-treenode,[class*=group-title],[class*=node-title]')]
        .filter(e=>__deap.vis(e)).slice(0,15).map(e=>(e.innerText||'').trim().split('\\n')[0]);
      const searchLike=[...p.querySelectorAll('[class*=search],[class*=filter]')].filter(e=>__deap.vis(e)).map(e=>e.className.slice(0,60));
      return {panelCls:p.className.slice(0,80),inputs,titles,groups,searchLike,html:p.outerHTML.slice(0,3000)}})()""")
    print(json.dumps(info, ensure_ascii=False, indent=1))
finally:
    s.close()
