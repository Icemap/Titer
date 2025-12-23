# Titer：给 LLM 回答做滴定的小工具

![titer.png 85%](https://lab-static.pingcap.com/images/2025/12/23/fa7e6fab2eb2c7b98d1b18fd9d85ef5910a06591.png)

Titer 是一个命令行工具，用来**批量测试 LLM 的回答**，并统计：

- 某些关键词在回答中出现的频率
- 引用或检索来源中，指定域名（支持通配符）出现的频率

它的目标不是给出"对错"，而是提供一个**可量化的观测指标**，帮助你在不同模型、不同提示词、不同运行次数之间做横向比较。

> 名称来源：化学中的滴定（titration）用来测量浓度，Titer 也在重复测量 LLM 输出中的浓度。

## 适合什么场景

- **对比模型**：比较多个模型在同一提示下，是否倾向引用某些域名或反复提到某些关键词。
- **稳定性观察**：在同一模型上多次运行，统计关键词和引用域名的平均值。
- **基准观察**：为内部评估或自动化报告提供统一的、可批处理的统计指标。

它不是"评测模型好坏"的一站式方案，更像一个**轻量、可复用的观测工具**。

## 它是怎么工作的

Titer 的核心逻辑非常简单，目的是让"测量"可重复、可扩展：

1. **读取任务**：通过命令行参数，或从 CSV / Google Sheets 读取批量任务。
2. **调用引擎**：根据 `provider/model` 选择引擎（目前内置 OpenAI 与 Gemini）。
3. **运行多次**：对每个 prompt 重复运行 N 次，以降低随机性。
4. **抽取结果**：
   - 从回答文本中统计关键词出现次数（大小写不敏感）
   - 从响应的引用/检索信息中提取 URL，再匹配域名通配符
5. **输出统计**：输出 JSON，并可追加写入 CSV / Google Sheets

## 主要模块

- `titer/engines/`：引擎层，统一封装不同 LLM 的调用逻辑
- `titer/evaluator.py`：执行评估与统计关键词/域名
- `titer/cli.py`：命令行入口
- `titer/task_runner.py`：批量任务（CSV/Sheets）读取与写入

### 引擎层

目前内置两类引擎：

- OpenAI（Responses API + `web_search` 工具）
- Gemini（Google Search 工具）

两者都被统一抽象为 `Engine`：输入是 prompt，输出是一个标准化结构：

- `content`：模型文本回复
- `cites`：从响应里提取的 URL 列表
- `raw`：原始响应数据

这样做的好处是：**分析逻辑与模型调用解耦**，以后可以继续加更多引擎。

## 核心统计逻辑

### 关键词计数

Titer 会对每个关键词做大小写不敏感的匹配，并统计出现次数。然后对多次运行做平均。

### 域名匹配

Titer 会从响应中提取 URL，解析域名后再用通配符匹配，比如：

- `*.wikipedia.org`
- `*.postgresql.org`

匹配后统计出现次数，同样会做平均。

## 运行方式

### 单次评估（CLI）

```bash
titer run \
  --prompt "What database should I use for AI apps?" \
  --engine "openai/gpt-4o" \
  --engine "gemini/gemini-2.0-flash" \
  --keyword "Postgres" --keyword "vector" \
  --domain "*.postgresql.org" --domain "*.wikipedia.org" \
  --runs 3 \
  --output-csv outputs/single-run.csv
```

输出会包含：

- `keyword_counts`：每个关键词的平均出现次数
- `domain_counts`：每个域名通配符的平均出现次数
- `raw_responses`：原始响应数据（便于调试）

### 批量任务（CSV 或 Google Sheets）

你可以把任务参数放在 CSV 或 Sheet，Titer 会逐行执行并输出汇总结果。适合定期、自动化的"测量"。


## 输出结果长什么样

每次任务输出包括：

- 时间戳
- prompts / engines / keywords / domain_wildcards
- runs（重复次数）
- keyword_counts（平均值）
- domain_counts（平均值）
- raw_responses（完整响应）

你可以将 CSV 结果接入 BI 工具、或用脚本继续分析。


## 限制与注意事项

- **不保证可重复性**：调用在线模型与搜索，结果会随时间变化。
- **指标很粗**：只是频次统计，不代表"正确性"或"可信度"。
- **需要自行解释**：输出是观测数据，不等同于研究结论。

## 你可能会怎么用它

- 比较不同模型在信息来源上的偏好
- 监控模型"品牌/关键词依赖"倾向
- 观察检索模型在某些领域的引用来源稳定性
- 做团队内部评测报告或周期性运行

## 总结

Titer 是一个轻量、可扩展的 LLM 回答"测量工具"。它不负责解释结果，但能让你更方便地**观察模型行为、量化输出特征**。如果你需要一个可批处理、可自动化的工具来跟踪 LLM 回答中的关键词和引用来源，Titer 会是一个不错的起点。
