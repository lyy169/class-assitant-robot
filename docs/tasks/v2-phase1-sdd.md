🧱 第一阶段 - 任务拆解
任务 1：PostgreSQL 基础接入
目标：
新增 PostgreSQLRepository，不替换 SQLite

输出：
cloud_backend/postgres_repository.py
剧本/setup_postgres.sh
剧本/validate_postgres.sh
任务 2：Repository 抽象增强
修改：
repository_interface.py

新增方法：
get_teacher_sessions
任务 3：用户系统（auth）
新增：
cloud_backend/auth.py
cloud_backend/security.py

实现：
login
JWT
password_hash
任务 4：管理员 API
新增：
/api/admin/users

支持：
创建 teacher
查询列表
任务 5：教师 API
新增：
/api/teacher/sessions
/api/teacher/trends
任务 6：数据库 schema 初始化脚本
scripts/setup_postgres_schema.sh
任务 7：验证脚本
scripts/validate_auth.sh
scripts/validate_teacher_api.sh
任务 8：文档输出
docs/project-status/v2-phase1-iteration-01.md