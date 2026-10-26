#!/usr/bin/env python3
"""
GoldenSpiral — Public Showcase Demo
Target Example: NVIDIA (NVDA) Daily K-Line + Fibonacci MAs + BOLL + KDJ + MACD

Usage:
  python3 demo.py                  # Generates both pure English and pure Chinese charts
  python3 demo.py NVDA --lang en   # Pure English console output
  python3 demo.py NVDA --lang zh   # Pure Chinese console output
"""

import argparse
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

MA_PERIODS = [5, 13, 21, 34, 55, 144, 233, 623]
MA_COLORS = {
    5: '#FFFFFF',    # White: Ultra-short momentum
    13: '#FFD700',   # Gold: Short-term trend
    21: '#FF00FF',   # Magenta (Bold): Wave defense / trim line
    34: '#00FF66',   # Green (Bold): Medium-term lifeline
    55: '#00FFFF',   # Cyan: Medium trend
    144: '#FF8800',  # Orange (Bold): Bull/Bear boundary
    233: '#FF3333',  # Red (Bold): Long-term bull/bear cycle
    623: '#7B68EE',  # SlateBlue: Secular cycle
}


def load_stock_data(symbol="NVDA", bars=800, lang="en"):
    """Load real NVDA daily data from local snapshot or live via AKShare."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_csv = os.path.join(base_dir, 'data', 'nvda_daily.csv')

    if symbol.upper() == "NVDA" and os.path.exists(cache_csv):
        if lang == "zh":
            print(f"[*] 正在读取本地英伟达 (NVDA) 日线数据集: {cache_csv}")
        else:
            print(f"[*] Loading cached NVDA daily dataset: {cache_csv}")
        df = pd.read_csv(cache_csv)
        return df.tail(bars).reset_index(drop=True)

    import akshare as ak
    if symbol.isalpha():
        if lang == "zh":
            print(f"[*] 正在通过 AKShare 在线拉取美股 [{symbol.upper()}] 前复权日线...")
        else:
            print(f"[*] Fetching US stock [{symbol.upper()}] forward-adjusted daily data via AKShare...")
        df = ak.stock_us_daily(symbol=symbol.upper(), adjust='qfq')
    else:
        code = symbol.lower()
        if not code.startswith(('sh', 'sz', 'bj')):
            code = f"sh{code}" if code.startswith('6') else f"sz{code}"
        if lang == "zh":
            print(f"[*] 正在通过 AKShare 在线拉取 A 股 [{code}] 前复权日线...")
        else:
            print(f"[*] Fetching A-share [{code}] forward-adjusted daily data via AKShare...")
        df = ak.stock_zh_a_hist_tx(symbol=code, start_date="20220101", adjust="qfq")

    df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
    df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').tail(bars).reset_index(drop=True)

    if symbol.upper() == "NVDA":
        os.makedirs(os.path.dirname(cache_csv), exist_ok=True)
        df.to_csv(cache_csv, index=False)
    return df


def compute_all_indicators(df):
    """Compute Fibonacci MAs, BOLL(89,2), Passivated KDJ(14,3,3), and MACD(12,26,9)."""
    df = df.copy()

    # 1. Fibonacci Moving Averages
    for p in MA_PERIODS:
        df[f'MA{p}'] = df['close'].rolling(window=p, min_periods=1).mean()

    # 2. Bollinger Bands (BOLL 89, 2)
    df['BOLL_MID'] = df['close'].rolling(window=89, min_periods=1).mean()
    boll_std = df['close'].rolling(window=89, min_periods=1).std().fillna(0)
    df['BOLL_UP'] = df['BOLL_MID'] + 2.0 * boll_std
    df['BOLL_LOW'] = df['BOLL_MID'] - 2.0 * boll_std

    # 3. Passivated KDJ (14, 3, 3) clamped to [0, 100]
    low_n = df['low'].rolling(window=14, min_periods=1).min()
    high_n = df['high'].rolling(window=14, min_periods=1).max()
    denom = (high_n - low_n).replace(0, np.nan)
    rsv = ((df['close'] - low_n) / denom * 100).fillna(50.0).clip(0, 100)

    k_list, d_list, j_list = [], [], []
    k_val, d_val = 50.0, 50.0
    for r in rsv:
        k_val = np.clip((2.0 / 3.0) * k_val + (1.0 / 3.0) * r, 0, 100)
        d_val = np.clip((2.0 / 3.0) * d_val + (1.0 / 3.0) * k_val, 0, 100)
        j_val = np.clip(3.0 * k_val - 2.0 * d_val, 0, 100)
        k_list.append(k_val)
        d_list.append(d_val)
        j_list.append(j_val)
    df['K'], df['D'], df['J'] = k_list, d_list, j_list

    # 4. MACD (12, 26, 9)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['DIF'] = ema12 - ema26
    df['DEA'] = df['DIF'].ewm(span=9, adjust=False).mean()
    df['MACD'] = (df['DIF'] - df['DEA']) * 2.0

    return df


def deduce_lookahead(df):
    """Calculate Lookahead Deduction prices for each Fibonacci MA."""
    latest_close = df['close'].iloc[-1]
    n_bars = len(df)
    deductions = []
    for p in MA_PERIODS:
        idx = max(0, n_bars - p)
        deduct_price = df['close'].iloc[idx]
        deduct_date = df['date'].iloc[idx]
        diff = latest_close - deduct_price
        deductions.append({
            'period': p,
            'idx': idx,
            'deduct_date': deduct_date,
            'deduct_price': deduct_price,
            'diff': diff,
            'status_en': "Bullish Support (Close > Deduct)" if diff >= 0 else "Bearish Pressure (Close < Deduct)",
            'status_zh': "向上助涨 (现价 > 抵扣价)" if diff >= 0 else "向下压制 (现价 < 抵扣价)"
        })
    return deductions


def plot_showcase_chart(df, deductions, out_path, symbol="NVDA", view_bars=120, lang="en"):
    """Plot a 4-panel dark-theme chart in either 100% pure English or 100% pure Chinese."""
    if lang == "zh":
        plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
    else:
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica', 'sans-serif']
    plt.rcParams['axes.unicode_minus'] = False

    sub = df.iloc[-view_bars:].reset_index(drop=True)
    offset = len(df) - len(sub)

    fig = plt.figure(figsize=(17, 12), facecolor='#0d1117')
    gs = fig.add_gridspec(4, 1, height_ratios=[3.2, 1.15, 1.15, 1.15], hspace=0.10)

    ax_main = fig.add_subplot(gs[0], facecolor='#0d1117')
    ax_boll = fig.add_subplot(gs[1], facecolor='#0d1117', sharex=ax_main)
    ax_kdj = fig.add_subplot(gs[2], facecolor='#0d1117', sharex=ax_main)
    ax_macd = fig.add_subplot(gs[3], facecolor='#0d1117', sharex=ax_main)

    # --- Panel 1: Candlesticks + Fibonacci MAs + Action Annotations ---
    for i, row in sub.iterrows():
        is_up = row['close'] >= row['open']
        color = '#ff3b30' if is_up else '#00e676'
        ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.9)
        body_low = min(row['open'], row['close'])
        body_h = max(abs(row['close'] - row['open']), 0.15)
        ax_main.add_patch(Rectangle((i - 0.32, body_low), 0.64, body_h,
                                    facecolor=color if is_up else '#0d1117',
                                    edgecolor=color, linewidth=0.9))

    for p in [5, 13, 21, 34, 55, 144, 233]:
        lw = 2.2 if p in (21, 34, 144, 233) else 1.0
        if lang == "zh":
            lbl = {
                21: "MA21 (21日减仓防守线)",
                34: "MA34 (34日生命线)",
                144: "MA144 (144日牛熊线)",
                233: "MA233 (233日牛熊线)"
            }.get(p, f"MA{p}")
        else:
            lbl = {
                21: "MA21 (Trim / Defense Line)",
                34: "MA34 (Medium Lifeline)",
                144: "MA144 (Bull-Bear Line)",
                233: "MA233 (Long-Term Cycle)"
            }.get(p, f"MA{p}")
        ax_main.plot(sub.index, sub[f'MA{p}'], color=MA_COLORS[p], linewidth=lw, label=lbl, alpha=0.92)

    # Mark interval deduction points inside the visible window
    for item in deductions:
        rel_idx = item['idx'] - offset
        if 0 <= rel_idx < len(sub) and item['period'] in (21, 34, 55):
            p = item['period']
            ax_main.axvline(rel_idx, color=MA_COLORS[p], linestyle=':', linewidth=0.8, alpha=0.6)
            ax_main.scatter([rel_idx], [item['deduct_price']], color=MA_COLORS[p], s=40, zorder=6)
            tag = f"抵扣{p}" if lang == "zh" else f"Deduct-{p}"
            ax_main.text(rel_idx, item['deduct_price'] * 1.015, tag, color=MA_COLORS[p], fontsize=8, ha='center')

    # Trim Signal Callouts (Break below MA21)
    trim_candidates = sub[(sub['close'] < sub['MA21']) & (sub['close'].shift(1) >= sub['MA21'].shift(1)) & (sub.index > 15)]
    if not trim_candidates.empty:
        for idx_t in [trim_candidates.index[0], trim_candidates.index[-1]]:
            row_t = sub.loc[idx_t]
            text_t = (f"跌破 21 日线 -> 减仓防守\n(${row_t['close']:.1f})"
                      if lang == "zh" else
                      f"Break Below MA21 -> Trim Position\n(${row_t['close']:.1f})")
            ax_main.annotate(
                text_t,
                xy=(idx_t, row_t['high']),
                xytext=(max(2, idx_t - 15), row_t['high'] + 10),
                arrowprops=dict(facecolor='#ff9500', edgecolor='#ff9500', arrowstyle='->', lw=1.5),
                fontsize=8.5, fontweight='bold', color='#ff9500',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#ff9500', alpha=0.92)
            )

    # Dip-Add Signal Callouts (KDJ Passivated + BOLL89 Support + MACD Turn)
    dip_candidates = sub[(sub['J'] <= 5.0) & (sub['low'] <= sub['BOLL_MID']) & (sub.index > 30)]
    if not dip_candidates.empty:
        chosen_dips = [dip_candidates.index[0]]
        for idx_d in dip_candidates.index:
            if idx_d - chosen_dips[-1] > 18:
                chosen_dips.append(idx_d)
        for k_i, idx_d in enumerate(chosen_dips[:2]):
            row_d = sub.loc[idx_d]
            text_d = (f"KDJ钝化 + BOLL89支撑 + MACD企稳\n多指标共振加仓 (${row_d['close']:.1f})"
                      if lang == "zh" else
                      f"KDJ Passivated + BOLL89 + MACD Turn\nMulti-Indicator Add Zone (${row_d['close']:.1f})")
            x_text_pos = max(2, idx_d - 24) if k_i == 0 else min(len(sub) - 32, idx_d + 1)
            ax_main.annotate(
                text_d,
                xy=(idx_d, row_d['low']),
                xytext=(x_text_pos, row_d['low'] - 13),
                arrowprops=dict(facecolor='#00e676', edgecolor='#00e676', arrowstyle='->', lw=1.5),
                fontsize=8.5, fontweight='bold', color='#00e676',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#00e676', alpha=0.92)
            )

    if lang == "zh":
        ax_main.set_title(f"GoldenSpiral (黄金螺旋) — 英伟达 ({symbol.upper()}) 日K线与多指标共振推演示例",
                          color='#e6edf3', fontsize=14, pad=12, fontweight='bold')
        ax_main.set_ylabel("价格 (USD)", color='#8b949e', fontsize=9.5)
    else:
        ax_main.set_title(f"GoldenSpiral — {symbol.upper()} Daily K-Line, Fibonacci MAs & Multi-Indicator Resonance",
                          color='#e6edf3', fontsize=14, pad=12, fontweight='bold')
        ax_main.set_ylabel("Price (USD)", color='#8b949e', fontsize=9.5)

    ax_main.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8.5)
    ax_main.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_main.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 2: BOLL (Bollinger Bands 89, 2) ---
    if lang == "zh":
        ax_boll.plot(sub.index, sub['close'], color='#FFFFFF', linewidth=1.1, label='收盘价')
        ax_boll.plot(sub.index, sub['BOLL_UP'], color='#ff6b6b', linestyle='--', linewidth=1.0, label='BOLL89 上轨')
        ax_boll.plot(sub.index, sub['BOLL_MID'], color='#ffd166', linewidth=1.1, label='BOLL89 中轨 (MA89)')
        ax_boll.plot(sub.index, sub['BOLL_LOW'], color='#00e676', linestyle='--', linewidth=1.2, label='BOLL89 下轨')
        ax_boll.set_ylabel("BOLL (89, 2)", color='#8b949e', fontsize=9)
    else:
        ax_boll.plot(sub.index, sub['close'], color='#FFFFFF', linewidth=1.1, label='Close Price')
        ax_boll.plot(sub.index, sub['BOLL_UP'], color='#ff6b6b', linestyle='--', linewidth=1.0, label='BOLL89 Upper Band')
        ax_boll.plot(sub.index, sub['BOLL_MID'], color='#ffd166', linewidth=1.1, label='BOLL89 Middle (MA89)')
        ax_boll.plot(sub.index, sub['BOLL_LOW'], color='#00e676', linestyle='--', linewidth=1.2, label='BOLL89 Lower Band')
        ax_boll.set_ylabel("BOLL (89, 2)", color='#8b949e', fontsize=9)

    ax_boll.fill_between(sub.index, sub['BOLL_LOW'], sub['BOLL_UP'], color='#58a6ff', alpha=0.08)
    ax_boll.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_boll.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_boll.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 3: KDJ (14, 3, 3 Passivated 0~100) ---
    ax_kdj.plot(sub.index, sub['K'], color='#FFFFFF', linewidth=1.0, label='K')
    ax_kdj.plot(sub.index, sub['D'], color='#FFD700', linewidth=1.0, label='D')
    if lang == "zh":
        ax_kdj.plot(sub.index, sub['J'], color='#FF00FF', linewidth=1.3, label='J (0~100 极值截断)')
        ax_kdj.fill_between(sub.index, 0, 20, where=(sub['J'] <= 10), color='#00e676', alpha=0.20, label='底部钝化区 (J <= 10)')
        ax_kdj.set_ylabel("KDJ (钝化指标)", color='#8b949e', fontsize=9)
    else:
        ax_kdj.plot(sub.index, sub['J'], color='#FF00FF', linewidth=1.3, label='J (Clamped 0~100)')
        ax_kdj.fill_between(sub.index, 0, 20, where=(sub['J'] <= 10), color='#00e676', alpha=0.20, label='Oversold Passivation Zone')
        ax_kdj.set_ylabel("KDJ (14, 3, 3)", color='#8b949e', fontsize=9)

    ax_kdj.axhline(80, color='#ff3b30', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.axhline(20, color='#00e676', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.set_ylim(-5, 105)
    ax_kdj.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_kdj.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_kdj.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 4: MACD (12, 26, 9) ---
    macd_colors = ['#ff3b30' if m >= 0 else '#00e676' for m in sub['MACD']]
    if lang == "zh":
        ax_macd.bar(sub.index, sub['MACD'], color=macd_colors, width=0.6, alpha=0.75, label='MACD 红绿柱')
        ax_macd.plot(sub.index, sub['DIF'], color='#FFFFFF', linewidth=1.0, label='DIF 快线')
        ax_macd.plot(sub.index, sub['DEA'], color='#FFD700', linewidth=1.0, label='DEA 慢线')
        ax_macd.set_ylabel("MACD (动能)", color='#8b949e', fontsize=9)
    else:
        ax_macd.bar(sub.index, sub['MACD'], color=macd_colors, width=0.6, alpha=0.75, label='MACD Histogram')
        ax_macd.plot(sub.index, sub['DIF'], color='#FFFFFF', linewidth=1.0, label='DIF (Fast)')
        ax_macd.plot(sub.index, sub['DEA'], color='#FFD700', linewidth=1.0, label='DEA (Slow)')
        ax_macd.set_ylabel("MACD (12,26,9)", color='#8b949e', fontsize=9)

    ax_macd.axhline(0, color='#8b949e', linewidth=0.6, alpha=0.5)
    ax_macd.legend(loc='upper left', ncol=3, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_macd.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_macd.tick_params(colors='#8b949e')

    tick_step = max(1, len(sub) // 10)
    tick_positions = list(range(0, len(sub), tick_step))
    ax_macd.set_xticks(tick_positions)
    ax_macd.set_xticklabels([sub['date'].iloc[i] for i in tick_positions], rotation=15, fontsize=8.5, color='#8b949e')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=160, bbox_inches='tight', facecolor='#0d1117')
    plt.close(fig)


def print_report(df, deductions, symbol="NVDA", lang="en"):
    """Print pure English or pure Chinese console report."""
    latest = df.iloc[-1]
    if lang == "zh":
        print("=" * 74)
        print(f"  GoldenSpiral (黄金螺旋) 公开演示版 — {symbol.upper()} 日K线与抵扣价推演")
        print("=" * 74)
        print(f"\n[+] 最新交易日行情 ({latest['date']}):")
        print(f"    收盘价: ${latest['close']:.2f} | MA21(减仓线): ${latest['MA21']:.2f} | MA34(生命线): ${latest['MA34']:.2f}")
        print(f"    BOLL89中轨: ${latest['BOLL_MID']:.2f} | BOLL89下轨: ${latest['BOLL_LOW']:.2f} | KDJ(J值): {latest['J']:.1f} | MACD柱: {latest['MACD']:.2f}")
        print("\n[+] “向右看”抵扣价差分推演表 (ΔMA = (现价 - 抵扣价) / N):")
        print("-" * 74)
        for d in deductions:
            print(f"    MA({d['period']:3d}) | 抵扣日期: {d['deduct_date']} | 抵扣价: ${d['deduct_price']:7.2f} | "
                  f"差值: {d['diff']:+7.2f} -> {d['status_zh']}")
        print("-" * 74)
    else:
        print("=" * 78)
        print(f"  GoldenSpiral Public Showcase — {symbol.upper()} Daily K-Line & Lookahead Deduction")
        print("=" * 78)
        print(f"\n[+] Latest Market Bar ({latest['date']}):")
        print(f"    Close: ${latest['close']:.2f} | MA21 (Trim Line): ${latest['MA21']:.2f} | MA34 (Lifeline): ${latest['MA34']:.2f}")
        print(f"    BOLL89 Mid: ${latest['BOLL_MID']:.2f} | BOLL89 Lower: ${latest['BOLL_LOW']:.2f} | KDJ (J): {latest['J']:.1f} | MACD Hist: {latest['MACD']:.2f}")
        print("\n[+] Lookahead Differential Deduction Table (ΔMA = (Close - Deduct) / N):")
        print("-" * 78)
        for d in deductions:
            print(f"    MA({d['period']:3d}) | Deduct Date: {d['deduct_date']} | Deduct Price: ${d['deduct_price']:7.2f} | "
                  f"Diff: {d['diff']:+7.2f} -> {d['status_en']}")
        print("-" * 78)


def main():
    parser = argparse.ArgumentParser(description="GoldenSpiral Public Demo")
    parser.add_argument("symbol", nargs="?", default="NVDA", help="Stock symbol (default: NVDA)")
    parser.add_argument("--lang", choices=["en", "zh", "both"], default="both", help="Output language: en, zh, or both")
    args = parser.parse_args()

    df = load_stock_data(symbol=args.symbol, bars=800, lang="en" if args.lang != "zh" else "zh")
    df = compute_all_indicators(df)
    deductions = deduce_lookahead(df)

    base_dir = os.path.dirname(os.path.abspath(__file__))

    if args.lang in ("en", "both"):
        print_report(df, deductions, symbol=args.symbol, lang="en")
        out_en = os.path.join(base_dir, 'samples', 'nvda_demo_en.png')
        plot_showcase_chart(df, deductions, out_en, symbol=args.symbol, view_bars=120, lang="en")
        print(f"[+] English chart saved to: {out_en}\n")

    if args.lang in ("zh", "both"):
        print_report(df, deductions, symbol=args.symbol, lang="zh")
        out_zh = os.path.join(base_dir, 'samples', 'nvda_demo_zh.png')
        plot_showcase_chart(df, deductions, out_zh, symbol=args.symbol, view_bars=120, lang="zh")
        print(f"[+] 中文演示图表已生成: {out_zh}\n")


if __name__ == '__main__':
    main()
