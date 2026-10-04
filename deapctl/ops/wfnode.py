"""工作流编辑器内节点操作。

画布结构（已实测）：
- 节点 = [class*=node-wrap-box]，innerText 以「序号./标题」开头
- 连线中点 = [class*=add-node-btn]（"+"按钮，点击出类型面板）
- 类型面板 = 逻辑/工具|AI|钉钉协作|其他业务 四页签 + 两列条目
- 点击节点 → 左侧抽屉 [class*=drawer-panel-body-v2]
- 触发节点抽屉：添加参数按钮（真 button）→ 名称/类型/默认值/说明/必填switch
- 变量选择：字段旁 ⊕ 图标 → 左侧变量面板（按类型过滤）
"""
import json

from ..envelope import OpError, ok
from .workflow import open_wf_editor

DRAWER = "[...document.querySelectorAll('[class*=drawer-panel-body-v2]')].filter(e=>__deap.vis(e)).pop()"


def _nodes_js():
    return """[...document.querySelectorAll('[class*=node-wrap-box]')].filter(e=>__deap.vis(e))
      .map(e=>{const b=e.getBoundingClientRect();
        const ls=(e.innerText||'').trim().split('\\n').map(x=>x.trim()).filter(Boolean);
        return {text:ls.join('/'),x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2),
                w:Math.round(b.width),h:Math.round(b.height)}})"""


def _add_btns_js():
    return """[...document.querySelectorAll('[class*=add-node-btn]')].filter(e=>__deap.vis(e))
      .map(e=>{const b=e.getBoundingClientRect();return {x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)}})"""


class WfEditor:
    def __init__(self, sess, agent, wf_name):
        self.sess, self.agent, self.wf = sess, agent, wf_name
        open_wf_editor(sess, agent, wf_name)

    # ---- 画布 ----
    def nodes(self):
        return self.sess.b.ev(f"(()=>{_nodes_js()})()")

    def add_buttons(self):
        return self.sess.b.ev(f"(()=>{_add_btns_js()})()")

    def find_node(self, seq_or_title):
        """按序号前缀（'2.'）或标题包含匹配。"""
        ns = self.nodes()
        s = str(seq_or_title)
        for n in ns:
            if n["text"].startswith(s) or s in n["text"]:
                return n
        raise OpError("NOT_FOUND", f"画布上找不到节点 '{s}'",
                      f"现有节点: {[n['text'] for n in ns]}")

    def open_drawer(self, seq_or_title):
        n = self.find_node(seq_or_title)
        self.sess.b.click_xy(n["x"], n["y"])
        self.sess.b.wait(1500)
        ok_open = self.sess.b.ev(f"(()=>{{const d={DRAWER}; return !!d&&(d.innerText||'').length>10}})()")
        if not ok_open:
            # 重试：dispatch 点击
            self.sess.b.ev(f"""(()=>{{const ns={_nodes_js()};
              const n=ns.find(x=>x.text.startsWith({json.dumps(str(seq_or_title))}));
              if(n){{const els=[...document.querySelectorAll('[class*=node-wrap-box]')].filter(e=>__deap.vis(e));
                const el=els.find(e=>{{const b=e.getBoundingClientRect();return Math.abs(b.x+b.width/2-n.x)<8&&Math.abs(b.y+b.height/2-n.y)<8}});
                if(el)__deap.clickEl(el)}}}})()""")
            self.sess.b.wait(1500)
            ok_open = self.sess.b.ev(f"(()=>{{const d={DRAWER}; return !!d&&(d.innerText||'').length>10}})()")
        if not ok_open:
            raise OpError("SELECTOR_MISS", "节点抽屉未打开")
        return n

    def close_drawer(self):
        self.sess.b.key("Escape")
        self.sess.b.wait(500)

    def save(self):
        r = self.sess.b.ev("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='保存');
          if(!b) return 'nf'; __deap.clickEl(b); return 'clicked'})()""")
        if r != "clicked":
            raise OpError("SELECTOR_MISS", "找不到「保存」按钮")
        self.sess.b.wait(2000)
        # 「仅保存」兜底（拆分按钮）
        m = self.sess.b.ev("""(()=>{const e=[...document.querySelectorAll('*')].find(x=>__deap.vis(x)&&(x.innerText||'').trim()==='仅保存'&&x.children.length<3);
          if(e){__deap.clickEl(e);return 'clicked-sub'}return 'none'})()""")
        self.sess.b.wait(1500)
        return True

    # ---- 节点类型面板 ----
    def insert_node(self, after_idx, type_name):
        """在序号为 after_idx 的节点后插入 type_name 节点。after_idx=-1 表示最后一个加号位。"""
        btns = self.add_buttons()
        if not btns:
            raise OpError("SELECTOR_MISS", "画布上没有可插入点")
        b = btns[after_idx]
        self.sess.b.click_xy(b["x"], b["y"])
        self.sess.b.wait(1500)
        r = self.sess.b.ev(f"""(()=>{{const items=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(type_name)}&&e.children.length<4);
          if(!items.length) return 'nf';
          __deap.clickEl(items[items.length-1]); return 'clicked'}})()""")
        if r != "clicked":
            raise OpError("SELECTOR_MISS", f"节点类型 '{type_name}' 不在面板中")
        self.sess.b.wait(1800)
        return {"nodes": self.nodes()}

    def insert_into_loop(self, loop_seq, type_name, position="top"):
        """往循环体内部插节点。注意：实测编辑器总是落在循环体顶部，
        多子节点请倒序调用。position 参数目前仅为语义标注。"""
        # 循环节点的 node-wrap-box 内部有自己的 add-node-btn
        r = self.sess.b.ev(f"""(()=>{{const ns=[...document.querySelectorAll('[class*=node-wrap-box]')].filter(e=>__deap.vis(e));
          const loop=ns.find(e=>(e.innerText||'').trim().startsWith({json.dumps(str(loop_seq))})&&(e.innerText||'').includes('循环'));
          if(!loop) return 'no-loop';
          const inner=[...loop.querySelectorAll('[class*=add-node-btn]')].filter(e=>__deap.vis(e));
          if(!inner.length) return 'no-inner';
          const b=inner[0].getBoundingClientRect(); return [b.x+b.width/2,b.y+b.height/2]}})()""")
        if not isinstance(r, list):
            raise OpError("SELECTOR_MISS", f"循环节点 '{loop_seq}' 内未找到插入点 ({r})")
        self.sess.b.click_xy(r[0], r[1])
        self.sess.b.wait(1500)
        r = self.sess.b.ev(f"""(()=>{{const items=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(type_name)}&&e.children.length<4);
          if(!items.length) return 'nf';
          __deap.clickEl(items[items.length-1]); return 'clicked'}})()""")
        if r != "clicked":
            raise OpError("SELECTOR_MISS", f"节点类型 '{type_name}' 不在面板中")
        self.sess.b.wait(1800)
        return {"nodes": self.nodes()}

    def delete_node(self, seq_or_title):
        n = self.find_node(seq_or_title)
        # 悬停节点 → 右上 ⋯ → 删除
        self.sess.b.ev(f"""(()=>{{const els=[...document.querySelectorAll('[class*=node-wrap-box]')].filter(e=>__deap.vis(e));
          const el=els.find(e=>{{const b=e.getBoundingClientRect();return Math.abs(b.x+b.width/2-{n['x']})<10&&Math.abs(b.y+b.height/2-{n['y']})<10}});
          if(!el) return 'nf';
          el.dispatchEvent(new MouseEvent('mouseover',{{bubbles:true}}));
          const ic=[...el.querySelectorAll('svg,[class*=icon],button')].filter(x=>__deap.vis(x));
          const c=ic[ic.length-1]; if(!c) return 'no-menu';
          __deap.clickEl(c); return 'menu'}})()""")
        self.sess.b.wait(1000)
        r = self.sess.b.ev("""(()=>{const it=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==='删除'&&e.children.length<4);
          if(!it.length) return 'nf'; __deap.clickEl(it[it.length-1]); return 'clicked'})()""")
        if r != "clicked":
            raise OpError("SELECTOR_MISS", "节点 ⋯ 菜单/删除项未出现")
        self.sess.b.wait(1200)
        # 确认弹窗
        self.sess.b.ev("""(()=>{const m=[...document.querySelectorAll('.dtd-modal,[role=dialog],[class*=popconfirm]')].filter(e=>__deap.vis(e)).pop();
          if(m){const btn=[...m.querySelectorAll('button')].find(e=>__deap.vis(e)&&['删除','确定','确认'].includes((e.innerText||'').trim()));if(btn)__deap.clickEl(btn)}})()""")
        self.sess.b.wait(1500)
        return {"nodes": self.nodes()}

    # ---- 触发节点参数 ----
    def param_add(self, name, desc="", required=True, ptype="文本"):
        self.open_drawer("1.")
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const btn=[...d.querySelectorAll('button')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='添加参数');
          if(!btn) return 'no-btn'; __deap.clickEl(btn); return 'added'}})()""")
        if r != "added":
            raise OpError("SELECTOR_MISS", "「添加参数」按钮未找到")
        self.sess.b.wait(1200)
        # 最后一行参数组的字段
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const labels=[...d.querySelectorAll('*')].filter(e=>(e.innerText||'').trim()==='参数名称:');
          const lab=labels[labels.length-1]; if(!lab) return 'no-label';
          const row=lab.closest('[class*=row],[class*=item],form,div');
          const scope=row?row.parentElement:d;
          const nm=[...d.querySelectorAll('input')].filter(e=>__deap.vis(e)&&(e.placeholder||'')==='请输入').pop();
          if(!nm) return 'no-name';
          __deap.fillIn(nm,{json.dumps(name)});
          const ds=[...d.querySelectorAll('textarea')].filter(e=>__deap.vis(e)).pop();
          if(ds&&{json.dumps(desc)}) __deap.fillIn(ds,{json.dumps(desc)});
          return 'filled'}})()""")
        if r != "filled":
            raise OpError("SELECTOR_MISS", f"参数字段未找到 {r}")
        self.sess.b.wait(400)
        # 必填开关：参数行内的 switch（默认开启？）
        if not required:
            self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const sws=[...d.querySelectorAll('.dtd-switch')].filter(e=>__deap.vis(e));
              const sw=sws[sws.length-2]||sws[sws.length-1]; // 行内必填switch（最后一个常是全局确认开关）
              if(sw&&!sw.className.includes('checked')&&!sw.getAttribute('aria-checked')==='true'){{}}
              if(sw) __deap.clickEl(sw)}})()""")
            self.sess.b.wait(500)
        # 参数类型（非默认文本时）
        if ptype and ptype != "文本":
            self._set_last_param_type(ptype)
        self.save()
        return {"param": name}

    # ---- 通用抽屉工具 ----
    def _drawer_fields(self):
        """抽屉内可编辑区盘点：editableArea(Slate) / input / select。"""
        return self.sess.b.ev(f"""(()=>{{const d={DRAWER}; if(!d) return null;
          const eds=[...d.querySelectorAll('[data-slate-editor=true]')].filter(e=>__deap.vis(e)).map(e=>{{
            const b=e.getBoundingClientRect();let label='';let n=e;
            for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim()&&(c.innerText||'').trim().length<12&&!/^请输入/.test((c.innerText||'').trim()));
              if(sib){{label=(sib.innerText||'').trim().split('\\n')[0];break}}n=n.parentElement}}
            return {{kind:'slate',label,x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)}}}});
          const ins=[...d.querySelectorAll('input,textarea')].filter(e=>__deap.vis(e)).map(e=>{{
            const b=e.getBoundingClientRect();let label='';let n=e;
            for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim()&&(c.innerText||'').trim().length<15);
              if(sib){{label=(sib.innerText||'').trim().split('\\n')[0];break}}n=n.parentElement}}
            return {{kind:e.tagName.toLowerCase(),label,ph:(e.placeholder||'').slice(0,14),x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)}}}});
          const sws=[...d.querySelectorAll('.dtd-switch')].filter(e=>__deap.vis(e)).map(e=>{{
            const b=e.getBoundingClientRect();let label='';let n=e;
            for(let i=0;i<6&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim()&&(c.innerText||'').trim().length<15);
              if(sib){{label=(sib.innerText||'').trim().split('\\n')[0];break}}n=n.parentElement}}
            return {{kind:'switch',label,on:e.className.includes('checked')||e.getAttribute('aria-checked')==='true',x:Math.round(b.x+b.width/2),y:Math.round(b.y+b.height/2)}}}});
          return {{eds,ins,sws}}}})()""")

    def pick_var(self, field_label, var_text, ed_index=None):
        """给 label 匹配的 Slate 字段插入变量叶子（如 '听记原文' / '步骤4.任务标题'）。

        var_text: 面板里显示的叶子名（默认按精确文本匹配最后一项）。
        """
        icon_pos_js = f"""(()=>{{const d={DRAWER}; if(!d) return 'no-drawer';
          const areas=[...d.querySelectorAll('[class*=inputVars]')].filter(e=>__deap.vis(e));
          let target=null;
          if({json.dumps(field_label)}){{
            target=areas.find(a=>{{let n=a;for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==a&&!c.contains(a)&&(c.innerText||'').trim().startsWith({json.dumps(field_label)}));if(sib)return true;n=n.parentElement}}return false}});
          }} else {{
            target=areas[{json.dumps(ed_index if ed_index is not None else 0)}];
          }}
          if(!target) return 'no-field';
          const ed=target.querySelector('[data-slate-editor=true]');
          const ic=target.querySelector('[class*=addIcon],[class*=varsPicker] [role=img]');
          if(!ic) return 'no-icon';
          const eb=ed?ed.getBoundingClientRect():null;
          const b=ic.getBoundingClientRect();
          return {{icon:{{x:b.x+b.width/2,y:b.y+b.height/2}},
                  editor:eb?{{x:eb.x+eb.width/2,y:eb.y+eb.height/2}}:null}}}})()"""
        r = self.sess.b.ev(icon_pos_js)
        if not isinstance(r, dict):
            raise OpError("SELECTOR_MISS", f"字段 '{field_label}' 的⊕未找到 ({r})")
        if r.get("editor"):
            self.sess.b.click_xy(r["editor"]["x"], r["editor"]["y"])
            self.sess.b.wait(600)
        self.sess.b.click_xy(r["icon"]["x"], r["icon"]["y"])
        self.sess.b.wait(1200)
        leaf = str(var_text).split(".")[-1]
        for attempt in range(4):
            r2 = self.sess.b.ev(f"""(()=>{{const ps=[...document.querySelectorAll('[class*="picker-pane_"]')].filter(e=>__deap.vis(e));
              const p=ps.pop();
              if(!p) return 'no-panel';
              const leaf={json.dumps(leaf)};
              const items=[...p.querySelectorAll('[class*=pane-item-title],.dtd-tree-title span')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()===leaf);
              if(items.length){{__deap.clickEl(items[items.length-1]);
                const si=p.querySelector('input.dtd-search-bar-input');if(si&&si.value)__deap.fillIn(si,'');
                return 'picked'}}
              // 面板自带搜索框（dtd-search-bar-input）：搜索是权威过滤，
              // 优先于 expand/scroll 遍历虚拟化树（后者渲染时序不稳曾致间歇性漏选）。
              const si=p.querySelector('input.dtd-search-bar-input');
              if(si){{
                if((si.value||'')!==leaf){{__deap.fillIn(si,leaf);return 'searched'}}
                return 'no-leaf-searched:'+[...p.querySelectorAll('[class*=pane-item-title],.dtd-tree-title span')].filter(e=>__deap.vis(e)).slice(-20).map(e=>(e.innerText||'').trim()).join('|')}}
              // 无搜索框的老面板：展开下一个折叠组（含 '+'/'>' 箭头的父节点行）
              const sw=[...p.querySelectorAll('.dtd-tree-switcher,[class*=switcher],[class*=arrow]')].filter(e=>__deap.vis(e));
              const closed=sw.find(e=>!String(e.className).includes('open'));
              if(closed){{__deap.clickEl(closed);return 'expand'}}
              const hold=p.querySelector('.dtd-tree-list-holder,[class*=holder]');
              if(hold&&hold.scrollTop+hold.clientHeight<hold.scrollHeight-20){{hold.scrollTop+=300;return 'scroll'}}
              return 'no-leaf:'+[...p.querySelectorAll('[class*=pane-item-title]')].filter(e=>__deap.vis(e)).slice(-20).map(e=>(e.innerText||'').trim()).join('|')}})()""")
            if r2 == "picked":
                break
            if r2 == "no-panel":
                r = self.sess.b.ev(icon_pos_js)
                if isinstance(r, dict):
                    if r.get("editor"):
                        self.sess.b.click_xy(r["editor"]["x"], r["editor"]["y"])
                        self.sess.b.wait(500)
                    self.sess.b.click_xy(r["icon"]["x"], r["icon"]["y"])
            if isinstance(r2, str) and r2.startswith("no-leaf-searched:"):
                break  # 搜索过滤是权威结果，搜不到=变量不存在或被类型过滤，不再展开/滚动
            self.sess.b.wait(900)
        if not isinstance(r2, str) or not r2.startswith("picked"):
            raise OpError("SELECTOR_MISS", f"变量 '{var_text}' 未选中（已用面板搜索过滤确认不在列表中，可能是变量缺失或类型不匹配）" if isinstance(r2, str) and r2.startswith("no-leaf-searched:") else f"变量 '{var_text}' 未选中", str(r2)[:300])
        self.sess.b.wait(800)

    def fill_slate(self, field_label, text, ed_index=None):
        """Slate 编辑器填文本：真实点击聚焦 + keyboard.type。"""
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER}; if(!d) return 'no-drawer';
          const eds=[...d.querySelectorAll('[data-slate-editor=true]')].filter(e=>__deap.vis(e));
          let t=null;
          if({json.dumps(field_label)}){{
            t=eds.find(e=>{{let n=e;for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim().startsWith({json.dumps(field_label)}));if(sib)return true;n=n.parentElement}}return false}});
          }} else {{ t=eds[{ed_index or 0}] }}
          if(!t) return 'no-field';
          const b=t.getBoundingClientRect(); return [b.x+b.width/2,b.y+b.height/2]}})()""")
        if not isinstance(r, list):
            raise OpError("SELECTOR_MISS", f"Slate 字段 '{field_label}' 未找到 ({r})")
        self.sess.b.click_xy(r[0], r[1])
        self.sess.b.wait(300)
        self.sess.b.type(text)
        self.sess.b.wait(400)

    def _drawer_tab(self, tab):
        self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const t=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(tab)}&&e.children.length<3);
          if(t) __deap.clickEl(t)}})()""")
        self.sess.b.wait(800)

    def select_option(self, label_or_index, option_text):
        """点抽屉内某个下拉（按 label 或序位），选 option_text。"""
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER}; if(!d) return 'no-drawer';
          const sels=[...d.querySelectorAll('input.dtd-select-selection-search-input,[class*=select] input')].filter(e=>__deap.vis(e));
          let s=null;
          if({json.dumps(label_or_index)}!==null&&typeof {json.dumps(label_or_index)}==='number') s=sels[{json.dumps(label_or_index)}];
          else s=sels.find(e=>{{let n=e;for(let i=0;i<8&&n&&n!==d;i++){{const sib=[...n.children].find(c=>c!==e&&!c.contains(e)&&(c.innerText||'').trim().startsWith({json.dumps(str(label_or_index or ''))}));if(sib)return true;n=n.parentElement}}return false}})||sels[0];
          if(!s) return 'no-sel'; __deap.clickEl(s); return 'opened'}})()""")
        if r != "opened":
            raise OpError("SELECTOR_MISS", f"下拉 '{label_or_index}' 未找到")
        self.sess.b.wait(1000)
        r2 = self.sess.b.ev(f"""(()=>{{const opts=[...document.querySelectorAll('.dtd-select-item-option,[class*=option],[role=option],li')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(option_text)});
          if(!opts.length) return 'nf'; __deap.clickEl(opts[opts.length-1]); return 'ok'}})()""")
        if r2 != "ok":
            raise OpError("SELECTOR_MISS", f"选项 '{option_text}' 未找到")
        self.sess.b.wait(800)

    # ---- LLM 节点 ----
    def config_llm(self, node, model=None, question_vars=None, prompt=None,
                   outputs=None, json_mode=None):
        """配 LLM 抽屉。outputs=[{name,desc,type}], json_mode=示例JSON字符串。"""
        self.open_drawer(node)
        if model:
            self.select_option(0, model)  # 第一个 select 是模型
        for v in (question_vars or []):
            self.pick_var("问题", v)
        if prompt is not None:
            self.fill_slate("提示词", prompt)
        if outputs:
            self._set_struct_outputs(outputs)
        if json_mode:
            self._set_json_mode(json_mode)
        self.save()
        return True

    def _set_struct_outputs(self, outputs):
        """高级设置→结构化输出 开关 + 参数行。"""
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          // 展开高级设置
          const adv=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='高级设置'&&e.children.length<5);
          if(adv) __deap.clickEl(adv);
          return 'adv'}})()""")
        self.sess.b.wait(800)
        # 结构化输出开关：找 label 行内 switch
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const lb=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim().startsWith('结构化输出')&&e.children.length<4);
          if(!lb) return 'no-label';
          let n=lb;for(let i=0;i<5&&n&&n!==d;i++){{const sw=[...n.querySelectorAll('.dtd-switch')].filter(e=>__deap.vis(e))[0];
            if(sw){{if(!sw.className.includes('checked')) __deap.clickEl(sw); return 'toggled'}} n=n.parentElement}}
          return 'no-sw'}})()""")
        self.sess.b.wait(800)
        for o in outputs:
            # 点 添加/新增输出参数
            r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const btn=[...d.querySelectorAll('button,div')].find(e=>__deap.vis(e)&&['添加','添加参数','新增'].includes((e.innerText||'').trim()));
              if(!btn) return 'no-add'; __deap.clickEl(btn); return 'added'}})()""")
            self.sess.b.wait(800)
            # 展开最新参数行 → 填名称/说明/类型
            r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const rows=[...d.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim().startsWith('参数'));
              const row=rows[rows.length-1]; if(!row) return 'no-row';
              __deap.clickEl(row); return 'expand'}})()""")
            self.sess.b.wait(800)
            self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const nm=[...d.querySelectorAll('input')].filter(e=>__deap.vis(e)&&(e.placeholder||'').includes('请输入')).pop();
              if(nm) __deap.fillIn(nm,{json.dumps(o['name'])});
              const ds=[...d.querySelectorAll('textarea')].filter(e=>__deap.vis(e)).pop();
              if(ds&&{json.dumps(o.get('desc',''))}) __deap.fillIn(ds,{json.dumps(o.get('desc',''))});
              return 'filled'}})()""")
            self.sess.b.wait(400)
            if o.get("type") and o["type"] != "文本":
                self._set_last_param_type(o["type"])

    def _set_json_mode(self, example_json):
        self._drawer_tab("输出")
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const t=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim()==='JSON模式'&&e.children.length<4);
          if(!t) return 'no-tab'; __deap.clickEl(t); return 'tab'}})()""")
        self.sess.b.wait(800)
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const ta=[...d.querySelectorAll('textarea,[contenteditable=true]')].filter(e=>__deap.vis(e));
          const t=ta[0]; if(!t) return 'no-ta';
          if(t.tagName==='TEXTAREA') __deap.fillIn(t,{json.dumps(example_json)});
          else {{const b=t.getBoundingClientRect();t.focus();
            return [b.x+b.width/2,b.y+b.height/2]}}
          return 'filled'}})()""")
        if isinstance(r, list):
            self.sess.b.click_xy(r[0], r[1]); self.sess.b.wait(300)
            self.sess.b.type(example_json); self.sess.b.wait(300)
        # 确认/生成结构
        self.sess.b.ev("""(()=>{const btns=[...document.querySelectorAll('button')].filter(e=>__deap.vis(e)&&['确定','生成','确认','应用'].includes((e.innerText||'').trim()));if(btns[0])__deap.clickEl(btns[0])})()""")
        self.sess.b.wait(1000)
        self._drawer_tab("配置")

    # ---- 循环 / 结束 节点 ----
    def bind_loop(self, node, array_var):
        """循环抽屉「循环内容」绑数组变量（如 '任务清单'）。"""
        self.open_drawer(node)
        self.pick_var(None, array_var, ed_index=0)
        self.save()
        return True

    def config_end(self, pairs):
        """结束节点输出参数：pairs=[{name,var}]。"""
        self.open_drawer("结束")
        for p in pairs:
            # 添加输出参数 → 填名 → 绑变量
            r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const btn=[...d.querySelectorAll('button,div')].find(e=>__deap.vis(e)&&['添加参数','添加'].includes((e.innerText||'').trim()));
              if(btn){{__deap.clickEl(btn);return 'added'}}return 'no-add'}})()""")
            self.sess.b.wait(800)
            self.sess.b.ev(f"""(()=>{{const d={DRAWER};
              const nm=[...d.querySelectorAll('input')].filter(e=>__deap.vis(e)&&(e.placeholder||'').includes('请输入')).pop();
              if(nm) __deap.fillIn(nm,{json.dumps(p['name'])})}})()""")
            self.sess.b.wait(400)
            self.pick_var(None, p["var"], ed_index=None)
        self.save()
        return True

    # ---- 新增记录（AI表格）节点 ----
    def config_record(self, node, base=None, table=None, fields=None, fixed=None):
        """配「新增记录」：base=AI表格文档名, table=数据表名,
        fields={字段名: 变量叶子名}, fixed={枚举/文本字段名: 字面值}。"""
        self.open_drawer(node)
        if base:
            self._pick_base(base)
        if table:
            self._pick_table(table)
        for fname, var in (fields or {}).items():
            self._bind_record_field(fname, var)
        for fname, val in (fixed or {}).items():
            self._set_record_field_literal(fname, val)
        self.save()
        return True

    def _pick_base(self, base_name):
        """点「选择AI表格」旁的文档图标 → Base 选择弹层（可能在 iframe）。"""
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER}; if(!d) return 'no-drawer';
          const lb=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim().startsWith('选择AI表格')&&e.children.length<6);
          if(!lb) return 'no-label';
          let n=lb;for(let i=0;i<6&&n&&n!==d;i++){{const ic=[...n.querySelectorAll('[role=img],svg,img')].filter(e=>__deap.vis(e))[0];
            if(ic){{const b=ic.getBoundingClientRect();return [b.x+b.width/2,b.y+b.height/2]}}n=n.parentElement}}
          return 'no-icon'}})()""")
        if not isinstance(r, list):
            raise OpError("SELECTOR_MISS", "「选择AI表格」图标未找到")
        self.sess.b.click_xy(r[0], r[1])
        self.sess.b.wait(2500)
        # Base 选择框常在 iframe 弹层
        picked = False
        for fr in self.sess.b.page.frames:
            try:
                hit = fr.evaluate(f"""(()=>{{const rows=[...document.querySelectorAll('*')].filter(e=>e.offsetParent&&(e.innerText||'').trim()==={json.dumps(base_name)}&&e.children.length<8);
                  if(!rows.length) return null;
                  const row=rows[rows.length-1];
                  row.dispatchEvent(new MouseEvent('click',{{bubbles:true}}));
                  return 'picked'}})()""")
            except Exception:
                continue
            if hit == "picked":
                picked = True
                self.sess.b.wait(800)
                try:
                    fr.evaluate("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>e.offsetParent&&['确定','确认'].includes((e.innerText||'').trim()));if(b){b.dispatchEvent(new MouseEvent('click',{bubbles:true}));return 'ok'}return 'nf'})()""")
                except Exception:
                    pass
                break
        if not picked:
            # 非 iframe 兜底：主文档里找
            r = self.sess.b.ev(f"""(()=>{{const rows=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(base_name)}&&e.children.length<8);
              if(!rows.length) return 'nf'; __deap.clickEl(rows[rows.length-1]); return 'picked'}})()""")
            if r != "picked":
                raise OpError("SELECTOR_MISS", f"AI表格 '{base_name}' 未找到")
            self.sess.b.wait(800)
            self.sess.b.ev("""(()=>{const b=[...document.querySelectorAll('button')].find(e=>__deap.vis(e)&&['确定','确认'].includes((e.innerText||'').trim()));if(b)__deap.clickEl(b)})()""")
        self.sess.b.wait(1500)

    def _pick_table(self, table_name):
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const s=[...d.querySelectorAll('*')].find(e=>__deap.vis(e)&&(e.innerText||'').trim().startsWith('请选择数据表')&&e.children.length<4);
          if(!s) return 'no-sel'; __deap.clickEl(s); return 'opened'}})()""")
        if r != "opened":
            raise OpError("SELECTOR_MISS", "「请选择数据表」未找到")
        self.sess.b.wait(1200)
        r2 = self.sess.b.ev(f"""(()=>{{const opts=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(table_name)}&&e.children.length<4);
          if(!opts.length) return 'nf'; __deap.clickEl(opts[opts.length-1]); return 'ok'}})()""")
        if r2 != "ok":
            raise OpError("SELECTOR_MISS", f"数据表 '{table_name}' 未找到")
        self.sess.b.wait(1500)

    def _record_field_row(self, fname):
        """找到字段名行的容器（抽屉内 label 匹配）。"""
        return f"""(()=>{{const d={DRAWER}; if(!d) return null;
          const lb=[...d.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(fname)}&&e.children.length<4);
          if(!lb.length) return null;
          let row=lb[lb.length-1];
          for(let i=0;i<6&&row&&row!==d;i++){{if(row.querySelector('.dtd-switch,[class*=addIcon],[role=img],input,select'))return row;row=row.parentElement}}
          return lb[lb.length-1].parentElement}})()"""

    def _bind_record_field(self, fname, var):
        """字段行 ⊕ → 变量面板 → dispatch 叶子（真实点击会被抽屉遮挡）。"""
        icon_js = self._record_field_row(fname) + ""
        pos = self.sess.b.ev(f"""(()=>{{const row={icon_js};
          if(!row) return 'no-row';
          const ic=row.querySelector('[class*=addIcon]')||[...row.querySelectorAll('[role=img],svg')].filter(e=>__deap.vis(e)).pop();
          if(!ic) return 'no-icon';
          const b=ic.getBoundingClientRect();return {{x:b.x+b.width/2,y:b.y+b.height/2}}}})()""")
        if not isinstance(pos, dict):
            raise OpError("SELECTOR_MISS", f"字段 '{fname}' 的⊕未找到 ({pos})")
        self.sess.b.click_xy(pos["x"], pos["y"])
        self.sess.b.wait(1200)
        leaf = str(var).split(".")[-1]
        for _ in range(4):
            r2 = self.sess.b.ev(f"""(()=>{{const p=[...document.querySelectorAll('[class*=\"picker-pane_\"]')].filter(e=>__deap.vis(e)).pop();
              if(!p) return 'no-panel';
              const items=[...p.querySelectorAll('[class*=pane-item-title]')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(leaf)});
              if(items.length){{__deap.clickEl(items[items.length-1]);
                const si=p.querySelector('input.dtd-search-bar-input');if(si&&si.value)__deap.fillIn(si,'');
                return 'picked'}}
              const si=p.querySelector('input.dtd-search-bar-input');
              if(si){{
                if((si.value||'')!=={json.dumps(leaf)}){{__deap.fillIn(si,{json.dumps(leaf)});return 'searched'}}
                return 'no-leaf'}}
              const hold=p.querySelector('.dtd-tree-list-holder,[class*=holder]');
              if(hold&&hold.scrollTop+hold.clientHeight<hold.scrollHeight-20){{hold.scrollTop+=300;return 'scroll'}}
              return 'no-leaf'}})()""")
            if r2 == "picked":
                break
            if r2 == "no-leaf":
                break  # 搜索过滤后的 no-leaf 是权威判定
            self.sess.b.wait(900)
        if r2 != "picked":
            raise OpError("VAR_TYPE_MISMATCH" if r2 == "no-leaf" else "SELECTOR_MISS",
                          f"字段 '{fname}' 绑变量 '{var}' 失败",
                          "可能变量类型与字段类型不匹配（面板按类型过滤）" if r2 == "no-leaf" else "")
        self.sess.b.wait(800)

    def _set_record_field_literal(self, fname, val):
        """枚举/文本字段直接选/填字面值。"""
        r = self.sess.b.ev(f"""(()=>{{const row={self._record_field_row(fname)};
          if(!row) return 'no-row';
          const inp=row.querySelector('input,textarea,[contenteditable=true]');
          if(!inp) return 'no-inp';
          if(inp.tagName==='INPUT'&&inp.closest('[class*=select],[class*=picker]')){{__deap.clickEl(inp);return 'select'}}
          __deap.fillIn(inp,{json.dumps(str(val))}); return 'filled'}})()""")
        if r == "select":
            self.sess.b.wait(1000)
            self.sess.b.ev(f"""(()=>{{const opts=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(str(val))}&&e.children.length<3);
              if(opts.length)__deap.clickEl(opts[opts.length-1])}})()""")
            self.sess.b.wait(600)
        elif r == "no-row":
            raise OpError("SELECTOR_MISS", f"字段 '{fname}' 未找到")

    def _set_last_param_type(self, ptype):
        r = self.sess.b.ev(f"""(()=>{{const d={DRAWER};
          const t=[...d.querySelectorAll('input')].filter(e=>__deap.vis(e)&&!e.placeholder);
          const sel=t[t.length-1]; if(!sel) return 'no-sel';
          __deap.clickEl(sel); return 'opened'}})()""")
        self.sess.b.wait(1000)
        r2 = self.sess.b.ev(f"""(()=>{{const opts=[...document.querySelectorAll('*')].filter(e=>__deap.vis(e)&&(e.innerText||'').trim()==={json.dumps(ptype)}&&e.children.length<3);
          if(!opts.length) return 'nf'; __deap.clickEl(opts[opts.length-1]); return 'ok'}})()""")
        self.sess.b.wait(600)
        return r2


def route(sess, sub, args):
    ed = WfEditor(sess, args.agent, args.workflow)
    if sub == "list":
        return ok({"agent": args.agent, "workflow": args.workflow,
                   "nodes": ed.nodes(), "add_points": ed.add_buttons()})
    if sub == "insert":
        return ok(ed.insert_node(args.after, args.type))
    if sub == "delete":
        return ok(ed.delete_node(args.node))
    if sub == "param-add":
        return ok(ed.param_add(args.name, args.desc, not args.optional, args.type))
    if sub == "config":
        spec = json.loads(args.spec)
        t = spec.get("type")
        if t == "llm":
            ed.config_llm(args.node, model=spec.get("model"),
                          question_vars=spec.get("question_vars"),
                          prompt=spec.get("prompt"),
                          outputs=spec.get("outputs"),
                          json_mode=spec.get("json_mode"))
        elif t == "loop":
            ed.bind_loop(args.node, spec["array"])
        elif t == "record":
            ed.config_record(args.node, base=spec.get("base"),
                             table=spec.get("table"),
                             fields=spec.get("fields"), fixed=spec.get("fixed"))
        elif t == "end":
            ed.config_end(spec["pairs"])
        else:
            raise OpError("USAGE", f"未知节点类型 {t}（llm/loop/record/end）")
        return ok({"agent": args.agent, "workflow": args.workflow,
                   "node": args.node, "type": t, "configured": True})
    raise OpError("USAGE", f"未知 node 子命令 {sub}")
