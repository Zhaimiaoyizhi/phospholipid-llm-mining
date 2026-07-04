# 基于 LLM 的受磷脂调控蛋白质论文信息挖掘与数据库建立

本项目是一个 Linux / Conda / Snakemake 课程项目 MVP。它从 PubMed PMID 种子列表下载论文题名、摘要和元数据，调用 OpenAI-compatible LLM API 抽取“受磷脂调控的蛋白质”结构化记录，并生成 CSV、SQLite 数据库和统计摘要。

## 项目特点

- 数据来源：PubMed 论文数据库，通过 NCBI E-utilities 下载原始论文元数据和摘要。
- 流程管理：使用 Snakemake 实现一键化、模块化 workflow。
- LLM 抽取：支持真实 OpenAI-compatible API，保留原始模型输出用于审计。
- 数据库建立：输出结构化宽表和 SQLite 数据库。
- 质控意识：默认 `review_status=pending`，要求证据句，缺失证据会标记 `ambiguity_flag`。

## 目录结构

```text
.
├── Snakefile
├── config/config.yaml
├── data/input/pmids.txt
├── environment.yml
├── prompts/extraction_prompt.md
├── schema/database_schema.md
├── docs/flowchart.mmd
├── scripts/
├── tests/
└── README.md
```

运行后生成：

```text
data/intermediate/articles_pubmed.csv
data/intermediate/prepared_articles.jsonl
results/raw_llm_outputs/
results/llm_extracted_raw.jsonl
results/extracted_records.csv
results/failed_records.csv
results/phospholipid_protein.sqlite
results/extraction_summary.json
```

## 环境配置

```bash
conda env create -f environment.yml
conda activate phospholipid-llm-mining
```

如果已经有环境，也可以安装依赖后导出：

```bash
conda env export --from-history > environment.yml
```

## API 配置

复制示例环境文件：

```bash
cp .env.example .env
```

填写：

```env
LLM_API_KEY=your_api_key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

也可以使用 DeepSeek、Kimi、通义千问等兼容 OpenAI Chat Completions 的服务，只需替换 `LLM_BASE_URL` 和 `LLM_MODEL`。

## 一键运行

```bash
snakemake --cores 1
```

Workflow 步骤：

1. `fetch_pubmed`：从 PubMed 下载 PMID 对应的题名、摘要、DOI、期刊、年份。
2. `prepare_inputs`：校验输入并生成 JSONL。
3. `llm_extract`：调用 LLM API，保存原始返回和结构化 JSON。
4. `normalize_records`：字段规范化，生成 CSV 和失败记录。
5. `build_database`：构建 SQLite 数据库。
6. `make_summary`：生成统计摘要。

## 离线烟测模式

真实项目主线使用 API。若临时没有 API key，可将 `config/config.yaml` 中的：

```yaml
llm:
  mode: api
```

临时改成：

```yaml
llm:
  mode: mock
```

然后运行同一条 Snakemake 命令。`examples/mock_llm_outputs/40172963.json` 只用于验证流程能从 LLM 原始输出走到 CSV/SQLite，不代表最终抽取效果。

## 测试

```bash
pytest
snakemake --dry-run --cores 1
```

## MVP 边界

本次课程项目强调完整框架和可复现流程，不追求抽取效果最优化。当前版本不做：

- PDF 全文解析
- 自动 PubMed 检索扩展
- UniProt / LIPID MAPS / PDB 自动映射
- LLM prompt 系统优化
- 大规模人工校验
- Web 数据库界面

这些将作为后续课题扩展方向。
