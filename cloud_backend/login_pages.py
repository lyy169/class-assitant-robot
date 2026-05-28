"""Login and permission pages for Phase 3.1 polished UI."""
from __future__ import annotations

from .ui_style import PHASE31_STYLE


def build_login_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>智能课堂行为分析与教学反馈平台</title>
  {PHASE31_STYLE}
  <style>
    body {{ min-height: 100vh; display: grid; place-items: center; padding: 26px 0; }}
    .login-shell {{ width: min(1180px, calc(100% - 40px)); display: grid; grid-template-columns: minmax(420px, .92fr) minmax(520px, 1.08fr); gap: 24px; align-items: stretch; }}
    .login-panel {{ background: rgba(255,255,255,.98); border: 1px solid var(--color-border); border-radius: 24px; padding: 34px; box-shadow: var(--shadow); }}
    .login-panel h1 {{ font-size: clamp(34px, 4.6vw, 52px); line-height: 1.08; margin: 12px 0; }}
    .login-panel input {{ width: 100%; }}
    .login-panel button {{ width: 100%; margin-top: 12px; }}
    .login-demo-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
    .login-product-card {{ min-height: 640px; align-content: center; }}
    .login-visual-panel {{
      min-height: 640px;
      background:
        linear-gradient(135deg, rgba(15,42,61,.20), rgba(37,99,235,.32)),
        radial-gradient(circle at 18% 20%, rgba(20,184,166,.34), transparent 28%),
        radial-gradient(circle at 76% 18%, rgba(37,99,235,.26), transparent 30%),
        url('/static/login-education-visual.png'),
        linear-gradient(135deg, #0F2A3D 0%, #174F59 45%, #2563EB 100%);
      background-size: cover, auto, auto, cover, cover;
      background-position: center;
    }}
    .login-visual-panel::before {{
      content: "";
      position: absolute;
      inset: 0;
      z-index: 1;
      background:
        linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,.7), transparent 82%);
    }}
    .visual-title-on-image {{
      position: absolute;
      z-index: 2;
      left: 36px;
      top: 42px;
      max-width: 500px;
      color: #F8FAFC;
      text-shadow: 0 2px 14px rgba(0,0,0,.28);
    }}
    .visual-title-on-image .kicker {{ color: #BFF7E3; }}
    .visual-title-on-image h2 {{ color: #FFFFFF; font-size: 34px; line-height: 1.18; margin: 12px 0; }}
    .visual-title-on-image p {{ color: rgba(248,250,252,.9); font-size: 15px; line-height: 1.75; }}
    @media (max-width: 920px) {{ .login-shell {{ grid-template-columns: 1fr; }} .login-demo-row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="login-shell" data-marker="phase29-login-page">
    <section class="login-panel login-product-card">
      <p class="kicker">智能课堂云端平台</p>
      <h1>欢迎登录</h1>
      <p class="muted">教师端 / 管理员端统一入口</p>
      <p class="error" id="error"></p>
      <form id="login-form">
        <label for="username">用户名</label>
        <input id="username" name="username" autocomplete="username" required />
        <label for="password">密码</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required />
        <button type="submit">登录</button>
      </form>
      <div class="login-demo-row">
        <button class="secondary" data-demo-user="teacher" data-demo-password="teacher123">教师演示登录</button>
        <button class="secondary" data-demo-user="admin" data-demo-password="admin123">管理员演示登录</button>
      </div>
      <p class="muted" style="margin-top:18px">还没有账号？<a href="/register">注册教师账号</a></p>
    </section>
    <section class="login-visual-panel" aria-label="教育数据平台视觉区">
      <div class="visual-title-on-image">
        <p class="kicker">Teaching Analytics</p>
        <h2>从课堂证据到教学行动</h2>
        <p>树莓派采集、本地分析与云端反馈形成可解释的课堂数据闭环，让课堂录像、行为曲线和教学建议在同一处完成复盘。</p>
      </div>
    </section>
  </main>
  <script>
    async function login(username, password) {{
      document.getElementById("error").textContent = "";
      const response = await fetch("/api/auth/login", {{
        method: "POST",
        headers: {{"Content-Type": "application/json"}},
        body: JSON.stringify({{username, password}})
      }});
      const payload = await response.json().catch(() => ({{}}));
      if (!response.ok || payload.success !== true) {{
        throw new Error(payload.message || payload.detail || "登录失败，请检查账号或密码。");
      }}
      window.location.href = payload.redirect_to || "/";
    }}
    document.getElementById("login-form").addEventListener("submit", async (event) => {{
      event.preventDefault();
      try {{
        const form = new FormData(event.target);
        await login(form.get("username"), form.get("password"));
      }} catch (error) {{
        document.getElementById("error").textContent = String(error.message || error);
      }}
    }});
    document.querySelectorAll("[data-demo-user]").forEach((button) => {{
      button.addEventListener("click", async () => {{
        try {{
          await login(button.dataset.demoUser, button.dataset.demoPassword);
        }} catch (error) {{
          document.getElementById("error").textContent = String(error.message || error);
        }}
      }});
    }});
  </script>
</body>
</html>"""


def build_register_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>注册教师账号</title>
  {PHASE31_STYLE}
  <style>
    body {{ min-height: 100vh; display: grid; place-items: center; padding: 26px 0; }}
    .login-shell {{ width: min(1180px, calc(100% - 40px)); display: grid; grid-template-columns: minmax(420px, .92fr) minmax(520px, 1.08fr); gap: 24px; align-items: stretch; }}
    .login-panel {{ background: rgba(255,255,255,.98); border: 1px solid var(--color-border); border-radius: 24px; padding: 34px; box-shadow: var(--shadow); }}
    .login-panel h1 {{ font-size: clamp(34px, 4.6vw, 52px); line-height: 1.08; margin: 12px 0; }}
    .login-panel input {{ width: 100%; }}
    .login-panel button {{ width: 100%; margin-top: 12px; }}
    .login-product-card {{ min-height: 640px; align-content: center; }}
    .code-row {{ display: grid; grid-template-columns: minmax(0, 1fr) 150px; gap: 10px; align-items: end; }}
    .code-row button {{ margin-top: 0; }}
    .rule-list {{ margin: 10px 0 0; padding-left: 18px; color: #64748b; font-size: 13px; line-height: 1.7; }}
    .success {{ color: #047857; font-weight: 800; }}
    .login-visual-panel {{
      min-height: 640px;
      background:
        linear-gradient(135deg, rgba(15,42,61,.20), rgba(37,99,235,.32)),
        radial-gradient(circle at 18% 20%, rgba(20,184,166,.34), transparent 28%),
        radial-gradient(circle at 76% 18%, rgba(37,99,235,.26), transparent 30%),
        url('/static/login-education-visual.png'),
        linear-gradient(135deg, #0F2A3D 0%, #174F59 45%, #2563EB 100%);
      background-size: cover, auto, auto, cover, cover;
      background-position: center;
    }}
    .login-visual-panel::before {{
      content: "";
      position: absolute;
      inset: 0;
      z-index: 1;
      background:
        linear-gradient(rgba(255,255,255,.08) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
      background-size: 42px 42px;
      mask-image: linear-gradient(180deg, rgba(0,0,0,.7), transparent 82%);
    }}
    .visual-title-on-image {{
      position: absolute;
      z-index: 2;
      left: 36px;
      top: 42px;
      max-width: 500px;
      color: #F8FAFC;
      text-shadow: 0 2px 14px rgba(0,0,0,.28);
    }}
    .visual-title-on-image .kicker {{ color: #BFF7E3; }}
    .visual-title-on-image h2 {{ color: #FFFFFF; font-size: 34px; line-height: 1.18; margin: 12px 0; }}
    .visual-title-on-image p {{ color: rgba(248,250,252,.9); font-size: 15px; line-height: 1.75; }}
    @media (max-width: 920px) {{ .login-shell {{ grid-template-columns: 1fr; }} .code-row {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
  <main class="login-shell" data-marker="db-backed-register-page">
    <section class="login-panel login-product-card">
      <p class="kicker">智能课堂云端平台</p>
      <h1>注册教师账号</h1>
      <p class="muted">注册成功后会返回登录页。公开注册仅创建教师账号，管理员账号仍由管理员后台创建。</p>
      <p class="error" id="error"></p>
      <p class="success" id="success"></p>
      <form id="register-form">
        <label for="username">用户名</label>
        <input id="username" name="username" autocomplete="username" minlength="3" maxlength="64" placeholder="3-64 位，字母/数字/_-.@" required />
        <label for="email">QQ 邮箱</label>
        <div class="code-row">
          <input id="email" name="email" type="email" autocomplete="email" placeholder="example@qq.com" required />
          <button class="secondary" id="send-code" type="button">发送验证码</button>
        </div>
        <label for="verification_code">邮箱验证码</label>
        <input id="verification_code" name="verification_code" inputmode="numeric" maxlength="6" placeholder="6 位验证码" required />
        <label for="display_name">显示名称</label>
        <input id="display_name" name="display_name" maxlength="80" placeholder="可选" />
        <label for="password">密码</label>
        <input id="password" name="password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required />
        <label for="confirm_password">确认密码</label>
        <input id="confirm_password" name="confirm_password" type="password" autocomplete="new-password" minlength="8" maxlength="128" required />
        <label for="classroom_id">绑定班级 ID</label>
        <input id="classroom_id" name="classroom_id" maxlength="80" placeholder="例如 classroom_101，可选" />
        <label for="classroom_name">班级名称</label>
        <input id="classroom_name" name="classroom_name" maxlength="120" placeholder="可选，默认等于班级 ID" />
        <ul class="rule-list">
          <li>用户名只允许字母、数字、下划线、短横线、点和 @。</li>
          <li>密码至少 8 位，且必须同时包含字母和数字。</li>
          <li>当前仅支持 QQ 邮箱验证码注册。</li>
        </ul>
        <button type="submit">注册账号</button>
      </form>
      <p class="muted" style="margin-top:18px">已有账号？<a href="/login">返回登录</a></p>
    </section>
    <section class="login-visual-panel" aria-label="教育数据平台视觉区">
      <div class="visual-title-on-image">
        <p class="kicker">Teaching Analytics</p>
        <h2>从课堂证据到教学行动</h2>
        <p>树莓派采集、本地分析与云端反馈形成可解释的课堂数据闭环，让课堂录像、行为曲线和教学建议在同一处完成复盘。</p>
      </div>
    </section>
  </main>
  <script>
    const errorEl = document.getElementById("error");
    const successEl = document.getElementById("success");
    const sendCodeButton = document.getElementById("send-code");
    function setMessage(type, message) {{
      errorEl.textContent = type === "error" ? message : "";
      successEl.textContent = type === "success" ? message : "";
    }}
    function validatePassword(password, confirmPassword) {{
      if (password !== confirmPassword) throw new Error("两次输入的密码不一致。");
      if (password.length < 8) throw new Error("密码至少需要 8 位。");
      if (!/[A-Za-z]/.test(password) || !/[0-9]/.test(password)) throw new Error("密码必须同时包含字母和数字。");
    }}
    sendCodeButton.addEventListener("click", async () => {{
      const email = document.getElementById("email").value.trim();
      setMessage("", "");
      if (!/^[A-Za-z0-9._-]+@qq\\.com$/.test(email)) {{
        setMessage("error", "请输入有效的 QQ 邮箱。");
        return;
      }}
      sendCodeButton.disabled = true;
      const oldText = sendCodeButton.textContent;
      sendCodeButton.textContent = "发送中...";
      try {{
        const response = await fetch("/api/auth/send-register-code", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify({{email}})
        }});
        const data = await response.json().catch(() => ({{}}));
        if (!response.ok || data.success !== true) {{
          throw new Error(data.detail || data.message || "验证码发送失败，请稍后重试。");
        }}
        setMessage("success", "验证码已发送，请查收 QQ 邮箱。");
        let seconds = 60;
        sendCodeButton.textContent = "已发送";
        const timer = setInterval(() => {{
          seconds -= 1;
          sendCodeButton.textContent = `已发送 ${{seconds}}s`;
          if (seconds <= 0) {{
            clearInterval(timer);
            sendCodeButton.disabled = false;
            sendCodeButton.textContent = "重新发送";
          }}
        }}, 1000);
      }} catch (error) {{
        sendCodeButton.disabled = false;
        sendCodeButton.textContent = oldText;
        setMessage("error", String(error.message || error));
      }}
    }});
    document.getElementById("register-form").addEventListener("submit", async (event) => {{
      event.preventDefault();
      setMessage("", "");
      const form = new FormData(event.target);
      const password = String(form.get("password") || "");
      const confirmPassword = String(form.get("confirm_password") || "");
      const payload = {{
        username: form.get("username"),
        email: form.get("email"),
        display_name: form.get("display_name"),
        password,
        confirm_password: confirmPassword,
        verification_code: form.get("verification_code"),
        classroom_id: form.get("classroom_id"),
        classroom_name: form.get("classroom_name")
      }};
      try {{
        validatePassword(password, confirmPassword);
        const response = await fetch("/api/auth/register", {{
          method: "POST",
          headers: {{"Content-Type": "application/json"}},
          body: JSON.stringify(payload)
        }});
        const data = await response.json().catch(() => ({{}}));
        if (!response.ok || data.success !== true) {{
          throw new Error(data.message || data.detail || "注册失败，请检查用户名是否已存在。");
        }}
        setMessage("success", "注册成功，即将返回登录页。");
        window.setTimeout(() => {{ window.location.href = data.redirect_to || "/login"; }}, 900);
      }} catch (error) {{
        setMessage("error", String(error.message || error));
      }}
    }});
  </script>
</body>
</html>"""


def build_forbidden_html() -> str:
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>无权限访问</title>{PHASE31_STYLE}</head>
<body><main class="page"><section class="card" data-marker="phase29-forbidden-page"><h1>没有权限访问该页面</h1><p class="muted">当前账号没有访问该控制台或课堂数据的权限，请返回首页或切换账号。</p><a class="button" href="/">返回首页</a></section></main></body>
</html>"""
