# KV Cache Simulator 工作计划

## 目标
- 构建可扩展的 KV cache 仿真框架，覆盖请求生成、输入序列、性能分析、重用分析与缓存算法优化。

## 里程碑
1. 骨架与可跑样例
   - 完成模块拆分（requests/simulator/cache/analysis）。
   - 提供基础 LRU 与基础统计。
2. 工作负载与输入建模
   - 支持 trace/数据集输入与参数化分布（长度、并发、热点）。
   - 引入多类型请求（prefill/decoding）与会话级别模型。
3. 性能模型与指标
   - 记录 TTFT、吞吐、尾延迟分布、带宽占用。
   - 引入带宽/算力约束的时序模型。
4. KV 重用与缓存分析
   - 重用率、reuse distance 分析。
   - 分层缓存（HBM/Host/NVMe）与命中率分解。
5. 缓存策略优化
   - 引入 LFU/ARC/分层/分片策略。
   - 支持策略对比与敏感性分析。
6. 实验与可视化
   - 输出 CSV/JSON 报告与绘图脚本。
   - 提供基准场景与对比表格。

## 本周优先任务
- 增加工作负载输入接口（trace + 参数化生成）。
- 扩展指标统计（TTFT、吞吐、p95/p99）。
- 引入至少两种新策略（LFU、分层 LRU）。
- 后续仿真统一基于 4 条 trace：`FAST25-release/arxiv-trace/mooncake_trace.jsonl` 与 `FAST25-release/traces/{conversation_trace,toolagent_trace,synthetic_trace}.jsonl`，以提升命中率为目标优化 cache 设计。

## 约束与约定
- 核心模块保持纯 Python、可单元测试。
- 指标与策略解耦，便于扩展与对比。
- 统一配置入口（YAML）。
