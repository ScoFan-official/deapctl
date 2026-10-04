"""会话层: CDP 连接、专用 Chrome profile、login 引导、status 自检。"""
import json
import os
import subprocess
import sys
import time
import urllib.request

from .browser import B
from .envelope import OpError, ok

DEAP_URL = "https://deap.dingtalk.com"
DEFAULT_CDP = "http://127.0.0.1:9222"
DEFAULT_PORT = 9222

CHROME_CANDIDATES = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%USERPROFILE%\scoop\apps\googlechrome\current\chrome.exe"),
    "/usr/bin/google-chrome", "/usr/bin/chromium",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
]


def profile_dir():
    d = os.path.join(os.path.expanduser("~"), ".deapctl", "profile")
    os.makedirs(d, exist_ok=True)
    return d


def _cdp_alive(url=DEFAULT_CDP):
    try:
        with urllib.request.urlopen(url + "/json/version", timeout=3) as r:
            return json.loads(r.read().decode("utf-8", "ignore"))
    except Exception:
        return None


BROWSER_CANDIDATES = CHROME_CANDIDATES + [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    "/usr/bin/microsoft-edge", "/usr/bin/microsoft-edge-stable",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe"),
    "/usr/bin/brave-browser", "/usr/bin/brave",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    os.path.expandvars(r"%LOCALAPPDATA%\Chromium\Application\chrome.exe"),
    "/usr/bin/chromium-browser",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
]


def _find_in_registry():
    """Windows App Paths 兜底探测（覆盖非标准安装路径）。"""
    if os.name != "nt":
        return None
    import winreg
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for name in ("chrome.exe", "msedge.exe", "brave.exe", "chromium.exe"):
            try:
                with winreg.OpenKey(hive, rf"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{name}") as k:
                    p = winreg.QueryValue(k, None)
                    if p and os.path.exists(p):
                        return p
            except OSError:
                continue
    return None


def _find_playwright_chromium():
    """扫描 ms-playwright 缓存里的 bundled Chromium（不启动 driver，可嵌套调用）。"""
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH") or (
        os.path.expandvars(r"%LOCALAPPDATA%\\ms-playwright") if os.name == "nt" else
        os.path.expanduser("~/Library/Caches/ms-playwright") if sys.platform == "darwin" else
        os.path.expanduser("~/.cache/ms-playwright"))
    if not os.path.isdir(root):
        return None
    import glob
    for d in sorted(glob.glob(os.path.join(root, "chromium-[0-9]*")), reverse=True):
        for pat in ("**/chrome.exe" if os.name == "nt" else "**/chrome", "**/Chromium"):
            hits = [p for p in glob.glob(os.path.join(d, pat), recursive=True)
                    if os.path.isfile(p)]
            if hits:
                return hits[0]
    return None


def _resolve_browser(explicit=None):
    """浏览器解析：显式指定 > DEAPCTL_BROWSER env > 路径候选 > 注册表 > Playwright 兜底。"""
    if explicit and os.path.exists(explicit):
        return explicit
    env = os.environ.get("DEAPCTL_BROWSER")
    if env and os.path.exists(env):
        return env
    for p in BROWSER_CANDIDATES:
        if os.path.exists(p):
            return p
    return _find_in_registry() or _find_playwright_chromium()


def _find_chrome():
    return _resolve_browser()


def _find_deap_page(pw_browser):
    best = None
    for ctx in pw_browser.contexts:
        for pg in ctx.pages:
            if "deap.dingtalk.com" in pg.url:
                if "#/agent" in pg.url:
                    return pg
                best = best or pg
    return best


class Session:
    """已连接的 deap 页面。每个命令一个 Session，用完 close（不断浏览器）。"""

    def __init__(self, cdp_url=DEFAULT_CDP, auto_launch=False, browser=None):
        from playwright.sync_api import sync_playwright
        self._pw_ctx = sync_playwright().start()
        try:
            self._browser = self._pw_ctx.chromium.connect_over_cdp(cdp_url)
        except Exception:
            if not auto_launch:
                raise OpError("NOT_CONNECTED", f"无法连接 CDP {cdp_url}",
                              "先运行 deapctl login，或用 --cdp-url 指定调试端口")
            self._browser = self._launch(cdp_url, browser)
        self.page = _find_deap_page(self._browser)
        if self.page is None:
            try:
                ctx = self._browser.contexts[0]
                self.page = ctx.new_page()
                self.page.goto(DEAP_URL, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                raise OpError("NOT_CONNECTED", f"打开 DEAP 页面失败: {e}")
        self.page.set_viewport_size({"width": 1424, "height": 900})
        self.b = B(self.page)

    def _launch(self, cdp_url, browser=None):
        port = int(cdp_url.rsplit(":", 1)[-1].strip("/")) if ":" in cdp_url else DEFAULT_PORT
        exe = _resolve_browser(browser)
        if not exe:
            raise OpError("NO_CHROME", "找不到 Chromium 系浏览器",
                          "安装 Chrome/Edge、`playwright install chromium`，"
                          "或用 --browser / DEAPCTL_BROWSER 指定可执行文件")
        subprocess.Popen([exe, f"--remote-debugging-port={port}",
                          f"--user-data-dir={profile_dir()}", DEAP_URL,
                          "--no-first-run", "--disable-session-crashed-bubble"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(60):
            time.sleep(1)
            if _cdp_alive(cdp_url):
                try:
                    return self._pw_ctx.chromium.connect_over_cdp(cdp_url)
                except Exception:
                    continue
        raise OpError("TIMEOUT", "Chrome 启动超时")

    def ensure_login(self):
        t = self.b.text(6000)
        if "新建智能体" in t or "我的智能体" in t or "智能体" in t and "登录" not in t:
            return
        if "登录" in t or "扫码" in t or "dingtalk.com" not in self.page.url:
            raise OpError("NOT_LOGGED_IN", "DEAP 未登录",
                          "运行 deapctl login 并在弹出的 Chrome 里扫码/登录")

    def close(self):
        try:
            self._pw_ctx.stop()
        except Exception:
            pass


def cmd_login(cdp_url, timeout=240, browser=None):
    from playwright.sync_api import sync_playwright
    ver = _cdp_alive(cdp_url)
    if not ver:
        port = int(cdp_url.rsplit(":", 1)[-1].strip("/")) if ":" in cdp_url else DEFAULT_PORT
        exe = _resolve_browser(browser)
        if not exe:
            raise OpError("NO_CHROME", "找不到 Chromium 系浏览器",
                          "安装 Chrome/Edge、`playwright install chromium`，"
                          "或用 --browser / DEAPCTL_BROWSER 指定可执行文件")
        subprocess.Popen([exe, f"--remote-debugging-port={port}",
                          f"--user-data-dir={profile_dir()}", DEAP_URL,
                          "--no-first-run", "--disable-session-crashed-bubble"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(3)
        if not _cdp_alive(cdp_url):
            continue
        try:
            pw = sync_playwright().start()
            br = pw.chromium.connect_over_cdp(cdp_url)
            pg = _find_deap_page(br)
            if pg:
                t = pg.evaluate("()=>document.body.innerText||''")
                if ("新建智能体" in t or "智能体" in t) and "扫码" not in t:
                    pw.stop()
                    return ok({"profile": profile_dir(), "browser": ver or {"launched": True}},
                              "已登录 DEAP")
            pw.stop()
        except Exception:
            continue
    raise OpError("TIMEOUT", "等待登录超时", "在 Chrome 窗口中完成钉钉登录后重试")


def cmd_status(cdp_url):
    ver = _cdp_alive(cdp_url)
    if not ver:
        return {"ok": False, "code": "NOT_CONNECTED",
                "message": f"CDP {cdp_url} 不可达",
                "data": {"profile": profile_dir()},
                "hint": "deapctl login 启动专用浏览器"}
    s = Session(cdp_url)
    try:
        logged = "新建智能体" in s.b.text(6000) or "智能体" in s.b.text(6000)
        return ok({"cdp": ver.get("Browser", "connected"), "url": s.page.url,
                   "logged_in": bool(logged)})
    finally:
        s.close()
