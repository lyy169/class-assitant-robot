"""Login and permission pages for Phase 2.9."""
from __future__ import annotations


def build_login_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Login - Intelligent Classroom Platform</title>
  <style>
    body { margin: 0; min-height: 100vh; font-family: "Segoe UI", Arial, sans-serif; background: radial-gradient(circle at top left, #dbeafe, #f8fafc 42%, #e0f2fe); color: #172033; display: grid; place-items: center; }
    .shell { width: min(1040px, calc(100% - 36px)); display: grid; grid-template-columns: minmax(0, 1.08fr) minmax(320px, .92fr); gap: 22px; align-items: stretch; }
    .hero, .panel { border-radius: 28px; padding: 28px; box-shadow: 0 24px 60px rgba(15, 23, 42, .14); }
    .hero { background: linear-gradient(135deg, #0f172a, #1d4ed8); color: #fff; }
    .hero .muted { color: #dbeafe; }
    .pipeline { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 20px; }
    .pipeline span { background: rgba(255,255,255,.14); border-radius: 999px; padding: 8px 12px; font-weight: 800; }
    .panel { background: rgba(255,255,255,.96); border: 1px solid #dbe7ff; }
    label { display: block; margin: 14px 0 6px; color: #64748b; font-weight: 700; }
    input { width: 100%; box-sizing: border-box; border: 1px solid #cbd5e1; border-radius: 13px; padding: 12px; font-size: 16px; }
    button { width: 100%; border: 0; border-radius: 13px; margin-top: 14px; padding: 12px 14px; font-weight: 900; cursor: pointer; background: #165dff; color: #fff; }
    button.secondary { background: #eef2f7; color: #172033; }
    .error { min-height: 22px; color: #b91c1c; font-weight: 800; }
    .kicker { letter-spacing: .08em; text-transform: uppercase; font-size: 12px; font-weight: 900; color: #bfdbfe; }
    @media (max-width: 820px) { .shell { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <main class="shell" data-marker="phase29-login-page">
    <section class="hero">
      <p class="kicker">Unified Login</p>
      <h1>智能课堂行为分析与教学反馈平台</h1>
      <p class="muted">Use one role-aware entry point for teacher review, admin overview, and classroom analysis dashboards.</p>
      <div class="pipeline"><span>树莓派采集</span><span>-></span><span>本地分析</span><span>-></span><span>云端反馈</span></div>
    </section>
    <section class="panel">
      <h2>Sign in</h2>
      <p class="error" id="error"></p>
      <form id="login-form">
        <label for="username">Username</label>
        <input id="username" name="username" autocomplete="username" required />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required />
        <button type="submit">Login</button>
      </form>
      <button class="secondary" data-demo-user="teacher" data-demo-password="teacher123">Teacher Demo Login</button>
      <button class="secondary" data-demo-user="admin" data-demo-password="admin123">Admin Demo Login</button>
    </section>
  </main>
  <script>
    async function login(username, password) {
      document.getElementById("error").textContent = "";
      const response = await fetch("/api/auth/login", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({username, password})
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok || payload.success !== true) {
        throw new Error(payload.message || payload.detail || "Login failed");
      }
      window.location.href = payload.redirect_to || "/";
    }
    document.getElementById("login-form").addEventListener("submit", async (event) => {
      event.preventDefault();
      try {
        const form = new FormData(event.target);
        await login(form.get("username"), form.get("password"));
      } catch (error) {
        document.getElementById("error").textContent = String(error.message || error);
      }
    });
    document.querySelectorAll("[data-demo-user]").forEach((button) => {
      button.addEventListener("click", async () => {
        try {
          await login(button.dataset.demoUser, button.dataset.demoPassword);
        } catch (error) {
          document.getElementById("error").textContent = String(error.message || error);
        }
      });
    });
  </script>
</body>
</html>"""


def build_forbidden_html() -> str:
    return """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8" /><meta name="viewport" content="width=device-width, initial-scale=1" /><title>403 Forbidden</title>
<style>body{font-family:"Segoe UI",Arial,sans-serif;background:#f8fafc;color:#172033;display:grid;place-items:center;min-height:100vh;margin:0}.card{max-width:560px;background:#fff;border:1px solid #e5e7eb;border-radius:22px;padding:28px;box-shadow:0 18px 42px rgba(15,23,42,.12)}a{display:inline-block;margin-top:12px;background:#165dff;color:#fff;text-decoration:none;border-radius:12px;padding:10px 14px;font-weight:800}</style></head>
<body><main class="card" data-marker="phase29-forbidden-page"><h1>没有权限访问该页面</h1><p>当前账号没有访问该控制台或课堂数据的权限。</p><a href="/">返回首页</a></main></body>
</html>"""
