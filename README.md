# DataFlow-Agent

> 生产级多智能体数据自动清洗引擎 | 基于 EleutherAI lm-evaluation-harness 评估规范

---

## 架构概览

```
用户请求
  │
  ▼
validate_input ──► profiler_node ──► engineer_node
                                          │
                         ◄─── retry ──── qa_node
                         │                │
                    human_review_node   finalize_node
```

| 组件 | 职责 |
|------|------|
| **ProfilerAgent** | 采样数据 → 统计列特征 → LLM 语义分析 → 推荐任务 |
| **EngineerAgent** | 读质量报告 → LLM 生成 Python 清洗脚本 |
| **QAAgent** | 语法检查 → 沙盒执行 → 熔断器检查 |
| **CircuitBreaker** | 行数减少 > 阈值 / 待审记录 > 20% → 人工介入 |
| **TaskRegistry** | YAML 任务配置注册中心（对齐 lm-eval harness） |
| **EvaluationRunner** | 批量 Benchmark 评估，输出加权得分报告 |

---

## 快速开始

### 1. 安装依赖

```bash
cd dataflow_agent
pip install -e ".[dev]"
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY 和 LLM_BASE_URL
```

### 3. 运行清洗任务

```bash
# 去重
python scripts/run_job.py \
    --task deduplication \
    --input data/sample_dirty.parquet \
    --output data/sample_clean.parquet \
    --dump-audit

# 实体消歧
python scripts/run_job.py \
    --task entity_resolution \
    --input data/companies_dirty.parquet \
    --output data/companies_clean.parquet
```

### 4. 运行评估

```bash
# 评估所有任务（需要 benchmarks/ 目录下有对应数据集）
python scripts/evaluate.py --tasks all --format table

# 评估指定任务，设置最低分门控
python scripts/evaluate.py \
    --tasks deduplication,entity_resolution \
    --min-score 0.85 \
    --output reports/eval.json
```

### 5. 启动 API 服务

```bash
python -m dataflow.api.main
# 访问 http://localhost:8080/docs
```

---

## API 端点

| Method | Path | 说明 |
|--------|------|------|
| `POST` | `/api/v1/jobs` | 提交清洗任务 |
| `GET`  | `/api/v1/jobs/{job_id}` | 查询任务状态 |
| `GET`  | `/api/v1/jobs/{job_id}/audit-log` | 获取完整审计日志 |
| `POST` | `/api/v1/jobs/{job_id}/approve` | 人工审批（human_review 状态） |
| `POST` | `/api/v1/jobs/{job_id}/abort` | 手动终止 |
| `GET`  | `/api/v1/tasks` | 列出所有已注册任务 |
| `POST` | `/api/v1/evaluate` | 触发 Harness 评估 |
| `GET`  | `/api/v1/evaluate/{eval_id}` | 查询评估报告 |
| `GET`  | `/metrics` | Prometheus 指标 |

---

## Docker 部署

```bash
# 构建沙盒镜像
docker build -f docker/Dockerfile.sandbox -t dataflow-sandbox:latest .

# 启动全栈（API + Worker + Redis + Prometheus + Grafana）
cd docker
docker-compose up -d

# 查看日志
docker-compose logs -f api
```

---

## 运行测试

```bash
# 单元测试（无需 LLM API Key）
pytest tests/unit/ -v

# 集成测试（使用 Mock LLM，无需 API Key）
pytest tests/integration/ -v

# 全量测试 + 覆盖率
pytest --cov=dataflow --cov-report=html
```

---

## 内置任务

| Task | 说明 | 关键指标 |
|------|------|---------|
| `deduplication` | 精确/模糊去重 | uniqueness_rate, row_retention_rate |
| `entity_resolution` | 跨记录实体消歧 | pair_f1, precision, recall |
| `format_standardization` | 日期/电话/邮编格式统一 | format_compliance_rate |
| `missing_value_imputation` | 缺失值统计或语义插补 | completeness_rate |
| `type_coercion` | 字段类型纠正 | type_consistency_rate, coercion_success_rate |

---

## 沙盒安全策略

| 策略 | 本地模式 | Docker 模式 |
|------|---------|------------|
| 内存限制 | 无 | 2 GB (`--memory`) |
| CPU 限制 | 无 | 0.5 核 (`--cpus`) |
| 超时 | 300 s | 300 s |
| 网络 | 继承主机 | 完全禁用 |
| 文件系统 | 主机路径 | 仅 `/data` 可写 |

> **生产环境**：设置 `SANDBOX_MODE=docker` 启用 Docker 沙盒。

---

## 目录结构

```
dataflow_agent/
├── configs/
│   ├── tasks/           # YAML 任务配置（Harness Task Configs）
│   └── profiles/        # 运行时 profile 覆盖（default / production）
├── dataflow/
│   ├── agents/          # ProfilerAgent, EngineerAgent, QAAgent
│   ├── graph/           # LangGraph nodes, edges, builder
│   ├── sandbox/         # LocalSandboxRunner, DockerSandboxRunner
│   ├── schemas/         # Pydantic v2 数据模型
│   ├── tasks/           # TaskRegistry, BaseCleaningTask, loader
│   ├── evaluation/      # Harness EvaluationRunner + MetricRegistry
│   ├── observability/   # structlog JSON 日志 + OpenTelemetry 追踪
│   └── api/             # FastAPI routers (jobs, tasks, evaluation)
├── scripts/
│   ├── run_job.py       # CLI: 运行单个清洗任务
│   └── evaluate.py      # CLI: Harness 评估
├── tests/
│   ├── unit/            # TaskRegistry, CircuitBreaker, Metrics
│   └── integration/     # LangGraph pipeline (Mock LLM + Mock Sandbox)
├── docker/
│   ├── Dockerfile
│   ├── Dockerfile.sandbox
│   ├── docker-compose.yml
│   └── prometheus.yml
└── benchmarks/          # 按 task_name/ 分目录存放 dirty + gold 数据集
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|-------|
| `LLM_API_KEY` | LLM API 密钥 | 必填 |
| `LLM_BASE_URL` | OpenAI 兼容 API 地址 | `https://api.openai.com/v1` |
| `LLM_MODEL` | 默认模型名称 | `gpt-4o` |
| `SANDBOX_MODE` | `local` 或 `docker` | `local` |
| `SANDBOX_IMAGE` | Docker 沙盒镜像名 | `dataflow-sandbox:latest` |
| `BENCHMARK_DIR` | Benchmark 数据根目录 | `./benchmarks` |
| `LOG_FORMAT` | `json` 或 `console` | `json` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
