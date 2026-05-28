# 云端真实上传联调 runbook V1

本文用于指导“真实本地端 JSON 成功上传到云端、成功写入 raw、成功被查询与 dashboard 读取”的最小联调验证。

当前目标不是扩功能，而是证明这条真实链路已经打通：

本地端输出 V1.1 JSON  
-> 云端 `POST /api/interaction-results`  
-> 写入 raw 文件  
-> `GET /api/recent-interaction-results` 可查到  
-> `/dashboard` 可看到真实 `analysis_id`

## 1. 正式接口

当前正式上传接口：

```text
POST /api/interaction-results
```

当前源码主入口：

- `/root/video_project_src/cloud_backend/main.py`

按当前源码与 runbook 约定，源码目录联调时通常使用：

```text
http://<host>:8011/api/interaction-results
```

如果你是在运行目录已托管服务上联调，则可能是：

```text
http://<host>:8010/api/interaction-results
```

实际以你启动服务时的端口为准。

## 2. 本地端上传命令示例

### 2.1 直接用 curl 上传

把 `<SERVER_IP>` 替换成云服务器地址，把 `<API_KEY>` 替换成真实值。如果当前服务未要求 API key，可去掉 `X-API-Key` 头。

```bash
curl -X POST "http://<SERVER_IP>:8011/api/interaction-results" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  -d '{
    "schema_version": "v1.1",
    "analysis_id": "cls_20260418_101_001",
    "classroom_id": "classroom_101",
    "video_id": "video_20260418_001",
    "source": {
      "source_kind": "captured_video",
      "source_path": "captures/classroom_101/lesson_20260418.mp4",
      "source_host": "raspberrypi-01"
    },
    "time": {
      "recorded_at": "2026-04-18T09:00:00Z",
      "generated_at": "2026-04-18T10:12:30Z",
      "duration_seconds": 2700
    },
    "summary": {
      "feedback_score": 78,
      "attention_score": 74,
      "response_score": 82,
      "teacher_question_count": 8,
      "avg_attention_ratio": 0.76,
      "response_success_rate": 0.75,
      "summary_text": "中段注意力下降明显，提问后响应较积极。"
    },
    "teacher": {
      "question_events": [
        {
          "event_id": "q_001",
          "start_sec": 320,
          "end_sec": 326,
          "text": "谁来回答一下这个问题？",
          "question_type": "open_question"
        }
      ],
      "stage_distribution": {
        "exposition_ratio": 0.62,
        "question_ratio": 0.12,
        "discussion_ratio": 0.09,
        "summary_ratio": 0.07,
        "management_ratio": 0.10
      }
    },
    "students": {
      "estimated_student_count": 36,
      "hand_raise_event_count": 5,
      "zones": {
        "front": {
          "avg_attention_ratio": 0.83,
          "active_ratio": 0.41
        },
        "middle": {
          "avg_attention_ratio": 0.75,
          "active_ratio": 0.32
        },
        "back": {
          "avg_attention_ratio": 0.61,
          "active_ratio": 0.19
        }
      }
    },
    "timeline": {
      "window_size_seconds": 60,
      "attention_curve": [0.82, 0.79, 0.77, 0.74, 0.69],
      "heat_curve": [0.30, 0.28, 0.35, 0.62, 0.81],
      "activity_curve": [0.24, 0.26, 0.29, 0.45, 0.51]
    }
  }'
```

### 2.2 若本地端已有 JSON 文件

假设本地端已经把真实结果写成 `result.json`：

```bash
curl -X POST "http://<SERVER_IP>:8011/api/interaction-results" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: <API_KEY>" \
  --data-binary @result.json
```

### 2.3 上传后立即查询

```bash
curl "http://<SERVER_IP>:8011/api/recent-interaction-results?classroom_id=classroom_101"
```

```bash
curl "http://<SERVER_IP>:8011/api/latest-interaction-result?classroom_id=classroom_101"
```

浏览器打开：

```text
http://<SERVER_IP>:8011/dashboard?classroom_id=classroom_101
```

## 3. 成功判定标准

这轮联调成功，必须同时满足以下条件：

### 3.1 接口返回成功

- `POST /api/interaction-results` 返回 `200`
- 返回体中 `success=true`
- 返回体中有 `saved_path`

### 3.2 raw 文件真实写入

服务端必须出现真实文件：

```text
cloud_backend/data/raw/YYYY-MM-DD/<analysis_id>.json
```

例如：

```text
/root/video_project_src/cloud_backend/data/raw/2026-04-18/cls_20260418_101_001.json
```

### 3.3 recent 接口能查到真实结果

调用：

```text
GET /api/recent-interaction-results?classroom_id=classroom_101
```

应至少满足：

- `results[0].result.analysis_id` 等于本次真实上传的 `analysis_id`
- `results[0].source_kind` 为 `raw`，而不是 `sample`

### 3.4 dashboard 可看到真实 analysis_id

打开：

```text
/dashboard?classroom_id=classroom_101
```

至少要确认：

- 页面中的 recent 列表能看到本次 `analysis_id`
- 页面展示使用的是 raw 结果，而不是 sample fallback

## 4. 排障步骤

### 4.1 端口监听

先确认云端服务真的启动了：

```bash
ss -lntp | grep 8011
```

如果你验证的是运行目录服务，则检查 8010。

### 4.2 防火墙

如果本机 `curl 127.0.0.1:<port>` 能通，但浏览器打不开：

- 检查阿里云安全组是否放行对应端口
- 检查服务器本机 `ufw` / `iptables`

例如：

```bash
ufw status
```

如果缺少规则，例如 8011，需要放行：

```bash
ufw allow 8011/tcp
```

### 4.3 schema 校验失败

如果上传返回 4xx，优先检查：

- `schema_version` 是否为 `v1.1`
- 是否缺少必填字段
- `teacher.question_events` 的 `end_sec` 是否小于 `start_sec`
- `attention_curve / heat_curve / activity_curve` 长度是否一致
- 比例字段是否用了 `0-1`
- 评分字段是否用了 `0-100`

当前正式 schema 在：

```text
/root/video_project_src/cloud_backend/schemas_v11.py
```

### 4.4 文件权限

如果接口返回成功前就失败，或服务日志显示写文件失败，检查：

- `cloud_backend/data/raw/` 是否存在
- 服务进程用户对该目录是否有写权限

目录由服务启动时的 `settings.ensure_directories()` 保证存在，但权限仍需正确。

### 4.5 sample / fallback 混淆

这是当前最常见的误判来源。

如果 recent 或 dashboard 还能显示内容，不代表真实上传已经成功，因为当前有 sample fallback。

必须明确检查：

- `GET /api/recent-interaction-results` 中 `results[0].source_kind`
- 是否为 `raw`
- 是否出现真实 `analysis_id`

只有看到 `raw + analysis_id 命中`，才能算真实上传验通。

## 5. 建议的最小联调顺序

### 步骤 1：先启动源码目录服务

```bash
cd /root/video_project_src
source /root/venv/bin/activate
uvicorn cloud_backend.main:app --host 0.0.0.0 --port 8011
```

### 步骤 2：本机先测 health

```bash
curl http://127.0.0.1:8011/health
```

### 步骤 3：上传真实 JSON

用 `curl --data-binary @result.json` 上传。

### 步骤 4：检查 recent

```bash
curl "http://127.0.0.1:8011/api/recent-interaction-results?classroom_id=classroom_101"
```

确认：

- `source_kind=raw`
- `analysis_id` 命中

### 步骤 5：打开 dashboard

```text
http://<SERVER_IP>:8011/dashboard?classroom_id=classroom_101
```

确认页面 recent 列表里已经出现真实 `analysis_id`。

## 6. 本轮输出要求

本轮联调结束后，建议至少记录以下结果：

### 6.1 当前监听地址

例如：

```text
http://0.0.0.0:8011
```

### 6.2 当前接口状态

- `/health` 是否 200
- `/api/interaction-results` 是否 200
- `/api/recent-interaction-results` 是否能返回 `raw`
- `/dashboard` 是否可打开

### 6.3 若上传成功

必须记录：

- 本次 `analysis_id`
- raw 文件实际路径
- recent 接口返回中命中的位置
- dashboard 页面是否已看到真实 `analysis_id`

### 6.4 若失败

必须明确写出阻塞点属于哪类：

- 端口监听问题
- 防火墙问题
- schema 校验失败
- 文件权限问题
- sample / fallback 混淆

