"""Stealth injection to make CF render Turnstile for automated Chrome.

CF withholds the interactive Turnstile widget when it detects automation.
We inject spoofing JS on every new document (before page scripts run) to
hide the common CDP/automation tells Turnstile fingerprints.
"""

import random
import nodriver as uc
import nodriver.cdp.page as cdp_page

# Realistic user-agents (Chrome on different OSes/browsers)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:129.0) Gecko/20100101 Firefox/129.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
]

# Realistic hardware fingerprints
SCREEN_RES = ["1920,1080", "1366,768", "1440,900", "1600,900", "2560,1440"]
DEVICE_MEM = ["2", "4", "8"]
HARDWARE_CONCURRENCY = ["2", "4", "8", "12", "16"]
TIMEZONES = ["America/New_York", "Europe/London", "Asia/Tokyo", "America/Los_Angeles",
             "Europe/Paris", "Australia/Sydney", "Asia/Singapore"]
LANGUAGES = [
    ["en-US", "en"],
    ["en-GB", "en"],
    ["en-AU", "en"],
    ["zh-CN", "zh", "en"],
    ["ja-JP", "ja", "en"],
    ["de-DE", "de", "en"],
    ["fr-FR", "fr", "en"],
]

# Realistic WebGL vendors (Intel, AMD, NVIDIA, Apple)
WEBGL_VENDORS = [
    ("Intel Inc.", "Intel Iris OpenGL Engine"),
    ("Intel Inc.", "Intel UHD Graphics 620"),
    ("Intel Inc.", "Intel HD Graphics 620"),
    ("NVIDIA Corporation", "NVIDIA GeForce GTX 1060/PCIe/SSE2"),
    ("NVIDIA Corporation", "NVIDIA GeForce RTX 3070/PCIe/SSE2"),
    ("AMD", "AMD Radeon Pro 5500M"),
    ("AMD", "AMD Radeon RX 580"),
    ("Apple Inc.", "Apple M1"),
    ("Apple Inc.", "Apple M2"),
]


def build_stealth_js(
    ua: str,
    screen_res: str,
    dev_mem: str,
    hw_conc: str,
    tz: str,
    langs: list,
    webgl_vendor: str,
    webgl_renderer: str,
) -> str:
    return f"""
(() => {{
  // navigator.webdriver -> undefined
  try {{ Object.defineProperty(Navigator.prototype, 'webdriver', {{get: () => undefined}}); }} catch (e) {{}}

  // chrome runtime stub
  try {{
    if (!window.chrome) window.chrome = {{}};
    if (!window.chrome.runtime) window.chrome.runtime = {{}};
    window.chrome.app = window.chrome.app || {{isInstalled: false}};
  }} catch (e) {{}}

  // permissions query
  try {{
    const orig = window.navigator.permissions.query.bind(window.navigator.permissions);
    window.navigator.permissions.query = (p) =>
      p && p.name === 'notifications'
        ? Promise.resolve({{state: Notification.permission}})
        : orig(p);
  }} catch (e) {{}}

  // plugins / mimeTypes non-empty
  try {{
    Object.defineProperty(navigator, 'plugins', {{get: () => [1, 2, 3, 4, 5]}});
    Object.defineProperty(navigator, 'mimeTypes', {{get: () => [1, 2, 3]}});
  }} catch (e) {{}}

  // languages
  try {{ Object.defineProperty(navigator, 'languages', {{get: () => {langs}}}); }} catch (e) {{}}

  // Timezone
  try {{ Object.defineProperty(Intl.DateTimeFormat, 'resolvedOptions', {{get: () => () => ({{timeZone: '{tz}'}})}}); }} catch (e) {{}}

  // WebGL vendor/renderer spoof
  try {{
    const gp = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function (p) {{
      if (p === 37445) return '{webgl_vendor}';
      if (p === 37446) return '{webgl_renderer}';
      return gp.call(this, p);
    }};
    // Also patch WebGL2
    const gp2 = WebGL2RenderingContext && WebGL2RenderingContext.prototype.getParameter;
    if (gp2) {{
      WebGL2RenderingContext.prototype.getParameter = function (p) {{
        if (p === 37445) return '{webgl_vendor}';
        if (p === 37446) return '{webgl_renderer}';
        return gp2.call(this, p);
      }};
    }}
  }} catch (e) {{}}

  // hardwareConcurrency
  try {{ Object.defineProperty(navigator, 'hardwareConcurrency', {{get: () => {hw_conc}}}); }} catch (e) {{}}

  // deviceMemory
  try {{ Object.defineProperty(navigator, 'deviceMemory', {{get: () => {dev_mem}}}); }} catch (e) {{}}

  // screen resolution
  try {{ Object.defineProperty(screen, 'availWidth', {{get: () => {screen_res.split(',')[0]}}}); }} catch (e) {{}}
  try {{ Object.defineProperty(screen, 'availHeight', {{get: () => {screen_res.split(',')[1]}}}); }} catch (e) {{}}
  try {{ Object.defineProperty(screen, 'width', {{get: () => {screen_res.split(',')[0]}}}); }} catch (e) {{}}
  try {{ Object.defineProperty(screen, 'height', {{get: () => {screen_res.split(',')[1]}}}); }} catch (e) {{}}
}})();
"""


def random_stealth_js() -> str:
    return build_stealth_js(
        ua=random.choice(USER_AGENTS),
        screen_res=random.choice(SCREEN_RES),
        dev_mem=random.choice(DEVICE_MEM),
        hw_conc=random.choice(HARDWARE_CONCURRENCY),
        tz=random.choice(TIMEZONES),
        langs=random.choice(LANGUAGES),
        webgl_vendor=random.choice(WEBGL_VENDORS)[0],
        webgl_renderer=random.choice(WEBGL_VENDORS)[1],
    )


async def apply_stealth(page: uc.Tab) -> None:
    """Register random stealth JS to run on every new document for this tab."""
    try:
        await page.send(cdp_page.enable())
    except Exception:
        pass
    try:
        await page.send(
            cdp_page.add_script_to_evaluate_on_new_document(source=random_stealth_js())
        )
    except Exception:
        pass


STEALTH_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-first-run",
    "--no-default-browser-check",
    "--disable-features=IsolateOrigins,site-per-process",
    "--exclude-switches=enable-automation",
]
