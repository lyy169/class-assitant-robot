#!/bin/bash
set -e

# 课堂交互分析系统云端接收服务联调脚本

CLOUD_URL="${CLOUD_URL:-http://127.0.0.1:8010/api/interaction-results}"
API_KEY="${API_KEY:-please-change-this-key}"

echo "开始测试云端接收接口：$CLOUD_URL"

curl -X POST "$CLOUD_URL" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "window_id": "window_20260414_001",
    "classroom_id": "classroom_101",
    "source_host": "lab-workstation-3060",
    "started_at": "2026-04-14T10:00:00Z",
    "ended_at": "2026-04-14T10:00:20Z",
    "generated_at": "2026-04-14T10:00:22Z",
    "interaction_counts": {
      "hand_raising": 4,
      "standing": 1,
      "total_events": 5
    },
    "grid_stats": {
      "r1c1": {"hand_raising": 1, "standing": 0},
      "r1c2": {"hand_raising": 0, "standing": 0},
      "r1c3": {"hand_raising": 1, "standing": 0},
      "r2c1": {"hand_raising": 0, "standing": 1},
      "r2c2": {"hand_raising": 1, "standing": 0},
      "r2c3": {"hand_raising": 0, "standing": 0},
      "r3c1": {"hand_raising": 0, "standing": 0},
      "r3c2": {"hand_raising": 1, "standing": 0},
      "r3c3": {"hand_raising": 0, "standing": 0}
    },
    "deduplication": {
      "enabled": true,
      "window_seconds": 20
    },
    "meta": {
      "model_name": "yolov11-dual-class",
      "classes": ["hand-raising", "standing"]
    }
  }'

echo
echo "测试完成，请检查返回结果和 cloud_backend/data/raw/ 目录。"
