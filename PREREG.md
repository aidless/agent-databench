# PREREG — agent-databench (评测 harness 阶段)

> 预注册规格：本文件声明**本仓库当前阶段可检验的研究假设、评测方案、
> 成功标准与明确边界**。内容全部对应仓库真实实现与真实输出
> （`agent_databench/` 的 loop/sandbox/scoring/tools/llm、`tasks/tasks.jsonl`
> 的 20 个带标准答案任务、`results/base-fake.jsonl` 的 20 行回放、
> `tests/` 的 7 项离线测试、`configs/base.yaml` vs `configs/variant_tool_hints.yaml`），
> 不含虚构数字或未实现能力。

## 1. 研究问题

手写 tool-calling 循环（不依赖 agent 框架）做 CSV 数据分析时，如何量化
「通过率 / 轮数 / token 成本」三个数，并让**配置差异可归因到 prompt 层**
而没有框架噪声？核心机制问题：把一个带评测 harness 的 agent 做成能
端到端判分、且配置对比干净的最小结构。

## 2. 假设（H1–H3，全部可证伪）

- **H1（管道可判分）**：手写 loop + 进程级沙箱能在 20 个带标准答案的 CSV
  分析任务上端到端跑通判分管道；`--fake` 回放证明 loop/沙箱/判分/报告接线正确。
- **H2（A/B 可归因）**：`base.yaml` vs `variant_tool_hints.yaml` 在同一任务集上
  的差异全部归因到 prompt 层（无框架噪声），因为二者共享同一 harness。
- **H3（沙箱是进程级而非安全边界）**：沙箱约束为超时 15s / 输出截断 4KB /
  脱敏 KEY|TOKEN|SECRET / cwd 锁定——**不是**安全边界（无 seccomp/容器），
  防失控刷爆会话够用，防恶意代码不够用。

## 3. 评测方案

- **任务集**：`tasks/tasks.jsonl`，20 个带标准答案任务；答案由
  `tasks/build_tasks.py` 从 `data/games.csv` **现场计算**，不是手抄——数据变了
  评测集自动跟着变。
- **判分**：`scoring.py` 程序化判分（数值容差 tol=0.01）；`submit_answer` 终止。
- **沙箱**：`sandbox.py` 进程级约束（超时/截断/脱敏/cwd 锁定/仅 `data/` 读）。
- **回放**：`run.py --fake` 脚本直接提交标准答案，结果行带 `llm: fake` 标记。

## 4. 成功标准

1. `tests/` **7 项全过**（2026-11-01 基线，离线、无网络、无 `.env` 也能跑）。
2. `run.py --fake --limit 20` 回放 **20/20 全过**（`results/base-fake.jsonl`，
   20 行、20 个不同 task_id、全 `llm: fake`）。
3. 判分拒绝错误答案（`tests/test_pipeline.py` 同款断言：gold=40.0, submitted="40"
   在 tol=0.01 下通过；明显错误答案被拒）。
4. 沙箱四断言：`read_file` 越权逃逸拦截、超时/截断/脱敏/正常计算。

## 5. 明确边界（不证明什么）

- **不证明真实 LLM 能力**：`results/` 只有 `base-fake.jsonl`（管道回放）；
  本仓库**不含**任何"模型能力通过率"数字，能力声明需另跑真模型再写。
- **不证明安全边界**：沙箱是**进程级**约束，不是安全边界（无 seccomp/容器）；
  防恶意代码不够用。
- **不证明外推到全量数据**：数据只取 40 局前十对局（非全量转储），结论
  不外推到整场 Kaggle episode 集。
- **不证明通用 agent 能力**：所有"通过率/轮数/token 成本"只对该任务集有效。

## 6. 数据与复现

- 复现：
  ```bash
  python3 -m pytest tests/ -q                        # 7 passed
  python3 run.py --fake --limit 20                   # 20/20 回放全过
  python3 tasks/build_games_from_episodes.py 40      # 从官方转储重建 CSV（只读源）
  python3 tasks/build_tasks.py                       # 任务+标准答案由脚本算出
  ```
- 真跑（需 API 端点）：
  ```bash
  cp .env.example .env        # 填任意 OpenAI 兼容端点
  python3 run.py --config configs/base.yaml
  python3 run.py --config configs/variant_tool_hints.yaml
  ```
