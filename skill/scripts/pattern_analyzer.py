#!/usr/bin/env python3
"""
AI拖延症破解器 — 模式分析器

功能：
  1. 从 victory_log.jsonl 中提取拖延模式
  2. 识别触发场景的共性特征
  3. 统计各策略的成功率
  4. 生成模式报告

使用方式：
  python pattern_analyzer.py                 # 全量分析
  python pattern_analyzer.py --recent 7      # 最近7天
  python pattern_analyzer.py --type 完美主义  # 按类型筛选
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import Counter, defaultdict

DATA_DIR = Path.home() / ".procrastination_breaker"
VICTORY_LOG = DATA_DIR / "victory_log.jsonl"


def load_all_records() -> list:
    """加载所有记录"""
    if not VICTORY_LOG.exists():
        return []
    records = []
    with open(VICTORY_LOG, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records


def filter_by_days(records: list, days: int) -> list:
    """按天数筛选"""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    return [r for r in records if r.get("timestamp", "") >= cutoff]


def filter_by_type(records: list, ptype: str) -> list:
    """按拖延类型筛选"""
    return [r for r in records if r.get("root_cause") == ptype]


def analyze_patterns(records: list) -> dict:
    """分析拖延模式"""
    if not records:
        return {"summary": "没有数据", "patterns": [], "insights": []}

    # 按类型统计
    type_counter = Counter(r.get("root_cause", "未知") for r in records)
    
    # 按日期统计趋势
    date_counter = Counter(r.get("date", "未知") for r in records)
    dates_sorted = sorted(date_counter.keys())
    
    # 每日频率
    if dates_sorted:
        first_date = datetime.strptime(dates_sorted[0], "%Y-%m-%d")
        last_date = datetime.strptime(dates_sorted[-1], "%Y-%m-%d")
        total_days = max((last_date - first_date).days + 1, 1)
        daily_avg = len(records) / total_days
    else:
        daily_avg = 0

    # 任务相似度分析
    task_words = []
    for r in records:
        task = r.get("task", "")
        task_words.extend(task)
    task_char_counter = Counter(task_words)
    
    # 高峰时段分析
    hour_counter = Counter()
    for r in records:
        ts = r.get("timestamp", "")
        if ts:
            try:
                hour = datetime.fromisoformat(ts).hour
                hour_counter[hour] += 1
            except ValueError:
                pass

    # 策略有效性：按类型统计常用策略
    strategy_by_type = defaultdict(Counter)
    for r in records:
        strategy_by_type[r.get("root_cause", "未知")][r.get("micro_action", "")] += 1

    # 洞察
    insights = []
    
    # 最常见拖延类型
    if type_counter:
        top_type, top_count = type_counter.most_common(1)[0]
        pct = top_count / len(records) * 100
        insights.append(f"最常见的拖延类型是「{top_type}」，占 {pct:.0f}%（{top_count}/{len(records)}次）")
    
    # 趋势
    if len(dates_sorted) >= 3:
        recent_dates = dates_sorted[-3:]
        recent_count = sum(date_counter[d] for d in recent_dates)
        older_dates = dates_sorted[:-3]
        if older_dates:
            older_count = sum(date_counter[d] for d in older_dates)
            older_days = len(older_dates)
            recent_days = len(recent_dates)
            older_avg = older_count / older_days
            recent_avg = recent_count / recent_days
            if recent_avg < older_avg * 0.7:
                insights.append("📉 近期拖延频率下降，策略可能正在生效！")
            elif recent_avg > older_avg * 1.3:
                insights.append("📈 近期拖延频率上升，可能需要调整策略或检查是否有新压力源")
    
    # 活跃时段
    if hour_counter:
        peak_hour, peak_count = hour_counter.most_common(1)[0]
        time_label = f"{peak_hour}:00-{peak_hour+1}:00"
        insights.append(f"最容易拖延的时段是 {time_label}（出现{peak_count}次），可以在这个时段提前安排微行动")

    return {
        "summary": {
            "total_records": len(records),
            "days_covered": len(date_counter),
            "daily_average": round(daily_avg, 2),
            "unique_types": len(type_counter),
        },
        "type_distribution": dict(type_counter.most_common()),
        "daily_trend": {d: date_counter[d] for d in dates_sorted[-14:]},
        "hourly_distribution": dict(sorted(hour_counter.items())),
        "top_strategies": {k: dict(v.most_common(3)) for k, v in strategy_by_type.items()},
        "insights": insights
    }


def main():
    records = load_all_records()
    
    # 命令行参数处理
    i = 1
    while i < len(sys.argv):
        if sys.argv[i] == "--recent" and i + 1 < len(sys.argv):
            records = filter_by_days(records, int(sys.argv[i+1]))
            i += 2
        elif sys.argv[i] == "--type" and i + 1 < len(sys.argv):
            records = filter_by_type(records, sys.argv[i+1])
            i += 2
        else:
            i += 1
    
    result = analyze_patterns(records)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
