# 个人标注说明 · Annotator D — Xinkai

> 本文件由 `python -m evaluation.four_person build` 根据模板 `annotation/four_person/templates/` 自动生成。
> 标注规则以 `ANNOTATION_GUIDE.md`（冻结版本，不可修改）为准；本文件只解释**你要做什么、打开哪些文件、怎么提交**，不改变任何字段定义、取值或评分规则。

## 0. 你的身份 / Your role

| 项目 | 内容 |
|---|---|
| 标注员编号 (Annotator ID) | **D — Xinkai** |
| 小组 (Team) | **Team CD** |
| 独立搭档 (Independent partner) | **C — Jiajun** |
| 合成数据 (synthetic) | **16 个 TEST case，共 61 条 output**；Pass 1 和 Pass 2 是**同一批** 61 条 |
| 真实论文 (real papers) | **6 篇论文，20 段 output，76 个句子** |

你的搭档 Jiajun（C）会标注与你**完全相同**的条目，只是行的顺序可能不同。你们必须**各自独立**完成：两人都提交之前，不能讨论任何具体的 TEST 条目，也不能查看、索取对方的标注。这样每条 output 都有两份独立判断，之后计算一致性（agreement）并通过讨论解决分歧（adjudication）。另一组 Team AB 负责另一半数据，你不会收到、也不需要看他们的条目。

原方案是两名标注员各标全部数据；现在改为两组、每组两人、每组负责一半（详见 `docs/AMENDMENT_FOUR_PERSON_ANNOTATION.md`，**标注结束前不要打开 `docs/`**）。`ANNOTATION_GUIDE.md` 中说的 “the two annotators / the other annotator” 现在指**你和你的搭档**；guide 里出现的旧路径（`annotation/pass1/…`、`annotator_<you>_…`）请换成下表中你自己的文件名。

## 你的情况 / Your situation

你是 **Annotator D**，与 **Jiajun（Annotator C）** 组成 Team CD。你收到的条目与 Jiajun **完全相同**（16 个 synthetic case、61 条 output、6 篇真实论文），只是顺序可能不同。你必须**独立**标注全部条目。

* 提交之前，**不要查看 Jiajun 的标签**，也不要讨论具体 TEST 条目。
* 文件发给协调人 Zheyuan。他属于另一组（Team AB），收到你的文件只是为了检查和汇总。
* 不要向任何人（包括协调人）询问 TEST 条目对应的系统或正确答案。

## 1. 你会分阶段收到这些压缩包 / Packages you receive, stage by stage

协调人会**按阶段**把压缩包发给你。拿到下一阶段之前，请不要向任何人索取下一阶段的材料。

| 阶段 | 压缩包 | 何时发放 | 里面要填写的文件 |
|---|---|---|---|
| Stage 0 培训 | `D_Xinkai__0_training.zip` | 一开始 | `D_Xinkai_blinding_declaration.csv`（盲态声明）、`D_Xinkai_time_log.csv`（时间记录，最后提交） |
| Stage 1 Synthetic Pass 1 | `D_Xinkai__1_pass1.zip` | 协调人收到你的盲态声明之后 | `D_Xinkai_pass1.csv` |
| Stage 2 Synthetic Pass 2 | `D_Xinkai__2_pass2.zip` | **只有在你的 Pass 1 文件已被协调人接收之后** | `D_Xinkai_pass2.csv` |
| Stage 3 Real papers | `D_Xinkai__3_real.zip` | 盲态声明之后（建议在 Pass 2 之后做） | `D_Xinkai_real_outputs.csv`、`D_Xinkai_real_sentences.csv` |
| Stage 5 Adjudication | `adjudication_TeamCD.zip` | 你和搭档都提交了全部文件之后 | 分歧表（两人一起填） |

每个压缩包里都有 `00_START_HERE.md`（本阶段的简短步骤）、本说明 `README_D_Xinkai.md`、`ANNOTATION_GUIDE.md`。

**你的 synthetic case（16 个，只显示匿名编号 `case_ref`）：**

| # | case_ref | category | outputs |
|---|---|---|---|
| 1 | `K19` | citation_support | 4 |
| 2 | `K22` | citation_support | 7 |
| 3 | `K11` | consistency | 3 |
| 4 | `K24` | consistency | 6 |
| 5 | `K18` | efficiency | 3 |
| 6 | `K30` | efficiency | 4 |
| 7 | `K16` | generalization | 6 |
| 8 | `K31` | generalization | 3 |
| 9 | `K06` | negative_results | 3 |
| 10 | `K10` | negative_results | 3 |
| 11 | `K28` | numerical_reporting | 3 |
| 12 | `K32` | numerical_reporting | 4 |
| 13 | `K15` | robustness | 3 |
| 14 | `K20` | robustness | 3 |
| 15 | `K04` | statistical_significance | 3 |
| 16 | `K14` | statistical_significance | 3 |

**你的真实论文（6 篇）：**

| paper | outputs | sentences |
|---|---|---|
| `RP-01` | 4 | 14 |
| `RP-02` | 2 | 6 |
| `RP-05` | 3 | 12 |
| `RP-06` | 4 | 17 |
| `RP-07` | 3 | 11 |
| `RP-12` | 4 | 16 |

## 2. 通用规则（所有阶段）/ General rules

1. **只用发给你的压缩包工作。** 不要用仓库（repository）的完整 clone 来标注。即使你有仓库权限，也**不要打开**：`private/`、`outputs/`、`results/`、`data/`、`benchmarks/`、`docs/`、`prompts/`、`src/`、`report/`、`annotation/pass1/`、`annotation/pass2/`、`annotation/real/`、`annotation/four_person/`（除了发给你的文件）、任何运行日志。
2. **不要打开** gold 标签、私有映射文件（condition mapping / case alias map）、带系统身份的原始输出、自动评测结果，也不要向任何人打听哪段文字是哪个系统写的。
3. **独立标注。** 两人都提交之前，不讨论具体 TEST 条目，不看对方的表。可以一起讨论 guide 的一般规则和 DEV 例子。
4. **不要用 AI 工具（ChatGPT、Claude、Copilot 等）来判断或填写任何标签。** 所有标签必须是你本人的判断。
5. **不改表格结构。** 不增删行或列，不改 `output_id`、`sentence_idx`、`case_ref`、`category`、`package_file`、`output_text`、`sentence_text`。只填写空白的标注列。不要按 `case_ref` 排序后再标注（行序是随机打乱的）。
6. 遇到拿不准的条目：按 guide §6 选**较低**的等级，置信度填 `low`，并在 notes 里**引用决定性的短语**。不要去问搭档。

### 2.1 怎么打开和保存 CSV（很重要）/ Opening and saving CSV files

CSV 文件是 UTF-8 编码（带 BOM），里面有 `±`、`≥`、`×` 等符号。

* **Excel：** 双击打开即可。保存时选择 **文件 → 另存为 → “CSV UTF-8 (逗号分隔) (*.csv)”**，文件名保持不变。**不要**存成 `.xlsx`，也不要选普通 “CSV (逗号分隔)”（会损坏符号）。
* **Google Sheets：** 文件 → 导入 → 上传 CSV；完成后 文件 → 下载 → 逗号分隔值 (.csv)，再把下载的文件**改回原文件名**。
* **Numbers / WPS / LibreOffice：** 导出为 CSV，编码选 UTF-8，分隔符用逗号。
* 数字列只写整数（如 `0`、`2`），不要写 `0.0`；文字标签必须和下表**完全一致**（如 `yes`、`well_calibrated`、`SUPPORTED`）。
* 填完后，用对应的 viewer（HTML 文件）顶部的 **“Check my CSV file / 检查我的 CSV”** 按钮选择你的 CSV 自检。它只在你自己的浏览器里本地运行，不会上传任何东西。显示 “No problems found” 再提交。协调人收到后还会再做一次正式检查。

## 3. Stage 0：准备 / Preparation

1. 从头到尾读一遍 `ANNOTATION_GUIDE.md` 和本说明。
2. 学习 DEV 训练材料：打开 `dev_training_viewer.html`（或 `demo_example_NOT_TEST.md` + `dev_packages/`）。这 4 个例子来自 DEV 集（不是 TEST），示例标签只是示范，你可以不同意。
3. 如有需要，四个人（或你和搭档）可以**一起讨论 DEV 例子**和 guide 的一般规则。这是唯一允许讨论具体例子的阶段。
4. 开始 TEST 标注前，确认你理解每个字段的取值和计分含义（见下面 Stage 1–3）。
5. **填写盲态声明** `D_Xinkai_blinding_declaration.csv`：对每个问题在 `answer` 列填 `yes` / `no` / `unsure`（最后一题 Q7 填 `agree` / `disagree`）；凡是填 `yes` 或 `unsure` 的，在 `details` 写清楚看过什么、什么时候。请如实填写：曾经看过并不会让你失去标注资格，但必须如实记录，报告里会据此说明盲态程度。保存后发给协调人。
6. 不要打开 gold 标签、私有映射文件、系统原始输出或无关的实验日志。

协调人收到并接收你的声明后，才会发 Stage 1 的压缩包。

## 4. Stage 1：Synthetic Pass 1

**打开：** `D_Xinkai_pass1_viewer.html`（浏览器打开）和 `D_Xinkai_pass1.csv`（Excel/Sheets）。共 **61 行**。

步骤：
1. 在浏览器打开 viewer。每张卡片对应 CSV 的一行，顺序相同（卡片 1 = CSV 第 2 行，因为第 1 行是表头）。也可以在 viewer 顶部输入 `output_id` 跳转。
2. 在 CSV 里找到同一个 `output_id`。
3. 点开卡片里的 “Research package & rubric”，阅读 research package（研究包：问题、设定、表格、统计检验、引用段落），然后阅读生成的段落（灰色框）。
4. 找到 rubric 里的 **focal proposition（焦点命题）**，读 level descriptors（等级描述）。
5. 填 `expressed_level`（仅限 6 个 ordinal 类别）。
6. 填 `focal_addressed`（仅限 6 个 ordinal 类别）。
7. 数 `unsupported_claims`。
8. 数 `numeric_errors`。
9. 填 `confidence_p1`。
10. 在 `notes_p1` 记录有歧义的决定（引用决定性短语）。
11. 保存为 CSV UTF-8，**不改任何 ID、行数或原文**。
12. 用 viewer 的自检按钮检查后，把 `D_Xinkai_pass1.csv` 发给协调人。**提交 Pass 1 之后才会收到 Pass 2。**

| 字段 | 允许的值 | 适用范围 | 说明 |
|---|---|---|---|
| `expressed_level` | `0` / `1` / `2` | SIG, ROB, GEN, CON, EFF, CIT（statistical_significance, robustness, generalization, consistency, efficiency, citation_support） | 段落**字面上**表达的焦点命题强度 |
| `focal_addressed` | `yes` / `no` | 同上 | 段落有没有谈到焦点命题；`no` 时 `expressed_level` 必须是 `0` |
| `unsupported_claims` | 整数 ≥ 0 | 所有类别 | 研究包不支持的额外断言数量（guide §5） |
| `numeric_errors` | 整数 ≥ 0 | 所有类别 | 错误数值、方向、单位，或数字安错了方法/数据集（含编造的 SD、p 值、CI） |
| `confidence_p1` | `low` / `medium` / `high` | 所有类别 | 你对本行判断的把握 |
| `notes_p1` | 自由文本 | 所有类别 | 边界情况请引用决定性短语 |

**NUM（numerical_reporting）和 NEG（negative_results）的行：`expressed_level` 和 `focal_addressed` 必须留空。** 这两类在 Pass 1 只填 `unsupported_claims`、`numeric_errors`、`confidence_p1`、`notes_p1`。

**最重要的区别：expressed strength ≠ evidence-supported (gold) strength。**
`expressed_level` 判断的是**段落用词实际表达的强度**，不是证据“应该”支持的强度。例如段落写 “significantly outperforms”，即使研究包里根本没有做显著性检验，`expressed_level` 也是 `2`；证据是否支持，由协调人在标注结束后和预先登记的标准比较，同时你在 `unsupported_claims` 里记录那个无依据的断言。不要因为“它说错了”就降低 `expressed_level`。各类别的等级规则见 guide §3，判定顺序见 guide §6（以最强的、未撤回的陈述为准；明确否定优先；拿不准选较低等级）。

## 5. Stage 2：Synthetic Pass 2（只在 Pass 1 已提交后）

**打开：** `D_Xinkai_pass2_viewer.html` 和 `D_Xinkai_pass2.csv`。是**同样的 61 条 output**，顺序不同。Pass 2 的研究包附带**核对清单（checklists）**，每项有一个 ID（如 `f1`、`n2`）。

步骤：
1. 打开 Pass 2 viewer 和 CSV。
2. 阅读每个 case 的 required-finding checklist（以及 NUM 的数值事实清单）。
3. 填 `findings_covered`：段落**正确**报告了的 required finding 的 ID。
4. NUM 行填 `num_facts_correct`：数值、对象（方法+数据集/行）、单位/尺度、方向**全部正确**的数值事实 ID。
5. NEG 行填 `neg_findings_reported`（以正确范围报告的负面/零结果 finding ID）和 `neg_reframed_positive`（`yes`/`no`：是否把不利或零结果说成有利）。
6. 填 `confidence_p2` 和 `notes_p2`。
7. 多个 ID 用**英文分号**分隔，严格使用清单里的 ID，例如 `f1;f3`。
8. 如果一个都没有，**留空**（不要写 `none`、`-` 或 `0`）。
9. 自检后把 `D_Xinkai_pass2.csv` 发给协调人。

| 字段 | 允许的值 | 适用范围 |
|---|---|---|
| `findings_covered` | 清单 ID，分号分隔，可留空 | 所有类别 |
| `num_facts_correct` | 数值事实 ID，分号分隔，可留空 | 只限 NUM；其他类别留空 |
| `neg_findings_reported` | finding ID，分号分隔，可留空 | 只限 NEG；其他类别留空 |
| `neg_reframed_positive` | `yes` / `no` | 只限 NEG（必填）；其他类别留空 |
| `confidence_p2` | `low` / `medium` / `high` | 所有类别 |
| `notes_p2` | 自由文本 | 所有类别 |

**不要回头修改 Pass 1。** Pass 2 的清单措辞可能让你对 Pass 1 有新的想法，但 Pass 1 已经提交并固定，请不要重新提交 Pass 1，也不要在 Pass 2 里改写 Pass 1 的字段。

## 6. Stage 3：真实论文 / Real-paper annotation

**打开：** `D_Xinkai_real_viewer.html`、`D_Xinkai_real_outputs.csv`（20 行，段落级）和 `D_Xinkai_real_sentences.csv`（76 行，句子级）。

真实论文**没有 gold 标签**。判断依据是**研究包本身**（表格、检验、引用段落），**不是**原论文作者的结论，也不是你对这篇论文的了解。viewer 里每段 output 都列出了编号句子，编号就是 `sentence_idx`。

**段落级（paragraph-level，`D_Xinkai_real_outputs.csv`，每段一行）：**

| 字段 | 允许的值 | 含义 |
|---|---|---|
| `readability` | `1`–`5` 的整数 | 1 = 很难读懂，5 = 清晰、可以直接发表 |
| `overall_calibration` | `well_calibrated` / `overstated` / `understated` / `mixed` | 整段的断言强度与研究包的匹配程度：基本匹配 / 总体说过头 / 总体说得过弱（如漏掉已报告的显著结果）/ 既有明显过度也有明显不足 |
| `confidence` | `low` / `medium` / `high` | 你的把握 |
| `notes` | 自由文本 | 需要时写理由 |

**句子级（sentence-level，`D_Xinkai_real_sentences.csv`，每句一行，`support_label` 必填）：**

| `support_label` | 含义 | 示例（虚构，仅作说明，不是 TEST 或真实论文条目） |
|---|---|---|
| `SUPPORTED` | 研究包以所述强度支持这句话 | 研究包：X 在数据集 Z 上准确率 84.1，Y 为 82.7，配对 t 检验 p = 0.03。句子：“On Z, X reached 84.1% accuracy versus 82.7% for Y, a statistically significant difference (p = 0.03).” |
| `OVERSTATED` | 比研究包支持的更强或更宽 | 同一研究包（只测了 Z）。句子：“X substantially outperforms Y across tasks.” |
| `UNDERSTATED` | 明显弱于研究包支持的强度（例如忽略了已报告的显著检验） | 同一研究包。句子：“X and Y performed about the same on Z.” |
| `UNSUPPORTED` | 研究包里没有依据 | 研究包没测速度。句子：“X is also faster than Y.” |
| `NUMERIC_ERROR` | 数字或归属错误 | 句子：“X reached 85.1% accuracy on Z.”（应为 84.1），或把 82.7 说成 X 的结果 |
| `NOT_A_CLAIM` | 不是关于结果的断言 | “Table 1 summarizes the results on Z.” / “We now turn to the second experiment.” |

段落里一个句子只选一个标签；同一句同时有数字错误和过度表述时，选你认为最主要的问题，并在 `notes` 说明。

## 7. Stage 4：提交 / Submission

你最终需要提交 **4 个 CSV 标注文件**（外加盲态声明和时间记录）：

| # | 文件名 | 行数 | 何时提交 |
|---|---|---|---|
| 1 | `D_Xinkai_pass1.csv` | 61 | Pass 1 完成后（Pass 2 发放前） |
| 2 | `D_Xinkai_pass2.csv` | 61 | Pass 2 完成后 |
| 3 | `D_Xinkai_real_outputs.csv` | 20 | 真实论文完成后 |
| 4 | `D_Xinkai_real_sentences.csv` | 76 | 真实论文完成后 |
| – | `D_Xinkai_blinding_declaration.csv` | 7 | Stage 0（最先提交） |
| – | `D_Xinkai_time_log.csv` | 5 | 全部结束后（每个阶段填总分钟数和次数） |

* 文件名保持不变；格式保持 CSV UTF-8。
* 在 `D_Xinkai_time_log.csv` 里记录每个阶段的**总用时（分钟）**和**标注次数（sessions）**，报告里会如实报告工作量和每个人的贡献。
* 发给协调人（Zheyuan），说明是哪一个文件。协调人会运行正式检查；如有问题会把具体行号/字段发回给你修改，修改后用**同一个文件名**重新发送。
* 详细的勾选清单见 `SUBMISSION_CHECKLIST_D_Xinkai.md`。

## 8. Stage 5：分歧讨论 / Disagreement resolution (adjudication)

**只有在你和搭档的全部独立文件都已提交并固定之后**才开始。

1. 协调人为 Team CD 生成分歧表（只包含你们两人**不一致**的字段；一致的标签自动保留）和 adjudication viewer，打包为 `adjudication_TeamCD.zip`。你只会看到本组的分歧，看不到另一组的数据。
2. 你和 Jiajun 一起，逐条根据**研究包证据**和 `ANNOTATION_GUIDE.md` 讨论。
3. 在 `adjudicated_value` 填最终取值，在 `rationale` 用一两句话写理由（引用研究包或 guide 条款）。每一行都必须填写，系统不会替你们选其中一人的答案。
   * synthetic 表中，如果最终结论是“清单为空”，`adjudicated_value` 写 `NONE`。
   * 取值必须是该字段允许的值（例如 `0/1/2`、`yes/no`、清单 ID、`SUPPORTED` 等）。
4. 讨论时系统身份和 TEST gold **仍然保密**；不要猜测或讨论哪段文字来自哪个系统。
5. 把填好的分歧表交给协调人。如果有空行或非法取值，协调人的检查会拒绝生成共识，并把问题发回给你们。

谢谢！有任何**流程**问题（文件打不开、格式问题）请问协调人；有关**具体条目**的问题请按 guide §6 自行决定并写进 notes。
