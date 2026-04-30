1. 项目背景

本系统为：

课堂时空互动可视化分析平台（V2）

目标：

从树莓派采集真实课堂数据 → 本地分析 → 云端存储 → Web 可视化 → 长期趋势分析

当前状态：

Baseline V1 已跑通（禁止破坏）：
树莓派 → 本地 → 云端 → dashboard
2. 本轮目标（V2 第一阶段）

本轮只做三件事：

1. PostgreSQL 数据库接入（不移除 SQLite）
2. 用户系统（登录 + teacher/admin）
3. 教师数据 API（不做 Vue 页面）
4. 不可破坏约束（必须遵守）
   ❗ POST /api/interaction-results 不允许修改
   ❗ raw JSON 落盘必须保留
   ❗ SQLite fallback 必须保留
   ❗ dashboard_v11 必须继续可用
5. 系统架构（保持不变）
   树莓派（采集）
   → 本地（分析）
   → 云端（API + DB）
   → Web（展示）

本轮只允许修改：

cloud_backend/*
5. 数据库设计（PostgreSQL）
5.1 用户
id 串行主键用户
名文本唯一
password_hash文本
角色  CHECK（角色在（'teacher'，'admin'）
）created_at时间戳
5.2教室
编号序列号小学
5.3 场次
ID 串行主键
 analysis_id  文本唯一
classroom_id文本
created_at时间戳
duration_seconds整数
raw_json_path文本
5.4 analysis_results
ID 串行主键
 analysis_id文本
response_score 浮点数
点数 attention_score浮点
点数点数feedback_score浮点
点数created_at时间戳
6. 仓库设计

新增：

cloud_backend/postgres_repository.py

必须实现：

save_result（json）
get_recent（classroom_id， limit）
get_latest（classroom_id）
get_teacher_sessions（user_id)
7. API 设计
7.1 登录 API
POST /api/auth/login

请求：

{
 “用户名”： “xxx”，
 “密码”： “xxx”
}

返回：

{
 “token”：“...”，
“role”：“teacher”
}
7.2 当前用户
GET /api/auth/me
7.3 教师 API
GET /api/teacher/sessions
GET /api/teacher/sessions/{analysis_id}
GET /api/teacher/trends?limit=5
7.4 管理员 API
POST /api/admin/users
GET  /api/admin/users
8. 鉴权规则
teacher：只能访问自己 classroom
admin：全部权限
9. 环境变量

新增：

CLOUD_DB_BACKEND=sqlite/postgres
POSTGRES_URL=postgresql://user:pass@localhost:5432/db
JWT_SECRET=xxx
10. SSHFS / 操作员规则
Codex 不允许执行服务器命令
必须生成 scripts/*.sh 供 operator 手动执行
11. 验证要求（必须生成脚本）
scripts/validate_postgres.sh
scripts/validate_auth.sh
scripts/validate_teacher_api.sh
12. 输出要求

Codex 必须生成：

docs/project-status/v2-phase1-iteration-01.md

包含：

修改内容
未修改内容
验证方法
验证结果（未执行部分标明）
