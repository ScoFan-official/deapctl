"""浏览器操作工具层: 穿透 Shadow DOM 的查询、dispatch 点击、受控输入填充、抽屉/弹窗处理。

所有定位优先用语义（文本/角色/placeholder/结构），坐标仅兜底。
实测要点已编码：React 受控输入须 native setter+事件；图标按钮靠 tooltip 辨别；
变量面板/文档选择器等弹层按容器内相对定位。
"""
import json

DOM_JS = r"""
window.__deap = {
  vis(e){ if(!e) return false; const r=e.getBoundingClientRect(); if(r.width<2||r.height<2) return false;
          const cs=getComputedStyle(e); return cs.visibility!=='hidden'&&cs.display!=='none'; },
  deepAll(sel, root){ const out=[]; (function rec(r){ r.querySelectorAll(sel).forEach(e=>out.push(e));
          r.querySelectorAll('*').forEach(e=>{if(e.shadowRoot) rec(e.shadowRoot)}); })(root||document); return out; },
  deepVisible(sel){ return this.deepAll(sel).filter(e=>this.vis(e)); },
  // 最深命中：innerText 命中且没有更深层可见子元素也命中同一文本
  byText(txt, exact){
          const all=this.deepAll('*').filter(e=>this.vis(e));
          const hit=e=>{const t=(e.innerText||'').trim(); return t&&(exact?t===txt:t.includes(txt))};
          const hits=all.filter(hit);
          return hits.filter(e=>!hits.find(c=>c!==e&&e.contains(c))); },
  rect(e){ const b=e.getBoundingClientRect(); return [b.x+b.width/2, b.y+b.height/2, b.width, b.height]; },
  clickEl(e){ const [cx,cy]=this.rect(e);
          ['mouseover','mousemove','mousedown','mouseup','click'].forEach(t=>e.dispatchEvent(
            new MouseEvent(t,{bubbles:true,cancelable:true,view:window,clientX:cx,clientY:cy,button:0}))); },
  // React 受控输入：native setter + input/change + blur
  fillIn(e, val){ const tag=e.tagName;
          if(tag==='INPUT'||tag==='TEXTAREA'){
            const proto=tag==='INPUT'?HTMLInputElement.prototype:HTMLTextAreaElement.prototype;
            const d=Object.getOwnPropertyDescriptor(proto,'value');
            e.focus(); d.set.call(e,val);
            e.dispatchEvent(new Event('input',{bubbles:true}));
            e.dispatchEvent(new Event('change',{bubbles:true}));
          } else { e.focus(); e.innerText=val; e.dispatchEvent(new InputEvent('input',{bubbles:true,inputType:'insertText',data:val})); }
          e.dispatchEvent(new FocusEvent('blur',{bubbles:true})); },
  // 可见弹层（modal/drawer），按容器内相对定位用
  layers(){ const sels=['.dtd-modal','.dtd-drawer','[class*=dtd-modal]','[class*=drawer]','[role=dialog]','.dtd-select-dropdown','[class*=dropdown]','[class*=popover]','[class*=tooltip]'];
          const seen=new Set(); const out=[];
          for(const s of sels){ for(const e of this.deepAll(s)){ if(this.vis(e)&&!seen.has(e)){seen.add(e);out.push(e)} } }
          return out; },
  topText(){ return (document.body.innerText||'').slice(0,4000); },
  chips(host){ return [...host.querySelectorAll('*')].filter(e=>e.children.length===0&&(e.innerText||'').trim()).map(e=>(e.innerText||'').trim()); }
};
'ok'
"""


def install(page):
    page.evaluate(DOM_JS)


class B:
    """绑定一个已连接的 deap 页面的操作面。"""

    def __init__(self, page):
        self.page = page
        install(page)

    def ev(self, js):
        return self.page.evaluate(js)

    def text(self, limit=4000):
        return self.ev("(window.__deap?__deap.topText():document.body.innerText||'').slice(0,%d)" % limit)

    def url(self):
        return self.page.url

    def click_xy(self, x, y):
        self.page.mouse.click(float(x), float(y))

    def confirm_modal(self, labels=None):
        """点掉顶层弹窗的肯定按钮（取消之外的动作）。返回被点按钮文本，无命中返回 None。

        labels 覆盖 DEAP 弹窗的肯定按钮文案全集；'确定删除' 等复合文案也在内。
        扫描 layers() 倒序取最顶层——同文档多次确认会堆叠同名 modal 实例。
        """
        labs = json.dumps(list(labels) if labels else
                          ["确定删除", "确定", "删除", "确认", "移除", "完成", "添加", "是"])
        return self.ev(f"""(()=>{{const labs={labs};
          const ms=__deap.layers().filter(m=>[...m.querySelectorAll('button')].some(b=>__deap.vis(b)));
          for(let i=ms.length-1;i>=0;i--){{
            const btn=[...ms[i].querySelectorAll('button')].find(e=>__deap.vis(e)&&labs.includes((e.innerText||'').trim()));
            if(btn){{__deap.clickEl(btn);return (btn.innerText||'').trim();}}}}
          return null}})()""")

    def click_el_js(self, js_el):
        """js_el 是返回 Element 的表达式。"""
        return self.ev(f"(()=>{{const e={js_el}; if(!e||!__deap.vis(e)) return null; __deap.clickEl(e); return __deap.rect(e);}})()")

    def click_text(self, txt, exact=True, index=0):
        js = f"__deap.byText({txt!r},{'true' if exact else 'false'})[{index}]"
        return self.click_el_js(js)

    def wait(self, ms):
        self.page.wait_for_timeout(ms)

    def wait_text(self, txt, timeout=15000, interval=500):
        import time
        t0 = time.time()
        while time.time() - t0 < timeout / 1000:
            if txt in self.text():
                return True
            self.wait(interval)
        return False

    def has_text(self, txt):
        return txt in self.text(8000)

    def screenshot(self, path):
        self.page.screenshot(path=path, full_page=False)

    def scroll_el(self, js_el, dy):
        self.ev(f"(()=>{{const e={js_el}; if(e) e.scrollTop+={dy};}})()")

    def key(self, k):
        self.page.keyboard.press(k)

    def type(self, text, delay=2):
        self.page.keyboard.type(text, delay=delay)
