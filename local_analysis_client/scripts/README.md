# Scripts

这个目录用于存放本地开发和联调测试脚本。

当前已提供：

- `test_local_receiver.py`
  - 用于测试本地计算机端 `FastAPI + YOLO + 统计输出` 链路
  - 默认测试接口：
    - `GET /health`
    - `POST /api/keyframes`
  - 可自动生成测试 JPEG 图片

## 使用方法

先启动本地服务：

```powershell
python keyframe_receiver.py
```

再运行测试脚本：

```powershell
python scripts/test_local_receiver.py --generate-samples
```

如果服务地址不是默认的 `http://127.0.0.1:8000`，可以手动指定：

```powershell
python scripts/test_local_receiver.py --server http://127.0.0.1:9000 --generate-samples
```

## 测试结果

运行成功后，通常会看到：

- 健康检查返回 JSON
- `/api/keyframes` 返回 `summary`
- 本地生成结果文件：
  - `processed_results/<window_id>.json`

## 样例图片目录

默认测试图片目录：

- `scripts/sample_keyframes/`

当目录中没有 JPEG 时，可使用 `--generate-samples` 自动生成测试图片。
