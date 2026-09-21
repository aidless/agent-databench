# agent-databench

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

## 待办

- [ ] 跑 base vs tool_hints 各 20 题 × 2 遍（留噪声底），把对比表贴进本 README
- [ ] 记录一个真实抓到的 agent 层 bug 进失败模式表
