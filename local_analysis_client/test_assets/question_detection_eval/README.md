# Question Detection Eval

这个目录用于验证本地规则算法对“教师提问候选事件”的判断效果，而不是验证精准教师身份识别。

## 文件说明

- `question_detection_gold.csv`：人工真值表，共 150 条样本。
- `teacher_transcript_eval.json`：模拟 ASR 输出，可直接作为 `--transcript` 输入。
- `README.md`：当前说明文件。

## 数据分类

| category | 数量 | gold_is_question | 目的 |
|---|---:|---|---|
| explicit_question | 50 | true | 测试真实课堂提问是否能被检出 |
| non_question | 50 | false | 测试普通陈述、课堂指令是否会被误判 |
| question_word_non_question | 50 | false | 测试含疑问词但语义不是提问的关键词陷阱 |

## 字段说明

CSV 字段：

- `case_id`：样本编号，与 JSON 中的 `segment_id` 一致。
- `category`：人工样本类型。
- `text`：课堂话语文本。
- `gold_is_question`：人工真值，`true` 表示真实提问，`false` 表示非提问。
- `language`：语言。
- `difficulty`：样本难度，用于观察简单样本和边界样本差异。
- `has_question_word`：是否包含常见疑问词或提问触发词。
- `has_question_mark`：是否包含 `?` 或 `？`。
- `notes`：人工备注。

JSON 中每个 `segment` 额外保留了 `gold_is_question`、`gold_category`、`gold_difficulty`，当前检测脚本不会使用这些字段，但便于后续评估时对齐真值。

## 时间间隔

每条片段间隔 15 秒，单条持续 4 秒。这样相邻片段间隔大于 5 秒，可避免当前脚本把相邻候选事件合并，影响逐条统计。

## 推荐运行

在 `ultralytics-8.3.163` 目录下运行：

```powershell
python scripts/phase3_13_generate_question_events_from_asr.py `
  --transcript test_assets/question_detection_eval/teacher_transcript_eval.json `
  --source-analysis test_assets/question_detection_eval/empty_source_analysis.json `
  --video test_assets/question_detection_eval/dummy.mp4 `
  --output-dir test_assets/question_detection_eval/output `
  --analysis-id question_detection_eval
```

`empty_source_analysis.json` 和 `dummy.mp4` 不存在也可以，当前脚本读取不到时会按空数据继续执行；本评估重点是文本规则是否生成 `question_events.csv`。

## 统计建议

运行后将输出中的 `question_events.csv` 与 `question_detection_gold.csv` 按 `source_segment_ids` / `case_id` 对齐：

- `precision`：检出的提问候选中，人工真值为提问的比例。
- `recall`：人工真值为提问的样本中，被检出的比例。
- `accuracy`：三类整体判断正确率。
- `false_positive`：非提问被误判为提问的数量。
- `false_negative`：明确提问被漏检的数量。

重点观察 `question_word_non_question` 类别。如果这类误判很多，说明关键词规则容易把“包含疑问词的陈述句”当成提问。
