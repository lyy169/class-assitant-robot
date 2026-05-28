# Local Demo Delivery Package Commands

演示包生成脚本：

```powershell
python scripts\phase3_5c_build_local_demo_delivery_package.py
```

生成后的演示包目录：

```text
C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\captures_local_delivery\classroom_local_imported_demo\2026-05-23\phase35_demo_local_imported_sav_full_classroom_20200908_17
```

直接解析这个单包，仅演示本地端把 Session 包转成结构化 JSON：

```powershell
python local-processor\scripts\analyze_classroom_delivery.py C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\captures_local_delivery\classroom_local_imported_demo\2026-05-23\phase35_demo_local_imported_sav_full_classroom_20200908_17 --config-path config.yaml --output-dir processed_results\classroom_feedback --pending-upload-dir processed_results\pending_upload --upload-mode directory
```

模拟“本地端扫描接收目录并消费 1 个 ready Session 包”：

```powershell
python local-processor\scripts\consume_ready_sessions.py --delivery-root C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\captures_local_delivery\classroom_local_imported_demo --config-path config.yaml --output-dir processed_results\classroom_feedback --pending-upload-dir processed_results\pending_upload --manifest-path processed_results\demo_session_consume_manifest.json --upload-mode directory --limit 1
```

如果你要演示“收到一个还没补 transcript/question 的原始包，本地端先补全再分析”，用这个脚本：

```powershell
python scripts\phase3_5c_enrich_and_analyze_delivery_package.py C:\Users\lyy\Desktop\gradu\ultralytics-8.3.163\captures_local_delivery\classroom_local_imported_demo\2026-05-23\phase35_demo_local_imported_sav_full_classroom_20200908_17_raw_like_validation --config-path config.yaml --output-dir processed_results\classroom_feedback --pending-upload-dir processed_results\pending_upload --upload-mode directory --transcript-json C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_results\phase312_asr_full_classroom_sav_20200908_17\transcript.json --question-csv C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_enriched_results\phase313_asr_enriched_full_classroom_sav_20200908_17\question_events.csv
```

说明：

- 这个 `raw_like_validation` 包起始时只有音视频和元数据，没有 `teacher_transcript.json` / `teacher_questions.json`。
- 当前这台机器缺少可直接重跑的本地 Whisper 模型缓存，所以命令里显式复用了你已经存在的本地 ASR / question 结果。
- 如果后面本机补好离线 ASR 模型缓存，也可以去掉 `--transcript-json` / `--question-csv`，让脚本优先尝试本地自动生成。

如果答辩现场云端服务已经就绪，需要在解析成功后自动尝试上传到云端，把上面命令里的 `--upload-mode directory` 改为：

```text
--upload-mode auto
```

说明：

- 这个演示包来源于 `SAV` 公开数据集完整课堂视频。
- 包结构仿照树莓派投递的 Session 目录布局，但元数据已明确标记：
  - `source_dataset=SAV`
  - `source_type=local_imported_video`
  - `is_pi_capture=false`
  - `is_own_capture=false`
- 适合答辩时说明“本地端可消费 Session 包并输出结构化课堂分析 JSON”，同时不把该样本说成树莓派实采数据。
