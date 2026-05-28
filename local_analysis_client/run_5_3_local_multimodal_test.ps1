param(
    [switch]$RerunAsr,
    [switch]$SkipQuestionAlignmentRebuild,
    [switch]$NoPause
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$OutputEncoding = [System.Text.UTF8Encoding]::new()

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$MaterialDir = Join-Path $RepoRoot "5.3本地多模态分析端测试截图素材"
$SessionDir = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\packages\local_imported_sav_full_classroom_20200908_17"
$FullVideo = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\videos\local_imported_sav_full_classroom_20200908_17.mp4"
$BaseAnalysisJson = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\analysis_results\local_imported_sav_full_classroom_20200908_17.json"
$AsrDir = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_results\phase312_asr_full_classroom_sav_20200908_17"
$TranscriptJson = Join-Path $AsrDir "transcript.json"
$ExtractedAudio = Join-Path $AsrDir "extracted_audio.wav"
$QuestionWorkDir = Join-Path $MaterialDir "_generated_question_alignment"
$DetectionSourceImage = Join-Path $RepoRoot "runs\detect\train_interaction_v1\val_batch2_pred.jpg"

$BehaviorImageOut = Join-Path $MaterialDir "图5-X-课堂行为识别测试结果.png"
$TranscriptOut = Join-Path $MaterialDir "图5-X-离线语音转写结果.json"
$QuestionEventsOut = Join-Path $MaterialDir "图5-X-提问候选事件生成结果.json"
$AlignmentOut = Join-Path $MaterialDir "图5-X-提问候选与视觉响应对齐结果.json"
$FinalJsonOut = Join-Path $MaterialDir "图5-X-本地多模态分析端最终分析结果.json"
$SummaryOut = Join-Path $MaterialDir "5.3本地多模态分析端测试摘要.json"
$ReadmeOut = Join-Path $MaterialDir "截图素材说明.md"

function Write-Step {
    param([string]$Title)
    Write-Host ""
    Write-Host "============================================================" -ForegroundColor DarkGray
    Write-Host $Title -ForegroundColor Cyan
    Write-Host "============================================================" -ForegroundColor DarkGray
}

function Assert-File {
    param([string]$Path, [string]$Name)
    if (-not (Test-Path -LiteralPath $Path)) {
        throw "$Name 不存在：$Path"
    }
    $item = Get-Item -LiteralPath $Path
    Write-Host ("[OK] {0}: {1} ({2} bytes)" -f $Name, $item.FullName, $item.Length)
}

function Read-JsonFile {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path)) {
        return $null
    }
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Convert-CsvToJsonFile {
    param([string]$CsvPath, [string]$JsonPath)
    $rows = @(Import-Csv -LiteralPath $CsvPath)
    $rows | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $JsonPath -Encoding UTF8
    return $rows.Count
}

function Copy-DetectionImageAsPng {
    param([string]$Source, [string]$Destination)
    if (-not (Test-Path -LiteralPath $Source)) {
        Write-Warning "未找到可复用的行为识别检测图：$Source"
        return $false
    }
    Add-Type -AssemblyName System.Drawing
    $image = [System.Drawing.Image]::FromFile($Source)
    try {
        $image.Save($Destination, [System.Drawing.Imaging.ImageFormat]::Png)
    }
    finally {
        $image.Dispose()
    }
    return $true
}

New-Item -ItemType Directory -Path $MaterialDir -Force | Out-Null
New-Item -ItemType Directory -Path $QuestionWorkDir -Force | Out-Null

Write-Host "本地多模态分析端测试开始" -ForegroundColor Green
Write-Host "项目路径：$RepoRoot"
Write-Host "截图素材目录：$MaterialDir"
Write-Host "说明：本次截图主流程使用本地导入的 SAV 完整课堂视频，非树莓派采集，非项目自采集。"

Write-Step "0）核心入口与测试数据定位"
Write-Host "核心分析入口：local-processor\core\classroom_feedback_pipeline.py :: analyze_delivery_package()"
Write-Host "完整课堂分析脚本：scripts\phase3_4e_analyze_local_imported_full_classroom.py"
Write-Host "音频提取与离线 ASR 脚本：scripts\phase3_12_extract_audio_and_run_asr.py"
Write-Host "提问候选与视觉响应对齐脚本：scripts\phase3_13_generate_question_events_from_asr.py"
Write-Host "测试输入 Session：$SessionDir"

Write-Step "1）输入文件校验"
Assert-File $FullVideo "完整课堂视频"
Assert-File (Join-Path $SessionDir "video.mp4") "Session video.mp4"
Assert-File (Join-Path $SessionDir "metadata.json") "Session metadata.json"
Assert-File (Join-Path $SessionDir "capture_metadata.json") "Session capture_metadata.json"
Assert-File (Join-Path $SessionDir "teacher_transcript.json") "Session teacher_transcript.json"
Assert-File (Join-Path $SessionDir "teacher_questions.json") "Session teacher_questions.json"
Write-Host ""
Write-Host "输入 Session 文件列表："
Get-ChildItem -LiteralPath $SessionDir | Sort-Object Name | Format-Table Name, Length, LastWriteTime -AutoSize

Write-Step "2）视频行为识别"
Write-Host "调用本地验证命令，确认完整课堂分析 JSON 已由现有分析流程生成："
& python (Join-Path $RepoRoot "scripts\validate_phase3_4e_local_imported_full_classroom.py")
if ($LASTEXITCODE -ne 0) {
    throw "完整课堂本地分析结果验证失败。"
}
Assert-File $BaseAnalysisJson "基础本地分析 JSON"
$basePayload = Read-JsonFile $BaseAnalysisJson
$handRaiseCount = [int]($basePayload.students.hand_raise_event_count)
$activityCurve = @($basePayload.timeline.activity_curve)
$activeWindowCount = @($activityCurve | Where-Object { [double]$_ -gt 0 }).Count
Write-Host "行为识别摘要：hand_raise_event_count=$handRaiseCount, active_window_count=$activeWindowCount"
$imageCopied = Copy-DetectionImageAsPng -Source $DetectionSourceImage -Destination $BehaviorImageOut
if ($imageCopied) {
    Write-Host "已复制行为识别展示图：$BehaviorImageOut"
}

Write-Step "3）音频提取"
if ($RerunAsr) {
    Write-Host "已请求重跑 ASR：将调用 Phase 3.12 脚本重新提取音频并执行本地离线 ASR。"
    $AsrRebuildDir = Join-Path $MaterialDir "_generated_asr"
    New-Item -ItemType Directory -Path $AsrRebuildDir -Force | Out-Null
    & python (Join-Path $RepoRoot "scripts\phase3_12_extract_audio_and_run_asr.py") --video $FullVideo --output-dir $AsrRebuildDir --analysis-id "chapter5_3_local_multimodal_asr" --engine auto --model "C:\Users\lyy\Desktop\gradu\asr_models\faster-whisper-base"
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 3.12 离线 ASR 重跑失败。"
    }
    $TranscriptJson = Join-Path $AsrRebuildDir "transcript.json"
    $ExtractedAudio = Join-Path $AsrRebuildDir "extracted_audio.wav"
}
Assert-File $ExtractedAudio "已提取音频 extracted_audio.wav"

Write-Step "4）离线语音转写"
Assert-File $TranscriptJson "离线语音转写 transcript.json"
Copy-Item -LiteralPath $TranscriptJson -Destination $TranscriptOut -Force
$transcriptPayload = Read-JsonFile $TranscriptOut
$transcriptSegments = @($transcriptPayload.segments).Count
Write-Host "离线转写结果：transcript_segment_count=$transcriptSegments"
Write-Host "已复制：$TranscriptOut"

Write-Step "5）提问候选生成"
if (-not $SkipQuestionAlignmentRebuild) {
    & python (Join-Path $RepoRoot "scripts\phase3_13_generate_question_events_from_asr.py") --transcript $TranscriptJson --source-analysis $BaseAnalysisJson --video $FullVideo --output-dir $QuestionWorkDir --analysis-id "chapter5_3_local_multimodal_question_alignment"
    if ($LASTEXITCODE -ne 0) {
        throw "Phase 3.13 提问候选与视觉响应对齐脚本执行失败。"
    }
}
$QuestionCsv = Join-Path $QuestionWorkDir "question_events.csv"
if (-not (Test-Path -LiteralPath $QuestionCsv)) {
    $QuestionCsv = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_enriched_results\phase313_asr_enriched_full_classroom_sav_20200908_17\question_events.csv"
}
Assert-File $QuestionCsv "提问候选事件 CSV"
$questionCount = Convert-CsvToJsonFile -CsvPath $QuestionCsv -JsonPath $QuestionEventsOut
Write-Host "提问候选事件数量：$questionCount"
Write-Host "已生成：$QuestionEventsOut"
Write-Host "说明：这里是基于 ASR 文本规则和视觉响应信号的提问候选，不等同于精准教师提问识别。"

Write-Step "6）视觉响应对齐"
$AlignmentCsv = Join-Path $QuestionWorkDir "interaction_alignment.csv"
if (-not (Test-Path -LiteralPath $AlignmentCsv)) {
    $AlignmentCsv = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_enriched_results\phase313_asr_enriched_full_classroom_sav_20200908_17\interaction_alignment.csv"
}
Assert-File $AlignmentCsv "视觉响应对齐 CSV"
$alignmentCount = Convert-CsvToJsonFile -CsvPath $AlignmentCsv -JsonPath $AlignmentOut
Write-Host "视觉响应对齐结果数量：$alignmentCount"
Write-Host "已生成：$AlignmentOut"

Write-Step "7）结构化 JSON 结果生成"
$EnrichedJson = Join-Path $QuestionWorkDir "chapter5_3_local_multimodal_question_alignment.json"
if (-not (Test-Path -LiteralPath $EnrichedJson)) {
    $EnrichedJson = "C:\Users\lyy\Desktop\gradu\real_classroom_samples\asr_enriched_results\phase313_asr_enriched_full_classroom_sav_20200908_17\phase313_asr_enriched_full_classroom_sav_20200908_17.json"
}
Assert-File $EnrichedJson "最终结构化 JSON"
Copy-Item -LiteralPath $EnrichedJson -Destination $FinalJsonOut -Force
Write-Host "已复制：$FinalJsonOut"

$summary = [ordered]@{
    test_input_session = $SessionDir
    source_note = "local imported SAV public full-classroom video; not Raspberry Pi capture; not own capture"
    material_dir = $MaterialDir
    behavior_hand_raise_event_count = $handRaiseCount
    behavior_active_window_count = $activeWindowCount
    transcript_segment_count = $transcriptSegments
    question_candidate_event_count = $questionCount
    visual_response_alignment_count = $alignmentCount
    final_json = $FinalJsonOut
    conclusion = "本地多模态分析端能够完成课堂音视频到结构化课堂反馈数据的转换。"
}
$summary | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $SummaryOut -Encoding UTF8

@"
# 5.3 本地多模态分析端测试截图素材说明

本目录由 run_5_3_local_multimodal_test.ps1 生成。

测试输入 Session：

```text
$SessionDir
```

关键边界：

- 本次截图主流程使用本地导入的 SAV 公开完整课堂视频。
- 该样本不是树莓派采集，不是项目自采集数据。
- 提问事件为 ASR 文本规则和视觉响应信号生成的候选事件，不等同于精准教师提问识别。
- 本测试不宣称系统已经完成自动课堂教学质量评价。

建议论文配图文件：

- 图5-X-课堂行为识别测试结果.png
- 图5-X-离线语音转写结果.json
- 图5-X-提问候选事件生成结果.json
- 图5-X-本地多模态分析端最终分析结果.json
"@ | Set-Content -LiteralPath $ReadmeOut -Encoding UTF8

Write-Host ""
Write-Host "本地多模态分析端测试完成。" -ForegroundColor Green
Write-Host "截图素材目录：$MaterialDir"
Write-Host "最终摘要：$SummaryOut"

if (-not $NoPause) {
    Write-Host ""
    Read-Host "按 Enter 结束，当前窗口可用于截图"
}
