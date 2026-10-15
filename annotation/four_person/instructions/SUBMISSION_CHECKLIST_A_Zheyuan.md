# 提交清单 · Submission checklist — Annotator A (Zheyuan, Team AB)

每提交一个文件，在对应的方框里打勾。文件名必须**完全一致**。

## Stage 0
- [ ] 读完 `ANNOTATION_GUIDE.md`、`README_A_Zheyuan.md` 和 DEV 例子
- [ ] 填好并发送 `A_Zheyuan_blinding_declaration.csv`（Q1–Q6 填 `yes`/`no`/`unsure`，Q7 填 `agree`；`yes`/`unsure` 要写 `details`）

## Stage 1 — Synthetic Pass 1
- [ ] `A_Zheyuan_pass1.csv`：61 行，全部行都填了 `unsupported_claims`、`numeric_errors`、`confidence_p1`
- [ ] 6 个 ordinal 类别的行：`expressed_level`（`0`/`1`/`2`）和 `focal_addressed`（`yes`/`no`）已填；`focal_addressed = no` 时 `expressed_level = 0`
- [ ] NUM / NEG 行：`expressed_level`、`focal_addressed` **留空**
- [ ] 没有改动 ID、行数、原文；另存为 “CSV UTF-8”
- [ ] viewer 自检显示 “No problems found”
- [ ] 已发送给协调人（**之后**才会收到 Pass 2）（先用 `intake` 接收自己的文件，并在群里公布 sha256）

## Stage 2 — Synthetic Pass 2
- [ ] `A_Zheyuan_pass2.csv`：61 行，`confidence_p2` 全部已填
- [ ] 清单 ID 只用研究包里列出的 ID，分号分隔；没有就留空
- [ ] `num_facts_correct` 只在 NUM 行；`neg_findings_reported`、`neg_reframed_positive` 只在 NEG 行（NEG 行 `neg_reframed_positive` 必填）
- [ ] 没有回头修改 Pass 1
- [ ] viewer 自检通过，已发送（先用 `intake` 接收自己的文件，并在群里公布 sha256）

## Stage 3 — Real papers
- [ ] `A_Zheyuan_real_outputs.csv`：19 行，`readability`（1–5）、`overall_calibration`、`confidence` 全部已填
- [ ] `A_Zheyuan_real_sentences.csv`：75 行，每句 `support_label` 已填（6 个标签之一）
- [ ] 依据的是研究包，而不是原论文作者的结论
- [ ] viewer 自检两个文件都通过，已发送（先用 `intake` 接收自己的文件，并在群里公布 sha256）

## 最后
- [ ] `A_Zheyuan_time_log.csv`：每个阶段（training / pass1 / pass2 / real / adjudication）的总分钟数和次数
- [ ] Stage 5：与 Yuxin 一起完成分歧表（每行 `adjudicated_value` + `rationale`），交给协调人
