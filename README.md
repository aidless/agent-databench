# agent-databench

> **English TL;DR**: A CSV data-analysis agent with a hand-written tool-calling loop and a programmatic scoring harness; the 20 gold-answer tasks are generated from a committed 40-row CC0 game dump. Every committed result is an offline `--fake` plumbing replay (no model calls), and the real-LLM A/B comparison between `base` and `tool_hints` is **NOT YET MEASURED** because no compatible endpoint is available.

[![CI](https://github.com/aidless/agent-databench/actions/workflows/ci.yml/badge.svg)](https://github.com/aidless/agent-databench/actions/workflows/ci.yml)

一个**带评测 harness 的 CSV 数据分析 agent**：手写 tool-calling 循环（不依赖
agent 框架），20 个有标准答案的任务，每次改动都能量出「通过率 / 轮数 / token
成本」三个数。

## 数据出处

`data/games.csv` = 本地 flatten 的 **Kaggle 官方 CC0 episode 转储**（2026-09-19
公开发布，取 40 局前十对局）。列：双方席位、终局 money、胜者、纯 PASS 回合数、
有动作回合数、seed。重生成：

```bash
.venv/bin/python tasks/build_games_from_episodes.py 40   # 只读源目录
```

所有派生数字在本仓脚本内现场计算，不引用任何外部账本（评测答案同理，见下）。


## 为什么不用 LangChain

因为框架把我最想测的东西藏起来了：状态怎么管、失败怎么回喂、成本花在第几轮。
harness 的产出不是"能跑的 demo"，而是**配置对比表**（见 `results/`）——同一
任务集，`configs/base.yaml` vs `configs/variant_tool_hints.yaml`，差异全部
归因到 prompt 层，没有框架噪声。

## 架构

```
question ──> loop.py（消息状态机, max_turns 封顶）
                │  llm.chat(messages, tools)
                ▼
        run_python ──> sandbox.py  超时 15s / 输出截断 4KB / 剥离含
        read_file  ──> 仅 data/    KEY|TOKEN|SECRET 的环境变量 / cwd 锁定
        submit_answer ──> 终止, scoring.py 程序化判分
```

## 目录结构

```
agent-databench/
├── agent_databench/        # 核心包：loop.py(状态机) sandbox.py(进程级约束)
│   │                       #   scoring.py(程序化判分) tools.py(工具注册) llm.py(LLM 适配)
├── tasks/
│   ├── build_games_from_episodes.py  # 官方 episode 转储 → data/games.csv
│   └── build_tasks.py                # CSV → tasks.jsonl（答案由脚本现场计算）
├── tasks/tasks.jsonl       # 20 个带标准答案的任务
├── configs/                # base.yaml（对照）/ variant_tool_hints.yaml（实验）
├── data/games.csv          # 40 局前十对局（CC0 转储展平）
├── results/                # 运行结果 jsonl（每行含 llm 名，fake 行可识别）
├── tests/                  # pytest：管道端到端 / 判分拒绝错误答案 / 沙箱四断言
└── run.py                  # 入口：--fake 管道自检 / --config 真跑
```

## 快速开始

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tasks/build_games_from_episodes.py 40  # 可选：从官方转储重建 CSV
.venv/bin/python tasks/build_tasks.py        # 任务+标准答案由脚本从 CSV 算出
.venv/bin/python run.py --fake --limit 3     # 离线管道自检（不考模型能力）
cp .env.example .env                          # 填任意 OpenAI 兼容端点
.venv/bin/python run.py --config configs/base.yaml
.venv/bin/python run.py --config configs/variant_tool_hints.yaml
```

## Benchmark (offline pipeline verification)

`benchmarks/bench_pipeline.py` runs the real test suite and checks the committed
`--fake` replay result — no model, no network:

```bash
python benchmarks/bench_pipeline.py   # RESULT: PASS
```

It verifies the 7-test suite and that `results/base-fake.jsonl` holds **20/20**
passed across 20 distinct tasks, every row marked `llm: fake`. This is the honest
claim the harness can make: the plumbing (loop/sandbox/scoring/report) verifies
end-to-end on 20 standard-answer tasks, and no capability number leaks into a
claim (see `PREREG.md` §5).

## 测试

```bash
.venv/bin/python -m pytest tests/ -q        # 7 项全部通过（2026-11-01 基线）
```

测试覆盖：20 任务集的存在性、`--fake` 管道端到端、判分对错误答案的拒绝、
`read_file` 越权逃逸拦截、沙箱超时/截断/脱敏/正常计算。测试不依赖网络与模型，
无 `.env` 也能跑。

## 证明什么 / 不证明什么

**证明什么**：手写 tool-calling 循环 + 进程级沙箱，能在 20 个带标准答案的
CSV 分析任务上端到端跑通判分管道；A/B 配置差异（`base` vs `tool_hints`）
可归因到 prompt 层；`--fake` 管道回放证明 loop/沙箱/判分/报告接线正确。

**不证明什么**：
- 未跑真实 LLM 对比表（`results/` 只有 `base-fake.jsonl`，是管道回放）——本
  README 与仓库**不含**任何"模型能力通过率"数字，能力声明需另跑真模型再写。
- 沙箱是**进程级**约束（超时/截断/脱敏），**不是**安全边界（无 seccomp/容器）：
  防失控刷爆会话够用，防恶意代码不够用。
- 标准答案由脚本从数据现场计算，但数据本身只取 40 局前十对局（非全量转储），
  结论不外推到整场 Kaggle episode 集。
- 所有"通过率/轮数/token 成本"指标只对该任务集有效，不是通用 agent 能力度量。

## Results（真实数字，如实标注）

| 结果 | 数字 | 证据 | 能否进能力声明 |
|---|---|---|---|
| 管道自检（`--fake` 回放，base 配置） | **20/20 通过，每题 2 轮，0 token** | `results/base-fake.jsonl`（`llm: fake` 标记） | **否**——只验证 loop/沙箱/判分接线 |
| 管道自检（`--fake --limit 3` 复跑） | `base / fake / 3题 / 100.0% / 2.0轮 / 0 token`，尾部打印 `NOTE: --fake validates plumbing only; not a capability result.` | 2026-11-10 实跑输出 | **否**（同上） |
| 单测 | 7 passed | `python3 -m pytest tests/ -q`（2026-11-10 实跑） | —（工程正确性） |
| **base vs tool_hints A/B（各 20 题 × 2 遍）** | **未跑** | 无真实 LLM 端点可用；`results/` 里没有任何带真实 `llm:` 标记的结果行 | — |

A/B 缺口如实记录：`configs/base.yaml` 与 `configs/variant_tool_hints.yaml` 的唯一
差异是 `tool_hints: false → true`（diff 已核），对比表设计就绪，但没有可用端点时
不产出任何"通过率/轮数/token"对比数字——`--fake` 回放的 100% 不是能力，不能
替代 A/B。此缺口对应下方待办第 1 条，保持未勾选。

## 诚实性约束（评测纪律）

- `--fake` 是**管道回放**：脚本直接提交标准答案，仅验证 loop/沙箱/判分接线，
  结果行带 `llm: fake` 标记，不允许出现在能力声明里。
- 标准答案由 `tasks/build_tasks.py` 从数据现场计算，不是手抄——数据变了
  评测集自动跟着变。
- 沙箱是**进程级**约束（超时/截断/脱敏），不是安全边界（无 seccomp/容器）。
  防"agent 失控刷爆会话"够用，防恶意代码不够用，边界写在这。

## 失败模式手册（边跑边补）

| 症状 | 根因 | 修法 |
|---|---|---|
| max_turns 不收敛 | 工具报错被当成"重试信号"死循环 | 报错回喂时附带第 n 次提示，n≥2 直接终止 |
| 数值对但差 10 倍 | DictReader 列全是字符串，模型忘了 cast | tool_hints 变体专治这个，A/B 见真章 |
| 幻觉列名 | 没先 read_file 就盲写代码 | 系统 prompt 要求首轮必须 inspect |
| 统计脚本把每局全记成"有动作" | episode 动作是嵌套结构 `{farmer:[], hands:[[]], market:[]}`，扁平比较漏掉 list 套 list | 递归展平后再判 PASS；测试用真实局结构 |

## 复算（数字从哪来）

仓库内所有数字**当场算，不引外部账本**。逐项复算命令：

| 数字 | 复算命令 | 来源 |
|---|---|---|
| 40 局前十对局 CSV | `.venv/bin/python tasks/build_games_from_episodes.py 40` | Kaggle 官方 CC0 episode 转储（2026-09-19） |
| 20 个标准答案任务 | `.venv/bin/python tasks/build_tasks.py` | 从 `data/games.csv` 现场计算 |
| 20 项管道回放全过 | `.venv/bin/python run.py --fake` | `results/base-fake.jsonl`（20 行，`llm: fake`） |
| 7 项测试全过 | `.venv/bin/python -m pytest tests/ -q` | `tests/` |

示例：`results/base-fake.jsonl` 第 1 行 `t01`，gold=40.0，submitted="40"，判分
`score_answer` 在 `tol=0.01` 下通过（`tests/test_pipeline.py` 的同款断言）。

## Limits

- **无真实 LLM 结果**：本仓所有已提交结果行都是 `llm: fake` 管道回放；base vs
  tool_hints 的 A/B 对比表在拿到真实 OpenAI 兼容端点前无法产出（NOT_FILLABLE）。
- 沙箱是进程级约束（超时/截断/脱敏），不是安全边界——防失控刷爆够用，防恶意代码不够。
- 20 题任务集来自单一数据源（40 局 CC0 episode 转储），结论外推到其他 CSV 任务域
  没有任何证据。

## 待办

- [ ] 跑 base vs tool_hints 各 20 题 × 2 遍（留噪声底），把对比表贴进本 README
- [ ] 记录一个真实抓到的 agent 层 bug 进失败模式表

## U1 results and reproducibility (recomputed 2026-11-11)

All numbers below were recomputed from committed files in this repository at the
time of the U1 content pass; no external ledger or remembered value was used.

| Recomputed result | Value | Source (path:line) | Method |
|---|---|---|---|
| `data/games.csv` rows | 40 | `data/games.csv:1-41` | `csv.DictReader`, header + data rows |
| `data/games.csv` columns | 12 | `data/games.csv:1` | `episode_id, seed, act_timeout_s, team_a, team_b, money_a, money_b, winner, pass_turns_a, pass_turns_b, act_turns_a, act_turns_b` |
| Committed result lines | 20 | `results/base-fake.jsonl:1-20` | count of JSONL lines |
| Lines with `passed: true` | 20/20 | `results/base-fake.jsonl:1-20` | sum of boolean `passed` |
| LLM marker on every line | fake | `results/base-fake.jsonl:1-20` | distinct `llm` values |
| Turns per line | 2 | `results/base-fake.jsonl:1-20` | distinct `turns` values |
| Prompt / completion tokens | 0 / 0 | `results/base-fake.jsonl:1-20` | sum of `prompt_tokens`, `completion_tokens` |

**Quickstart command actually executed for this pass** (offline, zero dependencies):

```bash
python3 run.py --fake --limit 3
# [PASS] t01 turns=2 gold=40 got='40' ... t03 turns=2
# | base | fake | 3 | 100.0% | 2.0 | 0 | 0 |
# NOTE: --fake validates plumbing only; not a capability result.
```

That smoke run rewrites `results/base-fake.jsonl` with 3 lines; the committed
20-line version was restored with `git checkout -- results/base-fake.jsonl`
before this README was staged, so this commit changes documentation only.

**NOT YET MEASURED**: the `configs/base.yaml` vs `configs/variant_tool_hints.yaml`
A/B run (20 tasks x 2 repeats per config). It needs a real OpenAI-compatible
endpoint; `--fake` replays are plumbing checks and are never reported as
capability. Reproduce once an endpoint exists:

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python tasks/build_tasks.py
cp .env.example .env   # fill any OpenAI-compatible endpoint
.venv/bin/python run.py --config configs/base.yaml
.venv/bin/python run.py --config configs/variant_tool_hints.yaml
```

<!-- figure: pending real measurement -->

## 验收标准与复算

**判据**：本仓判为合格的条件是 `python3 eval/run_cases.py` 通过率必须为 100%（20/20），且 `make eval` 退出码必须为 0；任何一条失败即判为不合格。

题库 `eval/cases.jsonl` 共 20 条，每条形如 `id/axis/question/expected/mode/verify/source`，其中 17 条是 `expr`（真调本仓 API / 真解析 `data/games.csv`、`tasks/tasks.jsonl`、`results/base-fake.jsonl`），2 条 `doc`（核对 README 自己的声明），1 条 `doc` 边界声明。期望值全部由脚本现场算出并固化，不抄文档。

| axis | 条数 | 考什么 |
|---|---|---|
| scoring/tolerance | 3 | `score_answer` 的 tol 边界（42.0±0.01 的通过/拒绝）、`kind=str` 大小写与空白无关 |
| data/csv | 3 | `games.csv` 行数 40、seat a 均值 102850.88、表头 12 列 |
| tasks/schema | 2 | `tasks.jsonl` 20 行且每行恰好五键、id 唯一；t20 的 `kind=str` 且 gold 属于 {a,b} |
| tasks/regeneration | 2 | `build_tasks.build` 从 CSV 重建的 20 条与已提交文件逐条相等、id 为 t01..t20 |
| tools/read_file | 2 | `../tasks/build_tasks.py` 越权读被拒且报 escapes；`games.csv` 首行表头正确 |
| sandbox | 3 | sleep(3) 在 timeout=1 下 timed_out；`*TOKEN*` 环境变量被剥离；20000 字符输出被截断并带标记 |
| loop | 3 | FakeLLM 端到端 submitted/2 轮/判分通过；不调工具 → max_turns；未知工具作为 observation 回喂后仍可 submit |
| results/replay | 1 | `base-fake.jsonl` 20 行、20 passed、20 个 task、全标 `llm: fake` |
| docs/claims | 1 | README 明确写了「进程级约束、不是安全边界」 |

```bash
python3 eval/run_cases.py                 # 逐条 PASS/FAIL，末行 20/20 cases passed
python3 eval/run_cases.py --save          # 同上，并重建 eval/run-report.json
python3 eval/run_cases.py --selftest      # 篡改 DB-01 期望值，必须变红（19/20）
```

**数字如何复算**：每题的 `verify` 就是复算代码本身——它现场执行本仓函数或重算 CSV，再与 `expected` 比对；`eval/run-report.json` 逐条记 `id/axis/ok/detail` 与 `failed_by_axis`，重跑 `--save` 即重建。所以「20/20」不是抄来的常量：改一行 `scoring.py`/`sandbox.py`/`build_tasks.py`，对应题目立刻变红。`--selftest` 是这套题的非空性反证（篡改一条必须 19/20）。

**失败归因**：`run_cases.py` 失败时按 axis 汇总，格式为 `<axis>: <n> 条 —— <ID 列表>`，并按下面的映射定位模块：

| 失败的 axis | 对应模块 |
|---|---|
| scoring/tolerance | `agent_databench/scoring.py`（判分容差/类型分支） |
| tools/read_file | `agent_databench/tools.py`（data/ 越权拦截） |
| sandbox | `agent_databench/sandbox.py`（超时/截断/环境变量脱敏） |
| loop | `agent_databench/loop.py` + `agent_databench/llm.py`（轮数上限、工具错误回喂） |
| data/csv、tasks/* | `data/games.csv`、`tasks/build_tasks.py`、`tasks/tasks.jsonl`（数据或生成脚本漂移） |
| results/replay | `results/base-fake.jsonl`（提交的回放结果被改写） |
| docs/claims | `README.md`（声明与实现不一致） |

`make eval` 同时跑本题库与既有 7 项 pytest；两者都过才返回 0。
