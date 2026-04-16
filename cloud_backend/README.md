# 课堂交互分析系统云端接收服务

## 目标

该服务负责接收本地高性能电脑推送的 20 秒课堂交互统计 JSON，并进行：
- 基本校验
- 日志记录
- 原始结果落盘
- 为后续数据库入库与仪表盘接口预留扩展点

## 推荐目录

```text
/root/video_project/
├─ app.py
├─ deploy.sh
├─ cloud_backend/
│  ├─ main.py
│  ├─ config.py
│  ├─ schemas.py
│  ├─ storage.py
│  ├─ requirements.txt
│  ├─ .env.example
│  └─ data/
│     └─ raw/
└─ scripts/
   ├─ deploy_cloud_backend.sh
   └─ test_cloud_backend.sh
```

## 启动命令

```bash
cd /root/video_project
source /root/venv/bin/activate
pip install -r cloud_backend/requirements.txt
uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8010
```

## systemd 建议

服务名建议：`classroom-cloud-backend.service`

启动命令建议：

```bash
/root/venv/bin/uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8010
```

工作目录建议：

```bash
/root/video_project
```

## 数据库存储建议

当前版本先采用 JSON 文件落盘，确保本地端可以立即推送成功。

后续迁移数据库时建议：
- PostgreSQL：适合做教室维度聚合、时间序列统计、仪表盘查询
- MongoDB：适合先快速存储结构灵活的原始 JSON

如果毕业设计后续重点是聚合统计与查询，优先建议 PostgreSQL。
