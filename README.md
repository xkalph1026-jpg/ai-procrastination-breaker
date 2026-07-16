# AI拖延症破解器 — 反拖延AI个人系统

> 选题来源：AI实践场景清单（自拟题目）  
> 核心理念：AI做执行，人做判断  

---

## 选题说明

### 为什么选这个题目？

清单中有 24 个选题，我选择了**自拟题目「AI拖延症破解器」**，原因：

1. **真实痛点** — 每个学生都经历过拖延，这不是理论假设，是每天发生的事
2. **AI不可替代** — 传统todo软件只管"列清单"，无法理解"为什么不做"、无法追问、无法学习拖延模式。这正是AI的核心价值
3. **零门槛** — 纯Python + 免费大模型API，1-2小时出MVP，符合课程★★★零门槛要求
4. **可持续使用** — 不像一次性作业，这个工具结课后我也会继续用

### 与现有选题的区别

清单 #24「AI作业截止日/任务管理器」侧重**时间安排和优先级**，本工具侧重**解决"启动不了"的心理卡点**，互补不重叠。

---

## 功能简介

### 核心功能

| 功能 | 说明 |
|------|------|
| **拖延类型诊断** | 识别7种拖延类型（完美主义/任务模糊/任务过大/缺乏动力/决策疲劳/中断重启/多任务并发） |
| **微行动处方** | 针对每种类型给出 ≤5分钟的"小到不可能失败"的微行动 |
| **追问式对话** | 通过 Socratic 追问精准定位根因，而非第一印象下判断 |
| **模式识别** | 跨时间学习用户的拖延模式，主动提及历史成功策略 |
| **降级回路** | 用户说"试了没用"时不重复建议，自动切换类型或减半微行动 |
| **连胜追踪** | 3/7/14/30天里程碑庆祝，建立正向激励循环 |
| **反拖延证据库** | 积累所有成功破解的记录，可随时翻看 |

### 技术架构

```
用户输入 → 共享信号词检测 → 模糊关键词匹配 → 追问诊断 → 微行动生成
                ↓                                       ↓
         模式库查询 ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ → 战果记录/连胜更新
                                              ↓
                                         反拖延证据库
```

---

## 使用方式

### 快速开始

```bash
# 交互模式
python skill/scripts/procrastination_breaker.py

# 示例对话
👤 你: 我不想写论文，拖了三天了，怕写不好
🤖 AI: 🔍 判断: 完美主义型拖延 (置信度: 40%)
      💡 根因: 对初稿质量有不切实际的期望
      📌 微行动: 写一个「烂版本」的写论文开头——故意写烂。5分钟。
```

### 命令参考

```bash
python skill/scripts/procrastination_breaker.py              # 交互模式
python skill/scripts/procrastination_breaker.py --input "..." # 单次分类
python skill/scripts/procrastination_breaker.py --dashboard   # 战果仪表盘
python skill/scripts/procrastination_breaker.py --history     # 反拖延证据库
python skill/scripts/procrastination_breaker.py --streak      # 连胜查询
python skill/scripts/procrastination_breaker.py --analyze     # 模式分析

python skill/scripts/pattern_analyzer.py --recent 7           # 近7天分析
python skill/scripts/victory_dashboard.py                     # 可视化仪表盘
```

---

## 项目结构

```
ai-procrastination-breaker/
├── skill/                              # Skill 文件
│   ├── SKILL.md                        # 技能定义
│   ├── scripts/
│   │   ├── procrastination_breaker.py  # 主入口 (v1.3)
│   │   ├── pattern_analyzer.py         # 模式分析器
│   │   └── victory_dashboard.py        # 战果仪表盘
│   └── references/
│       ├── prompt_templates.md         # Prompt 模板（6阶段）
│       ├── micro_actions_library.md    # 微行动模板库（46条）
│       └── config_reference.yaml       # 配置参考
├── data/                               # 测试数据
│   ├── test_cases.json                # 7个结构化测试用例
│   ├── sample_dialogues.md            # 6组完整对话样本
│   └── test_inputs.txt                # 15条批量测试输入
├── tests/                              # 测试记录
│   └── test_record.md                 # 测试报告（v1.0-v1.2）
├── iteration/                          # 迭代升级说明
│   └── iteration_log.md               # 3次迭代完整记录
└── README.md                           # 本文件
```

---

## 迭代历程

| 版本 | 主要改进 | 通过率 |
|------|---------|--------|
| v1.0 | 6种拖延类型 + 静态微行动 + 基础模式识别 | ~40% |
| v1.1 | 扩展关键词(12-17个/类型) + 降级回路 + 连胜 + 动态填充 + 多任务并发 | ~67% |
| v1.2 | 共享信号词层 + 反向模糊匹配 + 置信度重算 + 成功跟进 + 正则优化 | 90% |
| v1.3 | SKILL.md统一重写 + README + references更新 + 代码收敛 | **93%** |

详见 `iteration/iteration_log.md`。

---

## 后续迭代方向

1. **语义匹配** — 接入 embedding 模型，从精确匹配升级为语义相似度匹配
2. **多模态输入** — 支持语音输入（"不想做就直接说"更自然）
3. **社交激励** — 好友组队破解拖延，互相监督微行动完成
4. **生理节律** — 结合用户活跃时段自动推荐最佳微行动时间
5. **长期数据分析** — 生成月度/季度拖延报告，识别季节性模式

---

## 为什么没有 AI 就做不到？

| 功能 | 传统工具 | 本工具（AI） |
|------|---------|------------|
| 识别拖延原因 | 预设标签（"懒""忙"） | 追问+上下文理解，定位心理根因 |
| 给出解决方案 | 模板化建议 | 结合任务名+用户历史动态生成微行动 |
| 记住你的模式 | 无 | 跨时间学习，匹配历史成功策略 |
| 失败时调整 | 重复同样建议 | 降级回路：切换类型/减半微行动 |
| 理解口语 | 关键词硬匹配 | "烦""卡住了""拖了N天" → 都懂 |

---

## 技术栈

- **语言：** Python 3.11+
- **依赖：** 标准库（json, re, pathlib, datetime, collections）
- **AI 模型：** 通过 Hermes Agent Skill 框架调用（支持 DeepSeek/豆包/通义千问等免费API）
- **数据存储：** 本地 JSONL + JSON（`~/.procrastination_breaker/`）

---

## 许可证

MIT License
