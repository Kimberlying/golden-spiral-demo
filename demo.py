#!/usr/bin/env python3
"""
GoldenSpiral (黄金螺旋) — Public Showcase Demo (Bilingual EN / 中文)
Target Example: NVIDIA (NVDA) Daily K-Line + Fibonacci MAs + BOLL + KDJ + MACD

Demonstrates:
1. Fibonacci Moving Average Matrix (MA 5, 13, 21, 34, 55, 144, 233, 623)
2. Lookahead Differential Deduction (间隔线抵扣价推演: ΔMA = (Close - Deduct) / N)
3. Multi-Indicator Resonance Example on NVDA:
   - Trim / Reduce Position (减仓): Price breaks below MA21
   - Add Position / Buy Dip (加仓): KDJ oversold passivation + BOLL lower band + MACD momentum turn
"""

import os
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# Configure CJK & English fonts
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

MA_PERIODS = [5, 13, 21, 34, 55, 144, 233, 623]
MA_COLORS = {
    5: '#FFFFFF',    # White: Ultra-short momentum (5日线)
    13: '#FFD700',   # Gold: Short-term trend (13日线)
    21: '#FF00FF',   # Magenta (Bold): Short/Med trim line (21日减仓防守线)
    34: '#00FF66',   # Green (Bold): Lifeline (34日生命线)
    55: '#00FFFF',   # Cyan: Medium trend (55日线)
    144: '#FF8800',  # Orange (Bold): Bull/Bear boundary (144日牛熊线)
    233: '#FF3333',  # Red (Bold): Long-term cycle (233日牛熊线)
    623: '#7B68EE',  # SlateBlue: Secular cycle (623日线)
}


def load_stock_data(symbol="NVDA", bars=800):
    """Load real NVDA daily data (from local snapshot or live via AKShare)."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_csv = os.path.join(base_dir, 'data', 'nvda_daily.csv')

    if symbol.upper() == "NVDA" and os.path.exists(cache_csv):
        print(f"[*] Loading cached NVDA daily dataset / 读取本地英伟达 (NVDA) 日线数据: {cache_csv}")
        df = pd.read_csv(cache_csv)
        return df.tail(bars).reset_index(drop=True)

    try:
        import akshare as ak
        if symbol.isalpha():
            print(f"[*] Fetching US stock [{symbol.upper()}] via AKShare / 在线拉取美股前复权日线...")
            df = ak.stock_us_daily(symbol=symbol.upper(), adjust='qfq')
        else:
            code = symbol.lower()
            if not code.startswith(('sh', 'sz', 'bj')):
                code = f"sh{code}" if code.startswith('6') else f"sz{code}"
            print(f"[*] Fetching A-share [{code}] via AKShare / 在线拉取 A 股前复权日线...")
            df = ak.stock_zh_a_hist_tx(symbol=code, start_date="20220101", adjust="qfq")

        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        df = df[['date', 'open', 'high', 'low', 'close', 'volume']].sort_values('date').tail(bars).reset_index(drop=True)

        if symbol.upper() == "NVDA":
            os.makedirs(os.path.dirname(cache_csv), exist_ok=True)
            df.to_csv(cache_csv, index=False)
        return df
    except Exception as e:
        raise RuntimeError(f"Failed to load data for {symbol}: {e}")


def compute_all_indicators(df):
    """Compute Fibonacci MAs, BOLL(20,2), Passivated KDJ(14,3,3), and MACD(12,26,9)."""
    df = df.copy()

    # 1. Fibonacci Moving Averages
    for p in MA_PERIODS:
        df[f'MA{p}'] = df['close'].rolling(window=p, min_periods=1).mean()

    # 2. Bollinger Bands (BOLL 20, 2)
    df['BOLL_MID'] = df['close'].rolling(window=20, min_periods=1).mean()
    boll_std = df['close'].rolling(window=20, min_periods=1).std().fillna(0)
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
    """Calculate Lookahead Deduction prices (间隔线抵扣价) for each Fibonacci MA."""
    latest_close = df['close'].iloc[-1]
    n_bars = len(df)
    deductions = []
    for p in MA_PERIODS:
        idx = max(0, n_bars - p)
        deduct_price = df['close'].iloc[idx]
        deduct_date = df['date'].iloc[idx]
        diff = latest_close - deduct_price
        status = "Bullish Slope / 向上助涨" if diff >= 0 else "Bearish Pressure / 向下压制"
        deductions.append({
            'period': p,
            'idx': idx,
            'deduct_date': deduct_date,
            'deduct_price': deduct_price,
            'diff': diff,
            'status': status
        })
    return deductions


def plot_nvda_showcase(df, deductions, out_path, symbol="NVDA", view_bars=120):
    """Plot 4-panel dark-theme chart: Daily K + Fib MAs | BOLL | KDJ | MACD."""
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
        lbl = f"MA{p}"
        if p == 21:
            lbl = "MA21 (Trim Line / 减仓线)"
        elif p == 34:
            lbl = "MA34 (Lifeline / 生命线)"
        elif p == 144:
            lbl = "MA144 (Bull-Bear / 牛熊线)"
        ax_main.plot(sub.index, sub[f'MA{p}'], color=MA_COLORS[p], linewidth=lw, label=lbl, alpha=0.92)

    # Mark interval deduction points inside the visible window
    for item in deductions:
        rel_idx = item['idx'] - offset
        if 0 <= rel_idx < len(sub) and item['period'] in (21, 34, 55):
            p = item['period']
            ax_main.axvline(rel_idx, color=MA_COLORS[p], linestyle=':', linewidth=0.8, alpha=0.6)
            ax_main.scatter([rel_idx], [item['deduct_price']], color=MA_COLORS[p], s=40, zorder=6)
            ax_main.text(rel_idx, item['deduct_price'] * 1.015, f"D{p}/抵{p}", color=MA_COLORS[p], fontsize=8, ha='center')

    # Find representative Trim (break below MA21) & Add (KDJ passivated + BOLL low + MACD turn) points
    trim_candidates = sub[(sub['close'] < sub['MA21']) & (sub['close'].shift(1) >= sub['MA21'].shift(1)) & (sub.index > 15)]
    if not trim_candidates.empty:
        # Pick clear examples
        for idx_t in [trim_candidates.index[0], trim_candidates.index[-1]]:
            row_t = sub.loc[idx_t]
            ax_main.annotate(
                f"Break MA21 -> Trim\n跌破21日线减仓 (${row_t['close']:.1f})",
                xy=(idx_t, row_t['high']),
                xytext=(max(2, idx_t - 14), row_t['high'] + 10),
                arrowprops=dict(facecolor='#ff9500', edgecolor='#ff9500', arrowstyle='->', lw=1.5),
                fontsize=8.5, fontweight='bold', color='#ff9500',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#ff9500', alpha=0.9)
            )

    dip_candidates = sub[(sub['J'] <= 5.0) & (sub['low'] <= sub['BOLL_LOW'] * 1.02) & (sub.index > 20)]
    if not dip_candidates.empty:
        # Pick the first major resonance bottom and the latest one
        chosen_dips = [dip_candidates.index[0]]
        for idx_d in dip_candidates.index:
            if idx_d - chosen_dips[-1] > 20:
                chosen_dips.append(idx_d)
        for idx_d in chosen_dips[:2]:
            row_d = sub.loc[idx_d]
            ax_main.annotate(
                f"KDJ Passivated + BOLL Low + MACD\n指标共振加仓区 (${row_d['close']:.1f})",
                xy=(idx_d, row_d['low']),
                xytext=(min(len(sub) - 28, idx_d - 6), row_d['low'] - 13),
                arrowprops=dict(facecolor='#00e676', edgecolor='#00e676', arrowstyle='->', lw=1.5),
                fontsize=8.5, fontweight='bold', color='#00e676',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#161b22', edgecolor='#00e676', alpha=0.9)
            )

    ax_main.set_title(
        f"GoldenSpiral (黄金螺旋) — {symbol.upper()} Daily K-Line & Multi-Indicator Resonance (日K与多指标共振示例)",
        color='#e6edf3', fontsize=13.5, pad=12, fontweight='bold'
    )
    ax_main.set_ylabel("Price (USD / 价格)", color='#8b949e', fontsize=9.5)
    ax_main.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8.5)
    ax_main.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_main.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 2: BOLL (Bollinger Bands 20, 2) ---
    ax_boll.plot(sub.index, sub['close'], color='#FFFFFF', linewidth=1.1, label='Close / 收盘价')
    ax_boll.plot(sub.index, sub['BOLL_UP'], color='#ff6b6b', linestyle='--', linewidth=1.0, label='BOLL Upper / 上轨')
    ax_boll.plot(sub.index, sub['BOLL_MID'], color='#ffd166', linewidth=1.0, label='BOLL Mid / 中轨(MA20)')
    ax_boll.plot(sub.index, sub['BOLL_LOW'], color='#00e676', linestyle='--', linewidth=1.2, label='BOLL Lower / 下轨支撑')
    ax_boll.fill_between(sub.index, sub['BOLL_LOW'], sub['BOLL_UP'], color='#58a6ff', alpha=0.08)
    ax_boll.set_ylabel("BOLL (布林带)", color='#8b949e', fontsize=9)
    ax_boll.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_boll.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_boll.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 3: KDJ (14, 3, 3 Passivated 0~100) ---
    ax_kdj.plot(sub.index, sub['K'], color='#FFFFFF', linewidth=1.0, label='K')
    ax_kdj.plot(sub.index, sub['D'], color='#FFD700', linewidth=1.0, label='D')
    ax_kdj.plot(sub.index, sub['J'], color='#FF00FF', linewidth=1.3, label='J (Passivated 0~100 / 极值钝化)')
    ax_kdj.axhline(80, color='#ff3b30', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.axhline(20, color='#00e676', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.fill_between(sub.index, 0, 20, where=(sub['J'] <= 10), color='#00e676', alpha=0.18, label='Oversold Passivation / 底部钝化区')
    ax_kdj.set_ylim(-5, 105)
    ax_kdj.set_ylabel("KDJ (钝化指标)", color='#8b949e', fontsize=9)
    ax_kdj.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_kdj.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_kdj.tick_params(colors='#8b949e', labelbottom=False)

    # --- Panel 4: MACD (12, 26, 9) ---
    macd_colors = ['#ff3b30' if m >= 0 else '#00e676' for m in sub['MACD']]
    ax_macd.bar(sub.index, sub['MACD'], color=macd_colors, width=0.6, alpha=0.75, label='MACD Hist / 红绿柱')
    ax_macd.plot(sub.index, sub['DIF'], color='#FFFFFF', linewidth=1.0, label='DIF (Fast)')
    ax_macd.plot(sub.index, sub['DEA'], color='#FFD700', linewidth=1.0, label='DEA (Slow)')
    ax_macd.axhline(0, color='#8b949e', linewidth=0.6, alpha=0.5)
    ax_macd.set_ylabel("MACD (动能)", color='#8b949e', fontsize=9)
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


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "NVDA"
    print("=" * 76)
    print(f"  GoldenSpiral (黄金螺旋) Public Demo — {symbol.upper()} Daily K-Line Analysis")
    print("=" * 76)

    df = load_stock_data(symbol=symbol, bars=800)
    df = compute_all_indicators(df)
    deductions = deduce_lookahead(df)

    latest = df.iloc[-1]
    print(f"\n[+] Latest Bar / 最新行情 ({latest['date']}):")
    print(f"    Close / 收盘: ${latest['close']:.2f} | MA21: ${latest['MA21']:.2f} | MA34: ${latest['MA34']:.2f}")
    print(f"    BOLL Lower / 布林下轨: ${latest['BOLL_LOW']:.2f} | KDJ(J): {latest['J']:.1f} | MACD: {latest['MACD']:.2f}")

    print("\n[+] Lookahead Deduction Table / “向右看”抵扣价差分推演表:")
    print("-" * 76)
    for d in deductions:
        print(f"    MA({d['period']:3d}) | Deduct Date: {d['deduct_date']} | Deduct Price: ${d['deduct_price']:7.2f} | "
              f"Diff: {d['diff']:+7.2f} -> {d['status']}")
    print("-" * 76)

    out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples', 'nvda_demo_chart.png')
    plot_nvda_showcase(df, deductions, out_png, symbol=symbol, view_bars=120)
    print(f"\n[+] Showcase chart saved to / 演示图表已生成: {out_png}")


if __name__ == '__main__':
    main()
