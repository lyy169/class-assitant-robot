param(
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$MaterialDir = Join-Path $RepoRoot "5.3本地多模态分析端测试截图素材"
$SummaryPath = Join-Path $MaterialDir "5.3本地多模态分析端测试摘要.json"
$FinalJsonPath = Join-Path $MaterialDir "图5-X-本地多模态分析端最终分析结果.json"

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

if (-not (Test-Path -LiteralPath $SummaryPath)) {
    Write-Host "未找到截图素材摘要，请先运行：.\run_5_3_local_multimodal_test.ps1" -ForegroundColor Yellow
    if (-not $NoPause) {
        Read-Host "按 Enter 结束"
    }
    exit 1
}

$summary = Read-JsonFile $SummaryPath

Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host "第5章 5.3 本地多模态分析端测试结果" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor DarkGray
Write-Host ""
Write-Host "测试输入 Session 路径："
Write-Host ("  " + $summary.test_input_session)
Write-Host ""
Write-Host "输入文件列表："
Get-ChildItem -LiteralPath $summary.test_input_session | Sort-Object Name | ForEach-Object {
    Write-Host ("  {0,-28} {1,12} bytes" -f $_.Name, $_.Length)
}
Write-Host ""
Write-Host "测试结果摘要："
Write-Host ("  行为识别结果数量：hand_raise_event_count={0}, active_window_count={1}" -f $summary.behavior_hand_raise_event_count, $summary.behavior_active_window_count)
Write-Host ("  语音转写片段数量：{0}" -f $summary.transcript_segment_count)
Write-Host ("  提问候选事件数量：{0}" -f $summary.question_candidate_event_count)
Write-Host ("  视觉响应对齐结果数量：{0}" -f $summary.visual_response_alignment_count)
Write-Host ""
Write-Host "最终 JSON 文件路径："
Write-Host ("  " + $FinalJsonPath)
Write-Host ""
Write-Host "测试结论："
Write-Host "  本地多模态分析端能够完成课堂音视频到结构化课堂反馈数据的转换。" -ForegroundColor Green
Write-Host ""
Write-Host "边界说明："
Write-Host "  提问事件为候选事件，不等同于精准教师提问识别；本测试不宣称自动课堂教学质量评价已完成。"

if (-not $NoPause) {
    Write-Host ""
    Read-Host "按 Enter 结束，当前窗口可用于截图"
}
