#!/usr/bin/env python3
"""
GoldenSpiral (黄金螺旋) 公开演示脚本 (Public Demo)
展示：
1. 斐波那契 8 均线系统 (5, 13, 21, 34, 55, 144, 233, 623)
2. “向右看”间隔线（抵扣价）数学差分推演
3. 极值截断 KDJ (0~100) 与暗色风格可视化图表输出
"""

import os
import re
import sys
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# 设置中文字体兼容
plt.rcParams['font.sans-serif'] = ['PingFang SC', 'Heiti TC', 'Arial Unicode MS', 'SimHei', 'sans-serif']
plt.rcParams['axes.unicode_minus'] = False

MA_PERIODS = [5, 13, 21, 34, 55, 144, 233, 623]
MA_COLORS = {
    5: '#FFFFFF',    # 白：超短攻击线
    13: '#FFFF00',   # 黄：短线主力线
    21: '#FF00FF',   # 紫：波段辅助线
    34: '#00FF00',   # 绿（加粗）：中线生命线
    55: '#00FFFF',   # 青：中期趋势线
    144: '#FF6600',  # 橙（加粗）：长线牛熊分水岭
    233: '#FF0000',  # 红（加粗）：大周期牛熊线
    623: '#8888FF',  # 蓝紫：超长周期大底线
}


def load_demo_data(symbol=None, bars=750):
    """加载演示数据：支持默认生成模拟斐波那契波浪数据，或可选通过 AKShare 获取公开日线"""
    if symbol and re.match(r'^(sh|sz|bj)?\d{6}$', symbol.strip().lower()):
        try:
            import akshare as ak
            code = symbol.strip().lower()
            if not code.startswith(('sh', 'sz', 'bj')):
                code = f"sh{code}" if code.startswith('6') else f"sz{code}"
            start_year = datetime.now().year - 4
            print(f"[*] 正在通过 AKShare 拉取 [{code}] 公开前复权日线...")
            df = ak.stock_zh_a_hist_tx(symbol=code, start_date=f"{start_year}0101", adjust="qfq")
            df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
            return df.sort_values('date').reset_index(drop=True)
        except Exception as e:
            print(f"[!] 在线拉取失败 ({e})，回退至内置模拟数据...")

    print("[*] 生成 750 根斐波那契波浪模拟日线数据...")
    np.random.seed(42)
    end_date = datetime.now()
    dates = [end_date - timedelta(days=int(i * 1.45)) for i in range(bars)]
    dates.reverse()

    returns = np.random.normal(0.0006, 0.018, bars)
    trend = np.sin(np.linspace(0, 15, bars)) * 0.15 + np.linspace(0, 0.4, bars)
    price_base = 20.0 * np.exp(np.cumsum(returns) + trend)

    opens = price_base * (1 + np.random.uniform(-0.008, 0.008, bars))
    highs = np.maximum(price_base, opens) * (1 + np.abs(np.random.normal(0, 0.012, bars)))
    lows = np.minimum(price_base, opens) * (1 - np.abs(np.random.normal(0, 0.012, bars)))
    closes = price_base
    volumes = np.random.uniform(50000, 300000, bars) * (1 + np.abs(returns) * 20)

    return pd.DataFrame({
        'date': [d.strftime('%Y-%m-%d') for d in dates],
        'open': np.round(opens, 2),
        'high': np.round(highs, 2),
        'low': np.round(lows, 2),
        'close': np.round(closes, 2),
        'volume': np.round(volumes, 0)
    })


def compute_indicators(df):
    """计算斐波那契均线簇、均量线与钝化截断 KDJ"""
    df = df.copy()
    for p in MA_PERIODS:
        df[f'MA{p}'] = df['close'].rolling(window=p, min_periods=1).mean()

    df['VOL_MA5'] = df['volume'].rolling(window=5, min_periods=1).mean()
    df['VOL_MA40'] = df['volume'].rolling(window=40, min_periods=1).mean()

    # KDJ(14, 3, 3) 极值截断于 [0, 100]
    low_n = df['low'].rolling(window=14, min_periods=1).min()
    high_n = df['high'].rolling(window=14, min_periods=1).max()
    denom = (high_n - low_n).replace(0, np.nan)
    rsv = ((df['close'] - low_n) / denom * 100).fillna(50.0).clip(0, 100)

    k_list, d_list, j_list = [], [], []
    k_val, d_val = 50.0, 50.0
    for r in rsv:
        k_val = np.clip((2 / 3) * k_val + (1 / 3) * r, 0, 100)
        d_val = np.clip((2 / 3) * d_val + (1 / 3) * k_val, 0, 100)
        j_val = np.clip(3 * k_val - 2 * d_val, 0, 100)
        k_list.append(k_val)
        d_list.append(d_val)
        j_list.append(j_val)

    df['K'], df['D'], df['J'] = k_list, d_list, j_list
    return df


def deduce_lookahead(df):
    """计算各周期均线的抵扣价（间隔线）并推演斜率方向"""
    latest_close = df['close'].iloc[-1]
    n_bars = len(df)
    results = []
    for p in MA_PERIODS:
        idx = max(0, n_bars - p)
        deduct_price = df['close'].iloc[idx]
        deduct_date = df['date'].iloc[idx]
        diff = latest_close - deduct_price
        direction = "向上助涨 (现价 > 抵扣价)" if diff >= 0 else "向下压制 (现价 < 抵扣价)"
        results.append({
            'period': p,
            'idx': idx,
            'deduct_date': deduct_date,
            'deduct_price': deduct_price,
            'diff': diff,
            'direction': direction
        })
    return results


def plot_demo_chart(df, deductions, out_path, view_bars=120):
    """生成暗黑风格斐波那契均线与抵扣价演示图"""
    sub = df.iloc[-view_bars:].reset_index(drop=True)
    offset = len(df) - len(sub)

    fig = plt.figure(figsize=(16, 10), facecolor='#0d1117')
    gs = fig.add_gridspec(3, 1, height_ratios=[3.2, 1, 1], hspace=0.08)

    ax_main = fig.add_subplot(gs[0], facecolor='#0d1117')
    ax_vol = fig.add_subplot(gs[1], facecolor='#0d1117', sharex=ax_main)
    ax_kdj = fig.add_subplot(gs[2], facecolor='#0d1117', sharex=ax_main)

    # 1. 绘制 K 线
    for i, row in sub.iterrows():
        is_up = row['close'] >= row['open']
        color = '#ff3b30' if is_up else '#00e676'
        ax_main.plot([i, i], [row['low'], row['high']], color=color, linewidth=0.9)
        body_low = min(row['open'], row['close'])
        body_h = max(abs(row['close'] - row['open']), 0.02)
        ax_main.add_patch(Rectangle((i - 0.32, body_low), 0.64, body_h,
                                    facecolor=color if is_up else '#0d1117',
                                    edgecolor=color, linewidth=0.9))

    # 2. 绘制斐波那契 8 均线与窗口内抵扣价标记
    for p in MA_PERIODS:
        lw = 2.2 if p in (34, 144, 233) else 1.0
        label = f"MA{p} (生命线)" if p == 34 else (f"MA{p} (牛熊线)" if p in (144, 233) else f"MA{p}")
        ax_main.plot(sub.index, sub[f'MA{p}'], color=MA_COLORS[p], linewidth=lw, label=label, alpha=0.9)

    for item in deductions:
        rel_idx = item['idx'] - offset
        if 0 <= rel_idx < len(sub):
            p = item['period']
            ax_main.axvline(rel_idx, color=MA_COLORS[p], linestyle='--', linewidth=0.7, alpha=0.5)
            ax_main.scatter([rel_idx], [item['deduct_price']], color=MA_COLORS[p], s=45, zorder=6)
            ax_main.text(rel_idx, item['deduct_price'] * 1.01, f"抵{p}", color=MA_COLORS[p], fontsize=8, ha='center')

    ax_main.set_title("GoldenSpiral (黄金螺旋) 斐波那契八均线与抵扣价推演演示 (Public Demo)",
                      color='#e6edf3', fontsize=14, pad=12, fontweight='bold')
    ax_main.legend(loc='upper left', ncol=4, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=9)
    ax_main.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_main.tick_params(colors='#8b949e', labelbottom=False)

    # 3. 成交量与均量线
    colors_vol = ['#ff3b30' if r['close'] >= r['open'] else '#00e676' for _, r in sub.iterrows()]
    ax_vol.bar(sub.index, sub['volume'], color=colors_vol, width=0.6, alpha=0.75)
    ax_vol.plot(sub.index, sub['VOL_MA5'], color='#FFFFFF', linewidth=1.0, label='VOL_MA5')
    ax_vol.plot(sub.index, sub['VOL_MA40'], color='#FFFF00', linewidth=1.2, label='VOL_MA40')
    ax_vol.legend(loc='upper left', facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_vol.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_vol.tick_params(colors='#8b949e', labelbottom=False)

    # 4. KDJ(14, 3, 3) 钝化截断
    ax_kdj.plot(sub.index, sub['K'], color='#FFFFFF', linewidth=1.0, label='K')
    ax_kdj.plot(sub.index, sub['D'], color='#FFFF00', linewidth=1.0, label='D')
    ax_kdj.plot(sub.index, sub['J'], color='#FF00FF', linewidth=1.2, label='J (0~100 截断)')
    ax_kdj.axhline(80, color='#ff3b30', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.axhline(20, color='#00e676', linestyle='--', linewidth=0.6, alpha=0.5)
    ax_kdj.set_ylim(-5, 105)
    ax_kdj.legend(loc='upper left', ncol=3, facecolor='#161b22', edgecolor='#30363d', labelcolor='#e6edf3', fontsize=8)
    ax_kdj.grid(True, color='#21262d', linestyle=':', linewidth=0.6)
    ax_kdj.tick_params(colors='#8b949e')

    tick_step = max(1, len(sub) // 10)
    tick_positions = list(range(0, len(sub), tick_step))
    ax_kdj.set_xticks(tick_positions)
    ax_kdj.set_xticklabels([sub['date'].iloc[i] for i in tick_positions], rotation=20, fontsize=8, color='#8b949e')

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.savefig(out_path, dpi=160, bbox_inches='tight', facecolor='#0d1117')
    plt.close(fig)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else None
    print("=" * 68)
    print("  GoldenSpiral (黄金螺旋) 均线与抵扣价推演系统 - 公开演示版 Demo")
    print("=" * 68)

    df = load_demo_data(symbol=symbol, bars=750)
    df = compute_indicators(df)
    deductions = deduce_lookahead(df)

    print(f"\n[+] 数据准备完成：共 {len(df)} 根 K 线 | 最新日期: {df['date'].iloc[-1]} | 最新收盘价: {df['close'].iloc[-1]:.2f}")
    print("\n[+] “向右看”抵扣价差分推演表 (ΔMA = (现价 - 抵扣价) / N):")
    print("-" * 68)
    for d in deductions:
        print(f"    MA({d['period']:3d}) | 抵扣日: {d['deduct_date']} | 抵扣价: {d['deduct_price']:8.2f} | "
              f"差值: {d['diff']:+8.2f} -> {d['direction']}")
    print("-" * 68)

    out_png = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'samples', 'demo_chart.png')
    plot_demo_chart(df, deductions, out_png)
    print(f"\n[+] 演示图表已输出至: {out_png}")


if __name__ == '__main__':
    main()
