---
name: ai-procrastination-breaker
description: Use when the user is procrastinating, stuck, or avoiding a task. Diagnoses 7 procrastination types via fuzzy keyword matching + shared signal words. Prescribes contextual micro-actions (≤5min). Features downgrade loop for resistance, streak tracking, victory evidence library, and daily review. v1.3 final.
version: 1.3.0
author: 课程作业
license: MIT
metadata:
  hermes:
    tags: [productivity, psychology, procrastination, student, mental-health]
    related_skills: []
---

# AI拖延症破解器 (AI Procrastination Breaker)

## Overview

拖延的本质不是"忘了做"，而是**心理上卡住了**。这个 Skill 通过追问式对话精准定位拖延根因，给出"小到不可能失败"的微行动（≤5分钟），并随着使用次数的增长，学习用户的拖延模式，建立个人化的反拖延系统。

**为什么没有 AI 就做不到：** 传统 todo 软件只是列清单，无法理解"我为什么不做"，无法在追问中挖出真正的心理卡点，无法跨时间识别用户的拖延模式。

## When to Use

**触发条件（任一）：**
- 用户说"不想做""拖了X天""卡住了""不知道从哪开始"
- 用户描述该做但一直没做的事
- 用户表达焦虑/挫败感（"来不及了""作业好多"）
- 用户发送成功汇报（"做完了""接下来做什么"）

**不触发：**
- 正常时间管理咨询（非拖延情绪）
- 用户已有明确计划只需确认
- 纯闲聊（天气、吃饭等）

## Architecture

### 7 种拖延类型

| 类型 | 识别信号 | 典型微行动 |
|------|---------|-----------|
| **完美主义** | 怕做不好、不敢交、怕被批评 | 写一个"烂版本"——故意写烂 |
| **任务模糊** | 不知道从哪开始、没方向 | 只看材料前N行，列出观察点 |
| **任务过大** | 太多了做不完、好几门课 | 拆出最小一块，只做那块 |
| **缺乏动力** | 没意思、不想动、好烦 | 找到最容易的10%，先做掉 |
| **决策疲劳** | 选哪个、纠结、拿不定主意 | 最小后悔原则选一个 |
| **中断重启** | 之前学过忘了、荒废了 | 读旧文件，写注释回顾 |
| **多任务并发** ⭐ | 全都还没做、好几个ddl | 列任务→标紧迫度→只做最紧迫 |

### 共享信号词层 (v1.2)

独立于类型的通用拖延信号，确保"拖了三天""卡住了"等直白表达不被漏掉：

| 信号类别 | 示例 |
|---------|------|
| 时间信号 | "拖了N天""还没开始""又两天没动" |
| 卡点信号 | "卡住了""做不下去""推不动" |
| 回避信号 | "不想写""不想做""不想面对" |
| 焦虑信号 | "来不及了""ddl""时间不够" |

## Core Workflow

### Phase 1: 接收与共情
先共情再追问。"听起来这件事让你______。卡在哪一步？"

### Phase 2: 追问诊断（≤3轮）
每次追问只问1个问题，每次排除2-3种类型。匹配到历史模式时优先验证。

### Phase 3: 微行动处方
1个 ≤5分钟的具体动作，满足：具体到动作 / 不依赖外部条件 / 完成即成功。

### Phase 4: 反馈与记录
- ✅ 完成 → 记录 victory_log + 更新模式库 + 提议下一步
- ❌ 没用 → 触发 Phase 4b 降级回路

### Phase 4b: 降级回路
共情不责备 → 重新诊断 → 切换类型或微行动减半 → 记录 failure_log

### Phase 5: 模式识别
每次对话开始时检查历史模式库，匹配成功则主动提及历史策略。

### Phase 6: 成功跟进 (v1.2)
用户汇报"做完了"时，庆祝 + 记录战果 + 趁热打铁提议下一步。

## Scripts

| 脚本 | 功能 | 命令示例 |
|------|------|---------|
| `procrastination_breaker.py` | 主入口（交互/单次/仪表盘/连胜/分析/历史） | `python procrastination_breaker.py --dashboard` |
| `pattern_analyzer.py` | 拖延模式分析（趋势/类型/策略有效性） | `python pattern_analyzer.py --recent 7` |
| `victory_dashboard.py` | 战果仪表盘（含连胜） | `python victory_dashboard.py` |

## References

| 文件 | 内容 |
|------|------|
| `references/prompt_templates.md` | 6个阶段的完整 Prompt 模板（含降级回路 + 成功汇报） |
| `references/micro_actions_library.md` | 7种类型 × 6条微行动 + 4条通用模板 |
| `references/config_reference.yaml` | 配置参考（4个场景示例） |

## Data Persistence

```
~/.procrastination_breaker/
├── victory_log.jsonl     # 每次突破成功的记录
├── failure_log.jsonl     # 未成功尝试（降级回路用）
├── pattern_db.json       # 识别的拖延模式
├── daily_state.json      # 每日状态（首次使用检测）
└── config.yaml           # 用户偏好
```

## Common Pitfalls

1. **过早给方案** — 未定位根因就抛微行动。必须追问≥2轮。
2. **微行动太大** — "写第一段"不是微行动，"只写标题"才是。
3. **忘记模式识别** — 每次都像第一次对话。必须检查历史模式。
4. **共情变说教** — "你应该……"→ 用"我注意到……"代替。
5. **忽略否定反馈** — 用户说"没用"时不重复建议，降级处理。
6. **错过成功汇报** — 用户说"做完了"时不冷场，趁热打铁。
7. **一次给多个行动** — 只给1个。决策疲劳本身就是拖延原因。

## Verification Checklist

- [ ] 每次对话至少追问2轮才给微行动
- [ ] 微行动 ≤5分钟、具体到动作、不依赖外部条件
- [ ] 检查了历史模式库并主动提及
- [ ] 完成反馈后记录到 victory_log
- [ ] 否定反馈触发降级回路（不重复建议）
- [ ] 成功汇报触发庆祝 + 跟进提议
- [ ] 共享信号词层覆盖了"拖了N天""卡住了"等直白表达
