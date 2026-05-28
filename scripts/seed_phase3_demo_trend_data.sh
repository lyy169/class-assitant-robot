#!/bin/bash
set -euo pipefail

API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8011}"
CLASSROOM_ID="${CLASSROOM_ID:-classroom_101}"
ENV_FILE="${ENV_FILE:-/root/video_project_src/cloud_backend/.env.postgres.runtime}"

if [ "${1:-}" = "--cleanup" ]; then
  if [ -f "${ENV_FILE}" ]; then
    set -a
    # shellcheck disable=SC1090
    source "${ENV_FILE}"
    set +a
  fi
  DATABASE_URL="${CLOUD_DATABASE_URL:-${POSTGRES_URL:-}}"
  if [ -z "${DATABASE_URL}" ]; then
    echo "[error] CLOUD_DATABASE_URL or POSTGRES_URL is required for cleanup" >&2
    exit 1
  fi
  psql "${DATABASE_URL}" -v ON_ERROR_STOP=1 <<'SQL'
DELETE FROM analysis_results
WHERE analysis_id LIKE 'demo_phase3_%'
   OR payload_json->'dataset'->>'source' = 'demo'
   OR payload_json->'dataset'->>'purpose' = 'phase3_trend_seed';
DELETE FROM sessions
WHERE analysis_id LIKE 'demo_phase3_%';
SQL
  echo "[done] Phase 3.0 demo trend data cleaned"
  exit 0
fi

if [ "${1:-}" != "--seed" ]; then
  echo "usage: bash scripts/seed_phase3_demo_trend_data.sh --seed|--cleanup" >&2
  exit 1
fi

TMP_DIR="${TMPDIR:-/tmp}/phase30-demo-seed-$$"
mkdir -p "${TMP_DIR}"
trap 'rm -rf "${TMP_DIR}"' EXIT

python - "${TMP_DIR}" "${CLASSROOM_ID}" <<'PY'
import json
import pathlib
import sys
from datetime import datetime, timedelta, timezone

target = pathlib.Path(sys.argv[1])
classroom_id = sys.argv[2]
base = datetime.now(timezone.utc) - timedelta(days=8)
for index in range(8):
    score = 68 + index * 3
    attention = 56 + index * 4
    response = 0.42 + index * 0.055
    activity = 0.35 + index * 0.045
    ts = base + timedelta(days=index)
    payload = {
        "schema_version": "v1.1",
        "analysis_id": f"demo_phase3_{index + 1:03d}",
        "classroom_id": classroom_id,
        "classroom_name": "Phase 3 Demo Classroom",
        "lesson_title": f"Phase 3 Demo Lesson {index + 1}",
        "video_id": f"demo_phase3_video_{index + 1:03d}",
        "dataset": {"source": "demo", "purpose": "phase3_trend_seed", "generated_at": ts.isoformat()},
        "source": {"source_kind": "demo", "source_path": f"demo_phase3_{index + 1:03d}.json", "source_host": "phase3-demo-seed"},
        "time": {"recorded_at": ts.isoformat(), "generated_at": ts.isoformat(), "duration_seconds": 2400},
        "summary": {
            "feedback_score": min(score, 95),
            "attention_score": min(attention, 92),
            "response_score": min(response * 100, 90),
            "teacher_question_count": 2 + index,
            "avg_attention_ratio": min(attention / 100, 0.92),
            "response_success_rate": min(response, 0.9),
            "summary_text": "Phase 3 demo trend seed result.",
        },
        "teacher": {
            "question_events": [
                {"event_id": f"q{index}_{j}", "start_sec": 120 + j * 240, "end_sec": 145 + j * 240, "text": f"Demo question {j + 1}", "question_type": "guiding"}
                for j in range(2 + index)
            ],
            "stage_distribution": {
                "exposition_ratio": max(0.2, 0.55 - index * 0.025),
                "question_ratio": min(0.3, 0.12 + index * 0.018),
                "discussion_ratio": min(0.28, 0.08 + index * 0.025),
                "summary_ratio": 0.1,
                "management_ratio": max(0.08, 0.15 - index * 0.008),
            },
        },
        "students": {
            "estimated_student_count": 32,
            "hand_raise_event_count": 3 + index,
            "zones": {
                "front": {"avg_attention_ratio": min(0.95, attention / 100 + 0.08), "active_ratio": min(0.9, activity + 0.08)},
                "middle": {"avg_attention_ratio": min(0.9, attention / 100), "active_ratio": min(0.85, activity)},
                "back": {"avg_attention_ratio": min(0.82, attention / 100 - 0.06), "active_ratio": min(0.78, activity - 0.04)},
            },
        },
        "timeline": {
            "window_size_seconds": 300,
            "attention_curve": [round(min(0.95, attention / 100 + (j - 2) * 0.025), 3) for j in range(6)],
            "heat_curve": [round(min(0.9, activity + j * 0.025), 3) for j in range(6)],
            "activity_curve": [round(min(0.9, activity + (j % 3) * 0.035), 3) for j in range(6)],
        },
        "issues": [] if index > 3 else [{"event_id": f"issue_{index}", "type": "low_attention", "start_sec": 600, "description": "Demo low attention segment"}],
    }
    (target / f"demo_phase3_{index + 1:03d}.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
PY

for file in "${TMP_DIR}"/demo_phase3_*.json; do
  status="$(curl -sS -o /tmp/phase30-seed-response.json -w "%{http_code}" -H "Content-Type: application/json" --data @"${file}" "${API_BASE_URL}/api/interaction-results")"
  if [ "${status}" != "200" ]; then
    echo "[error] upload failed for ${file}: HTTP ${status}" >&2
    cat /tmp/phase30-seed-response.json >&2 || true
    exit 1
  fi
done

echo "[done] Phase 3.0 demo trend data seeded"
