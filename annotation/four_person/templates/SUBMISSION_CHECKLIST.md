# 提交清单 · Submission checklist — Annotator {{ID}} ({{NAME}}, Team {{TEAM}})

每提交一个文件，在对应的方框里打勾。文件名必须**完全一致**。

## Stage 0
- [ ] 读完 `ANNOTATION_GUIDE.md`、`{{README}}` 和 DEV 例子
- [ ] 填好并发送 `{{F_DECL}}`（Q1–Q6 填 `yes`/`no`/`unsure`，Q7 填 `agree`；`yes`/`unsure` 要写 `details`）

## Stage 1 — Synthetic Pass 1
- [ ] `{{F_PASS1}}`：{{N_SYN}} 行，全部行都填了 `unsupported_claims`、`numeric_errors`、`confidence_p1`
- [ ] 6 个 ordinal 类别的行：`expressed_level`（`0`/`1`/`2`）和 `focal_addressed`（`yes`/`no`）已填；`focal_addressed = no` 时 `expressed_level = 0`
- [ ] NUM / NEG 行：`expressed_level`、`focal_addressed` **留空**
- [ ] 没有改动 ID、行数、原文；另存为 “CSV UTF-8”
- [ ] viewer 自检显示 “No problems found”
- [ ] 已发送给协调人（**之后**才会收到 Pass 2）{{ORDER_NOTE}}

## Stage 2 — Synthetic Pass 2
- [ ] `{{F_PASS2}}`：{{N_SYN}} 行，`confidence_p2` 全部已填
- [ ] 清单 ID 只用研究包里列出的 ID，分号分隔；没有就留空
- [ ] `num_facts_correct` 只在 NUM 行；`neg_findings_reported`、`neg_reframed_positive` 只在 NEG 行（NEG 行 `neg_reframed_positive` 必填）
- [ ] 没有回头修改 Pass 1
- [ ] viewer 自检通过，已发送{{ORDER_NOTE}}

## Stage 3 — Real papers
- [ ] `{{F_REAL_OUT}}`：{{N_REAL_OUT}} 行，`readability`（1–5）、`overall_calibration`、`confidence` 全部已填
- [ ] `{{F_REAL_SENT}}`：{{N_REAL_SENT}} 行，每句 `support_label` 已填（6 个标签之一）
- [ ] 依据的是研究包，而不是原论文作者的结论
- [ ] viewer 自检两个文件都通过，已发送{{ORDER_NOTE}}

## 最后
- [ ] `{{F_TIME}}`：每个阶段（training / pass1 / pass2 / real / adjudication）的总分钟数和次数
- [ ] Stage 5：与 {{PARTNER_NAME}} 一起完成分歧表（每行 `adjudicated_value` + `rationale`），交给协调人
