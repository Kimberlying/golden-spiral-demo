---
name: golden-spiral-demo
description: Public showcase of the GoldenSpiral trading analysis skill. Demonstrates Fibonacci Moving Averages (5/13/21/34/55/144/233/623), Lookahead Differential Deduction, and Multi-Indicator Resonance (BOLL + KDJ + MACD) on NVIDIA (NVDA) Daily K-lines.
---

# GoldenSpiral — Public Demo Skill (English)

> **Public Showcase Notice**  
> This is the sanitized public demo of the **GoldenSpiral** skill. Full proprietary course cards, Level-2 order-book rules, and private strategy parameters are maintained in a separate private repository.

## Core Rules Demonstrated

1. **Fibonacci Moving Averages (`5, 13, 21, 34, 55, 144, 233, 623`)**
   - **`MA21` (Trim / Defense Line)**: Short-to-medium wave defense line. Closing decisively below `MA21` triggers position trimming.
   - **`MA34` (Medium Lifeline)**: Core medium-term bull/bear dividing line.
   - **`MA144` & `MA233` (Bull-Bear Lines)**: Long-term institutional support base.

2. **Lookahead Differential Deduction**
   - $\Delta \text{MA}(N) = (C_t - C_{t-N}) / N$. Compare current closing price $C_t$ with the historical deduction price $C_{t-N}$ to anticipate moving average inflection points before crossovers occur.

3. **Multi-Indicator Dip-Adding Resonance (`BOLL89` + `KDJ` + `MACD`)**
   - When price pulls back to major support (`MA144/233` and the **89-period Bollinger Band `BOLL(89, 2)` support zone**), **KDJ enters oversold passivation** (`J <= 10`, clamped to `[0, 100]`), and **MACD bearish momentum shrinks or turns upward**, it signals a high-probability zone to add positions.

## Execution
- `python3 demo.py NVDA --lang en` — Generates the 4-panel English showcase chart (`samples/nvda_demo_en.png`) and lookahead deduction table.

---
---

# GoldenSpiral (黄金螺旋) — 公开演示版 Skill (简体中文)

> **公开演示版说明**  
> 本文件为 **GoldenSpiral Skill** 的脱敏公开演示版入口，仅包含斐波那契均线簇、抵扣价差分推演及 `BOLL + KDJ + MACD` 多指标共振的示例逻辑。完整的盘口微观规则与内部资料保存在私有库中。

## 公开演示核心规则

1. **斐波那契均线簇 (`5, 13, 21, 34, 55, 144, 233, 623`)**
   - **`MA21`（21日减仓防守线）**：短中线波段防守线，有效跌破 `MA21` 触发减仓防守。
   - **`MA34`（34日生命线）**：中线多空强弱分水岭。
   - **`MA144` 与 `MA233`（牛熊分界线）**：大周期机构成本底座与回调强支撑。

2. **“向右看”抵扣价差分推演**
   - $\Delta \text{MA}(N) = (C_t - C_{t-N}) / N$。通过对比当前收盘价 $C_t$ 与 $N$ 日前抵扣价 $C_{t-N}$，提前预判均线助涨或压制拐点。

3. **多指标共振加仓 (`BOLL89` + `KDJ` + `MACD`)**
   - 当股价回踩大均线（`MA144/233`）并进入 **89周期布林带 `BOLL(89, 2)` 支撑带**企稳，同时 **KDJ 进入底部钝化区**（`J <= 10`，极值截断于 `[0, 100]`），且 **MACD 绿柱缩短或快慢线拐头**时，构成高胜率波段加仓区。

## 运行命令
- `python3 demo.py NVDA --lang zh` — 生成纯中文四宫格演示图表（`samples/nvda_demo_zh.png`）与中文抵扣价推演表。
