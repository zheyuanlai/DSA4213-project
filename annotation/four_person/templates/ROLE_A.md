## ⚠️ 你的特殊情况：你同时是协调人 / You are also the coordinator

你是 **Annotator A**，与 **Yuxin（Annotator B）** 组成 Team AB，负责 Team AB 的 {{N_CASES}} 个 synthetic case 和 {{N_PAPERS}} 篇真实论文，每一条都要独立标注；Yuxin 标注完全相同的条目。两人都提交之前，**不要查看** Yuxin 的标注。

你作为协调人能访问协调人私有文件（`private/` 中的 TEST gold、condition mapping、case alias map，以及被保留的 `outputs/` 原始输出和自动评测）。这带来一个无法靠重新打乱文件来消除的问题：**如果你曾经看过这些内容，你的标注就不是盲标（not blind）**。因此：

1. **如实填写盲态声明。** 包括你作为协调人审阅过的任何 TEST 输出、自动评测、条件映射。另外请注意：{{EXPOSURE_NOTE}}如果你读过那段会话记录，请在声明的 Q2 中写明。
2. 无论声明结果如何，因为你有私有文件访问权，你的标注最多只能报告为 **“自报盲态、无法验证”（self-reported blind, not verifiable）**；若声明中有任何 `yes`/`unsure`，Team AB 的结果会被标记为 **“可能非盲”（potentially non-blind）**。最终报告不会把 Team AB 描述为完全独立的盲标，除非这有依据。
3. **标注和讨论期间**，不要打开 `private/`、`outputs/`、`results/automatic/`、`docs/AUTOMATIC_RESULTS.md` 等任何能看到 gold、条件或逐条自动评分的文件；不要用协调人权限查询 TEST gold 或条件映射来帮助判断。运行 `evaluation.four_person` 工具时它只打印汇总数字；`score` 命令（会揭盲）只能在**所有** adjudication 结束后运行。
4. **提交顺序（工具会强制）：** 每个阶段，你必须**先**用 `intake` 接收你自己的文件，并把工具打印的 `sha256` 发到群里，**然后** Yuxin 才把她同一阶段的文件发给你。这样能证明你的标签在看到她的之前已经固定。
5. **Pass 2 的发放对你只能自我约束：** 在你的 Pass 1 被 `intake` 接收之前，不要打开你的 `2_pass2` 文件夹或 `annotation/pass2/`。
6. **Team AB 分歧讨论时**，你仍然持有私有文件。请只用研究包证据和 guide 论证，并在 `rationale` 中写出证据。建议请 Team CD 的一位同学事后抽查 AB 的 adjudication 记录。

**科学上更好的替代方案（供小组决定）：** 你只担任协调人、不参与标注，由 Yuxin、Jiajun、Xinkai 三人轮换配对，每条 output 仍有两名完全盲的标注员。代价是每人工作量从约 1/2 增加到约 2/3。说明见 `docs/AMENDMENT_FOUR_PERSON_ANNOTATION.md` §5。目前的文件按小组要求的 A/B/C/D 分配生成；如果要改方案，请在发放 Pass 1 之前决定。
