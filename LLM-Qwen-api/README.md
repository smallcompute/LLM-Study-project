# Qwen API 电商售后工单分流（详细教学版）

[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

这是一个聚焦真实业务场景的 LLM 项目：**电商售后工单自动分流**。  
项目目标是把“模型调用”变成“可执行客服动作”，帮助团队实现降本增效。

---

## 1. 项目解决什么问题

客服团队常见痛点：

- 工单量大，人工分流速度慢、标准不一致
- 紧急问题（投诉升级、品牌风险）容易被淹没
- 客服回复质量不稳定，新人上手慢

本项目输出三项核心结果：

1. `ticket_type`：工单类型（退款/物流/质量/使用帮助/其他）
2. `priority`：优先级（P0/P1/P2）
3. `reply`：客服回复草稿（可人工复核后发送）

---

## 2. 为什么这个场景有盈利价值

- **节省人力**：减少人工分单和初稿编写时间
- **提升 SLA**：高优工单优先触达，缩短响应时长
- **降低风险**：P0 问题更快闭环，减少舆情和差评
- **提高一致性**：分类规则和回复风格统一

---

## 3. 当前版本设计原则（已同步代码）

- 保留主干学习路径：`密钥管理 -> API 客户端 -> 业务封装 -> 批处理落地`
- 删除分散主线的复杂功能：缓存、会话、评测、复杂 CLI
- 注释统一为中文，强调“结构 + 作用”

---

## 4. 项目结构（与当前代码一致）

```text
Qwen_Api_MiniLLM/
  .gitignore
  requirements.txt
  LICENSE
  README.md
  api_key.py
  api_key.example.txt
  run_chat_demo.py
  run_classify_demo.py
  run_batch_tickets.py
  data/
    tickets_sample.csv
  qwen/
    __init__.py
    qwen_client.py
    mini_llm.py
```

---

## 5. 核心文件说明（结构 + 作用）

### `api_key.py`

- **结构**：环境变量读取 -> 本地文件兜底 -> 缺失抛错
- **作用**：统一密钥管理入口，避免业务层重复处理密钥

### `qwen/qwen_client.py`

- **结构**：
  - 异常类型定义（鉴权/限流/服务端/响应异常）
  - `LLMClient` 类封装请求与解析
  - `chat_completions` 函数式兼容入口
- **作用**：隔离底层 HTTP 细节，让业务代码专注提示词设计

### `qwen/mini_llm.py`

- **结构**：
  - `_normalize_label`：标签标准化
  - `TicketResult`：输出数据结构
  - `EcommerceSupportAssistant`：业务主类
    - `analyze_ticket`：主流程
    - `_repair_label`：分类纠错
    - `_draft_reply`：回复草稿生成
- **作用**：把通用 LLM 能力转换为售后场景能力

### `run_classify_demo.py`

- **结构**：单条工单输入 -> 调用主类 -> 打印结果
- **作用**：快速验证业务链路是否可用

### `run_batch_tickets.py`

- **结构**：读取 CSV -> 逐条分析 -> 写入增强后的 CSV
- **作用**：最小商用闭环，支持真实团队批量处理流程

---

## 6. 业务流程（文字流程图）

1. 读取用户工单文本  
2. 让模型在候选集合内输出 `ticket_type`  
3. 若输出非法，触发一次纠错重试，失败回退 `Other`  
4. 基于工单内容 + 类型判断 `priority`  
5. 若优先级非法，默认回退 `P2`  
6. 生成简短中文回复草稿  
7. 返回结构化结果用于路由和人工复核

---

## 7. 环境要求

- Python 3.10+
- 能访问 DashScope API 的网络
- 有效 `DASHSCOPE_API_KEY`

安装依赖：

```bash
pip install -r requirements.txt
```

---

## 8. API Key 配置

### 方式 A（推荐）：环境变量

PowerShell：

```powershell
$env:DASHSCOPE_API_KEY="你的真实Key"
```

### 方式 B：本地文件兜底（仅开发）

在项目根目录创建 `api_key.txt`：

```text
your_real_key
```

---

## 9. 运行方式

### 9.1 最小聊天调用（验证底层客户端）

```bash
python run_chat_demo.py
```

### 9.2 单条工单分析（验证业务流程）

```bash
python run_classify_demo.py
```

示例输出字段：

- `Ticket Type`
- `Priority`
- `Reply Draft`

### 9.3 批量工单处理（最小商用闭环）

```bash
python run_batch_tickets.py --input data/tickets_sample.csv --output output/routed_tickets.csv
```

---

## 10. 批处理 CSV 格式

### 输入 CSV（至少包含）

- `ticket_text`：工单文本

可额外包含业务字段（如 `ticket_id`、`created_at`），脚本会原样保留。

### 输出 CSV（新增列）

- `ticket_type`
- `priority`
- `reply_draft`

异常场景下会自动回退到安全值，保证批处理不中断。

---

## 11. 异常与回退策略

- 文本为空：直接输出 `Other + P2 + 默认回复`
- 模型类型非法：重试纠错，仍失败回退 `Other`
- 模型优先级非法：回退 `P2`
- 单条请求报错：写入“需人工介入”提示，不影响后续行

---

## 12. 学习路线建议

1. 先读 `qwen/qwen_client.py`，理解调用链和异常分层  
2. 再读 `qwen/mini_llm.py`，理解业务提示词与回退策略  
3. 跑 `run_classify_demo.py`，观察单条工单结构化输出  
4. 跑 `run_batch_tickets.py`，感受批量流程与容错策略  
5. 用你自己的工单数据替换 `data/tickets_sample.csv`

---

## 13. 上传 GitHub 前检查清单

- [ ] 没有提交真实密钥（`api_key.txt`、`.env`）
- [ ] 没有提交业务敏感数据（如客户隐私 CSV）
- [ ] 运行脚本可复现（`run_chat_demo.py`、`run_classify_demo.py`、`run_batch_tickets.py`）
- [ ] README 与代码结构一致

---

## 14. License

MIT License. See [LICENSE](LICENSE).