---
name: golden-spiral-demo
description: Bilingual (EN/中文) public showcase of the GoldenSpiral (黄金螺旋) trading analysis skill. Demonstrates Fibonacci Moving Averages (5/13/21/34/55/144/233/623), Lookahead Deduction (抵扣价推演), and Multi-Indicator Resonance (BOLL + KDJ + MACD) on NVIDIA (NVDA) Daily K-lines.
---

# GoldenSpiral (黄金螺旋) — Public Demo Skill (EN / 中文)

> **Public Showcase Notice / 公开版说明**  
> This is the sanitized public demo of the **GoldenSpiral** skill. Full proprietary course cards, Level-2 order-book rules, and private strategy parameters are maintained in a separate private repository.  
> 本文件为 **GoldenSpiral Skill** 的公开演示版入口，仅包含斐波那契均线、抵扣价差分推演及 `BOLL + KDJ + MACD` 多指标共振的示例逻辑。

## Core Rules Demonstrated / 公开演示核心规则

1. **Fibonacci Moving Averages / 斐波那契均线簇 (`5, 13, 21, 34, 55, 144, 233, 623`)**
   - **`MA21` (Trim Line / 减仓线)**: Short-to-medium wave defense line. Break below `MA21` triggers position trimming (`跌破 21 日线减仓`).
   - **`MA34` (Lifeline / 生命线)**: Core medium-term bull/bear dividing line.
   - **`MA144` & `MA233` (Bull-Bear Lines / 牛熊分界线)**: Long-term institutional support base.

2. **Lookahead Differential Deduction / “向右看”抵扣价推演**
   - $\Delta \text{MA}(N) = (C_t - C_{t-N}) / N$. Compare current price $C_t$ with the historical deduction price $C_{t-N}$ to anticipate MA inflection points.

3. **Multi-Indicator Dip-Adding Resonance / 多指标共振加仓 (`KDJ` + `BOLL` + `MACD`)**
   - When price pulls back to major support (`MA144/233` or **`BOLL` Lower Band**), **`KDJ` enters oversold passivation** (`J` near `0`, clamped to `[0, 100]`), and **`MACD` bearish momentum shrinks/turns up**, it signals a high-probability zone to add position (`指标共振加仓`).

## Execution / 运行命令
- `python3 demo.py` — Generates the 4-panel bilingual showcase chart (`samples/nvda_demo_chart.png`) and lookahead deduction table for `NVDA`.
