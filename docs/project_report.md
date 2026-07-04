# 基于 LLM 的受磷脂调控蛋白质论文信息挖掘与数据库建立

作者：翟淼

GitHub 仓库链接：待推送至 GitHub 后填写

## 中文摘要

受磷脂调控的蛋白质广泛参与膜定位、离子通道门控、信号转导、膜修复和细胞器功能维持等过程。传统人工整理该类文献信息时，需要从论文题名、摘要、结果描述和实验方法中识别蛋白质、磷脂种类、调控关系、实验体系和证据等级，工作量大且字段一致性难以保证。本项目围绕“基于 LLM 的受磷脂调控蛋白质论文信息挖掘与数据库建立”这一目标，构建了一个可复现的最小可行流程。流程以 PMID 列表作为输入，通过 PubMed/NCBI E-utilities 下载论文元数据和摘要，使用 Snakemake 管理数据获取、输入准备、LLM 结构化抽取、字段规范化、SQLite 数据库构建和统计摘要生成等步骤。抽取字段参考前期项目形成的“受磷脂调控蛋白质数据库字段设计清单”，并通过 prompt 约束要求模型忠于原文、不编造 UniProt ID、PDB ID 或脂质数据库 ID，所有记录默认标记为 pending 以便后续人工复核。实际运行中，本项目处理 10 篇 PubMed 文献，生成 16 条结构化记录，失败记录为 0。结果表明，该框架能够稳定完成从论文数据库原始记录到结构化数据库的自动化转换，为后续扩大文献规模、接入全文解析和进行人工校验奠定了工程基础。

关键词：磷脂调控蛋白；大语言模型；文献信息抽取；PubMed；Snakemake；SQLite

## Abstract

Phospholipid-regulated proteins are involved in membrane localization, ion channel gating, signaling, membrane repair, and organelle homeostasis. Manual curation of this literature requires extracting proteins, lipid species, regulatory relationships, experimental systems, and evidence levels from biomedical articles, which is labor-intensive and difficult to standardize. This project builds a reproducible minimum viable workflow for LLM-assisted literature mining and database construction of phospholipid-regulated proteins. The workflow starts from a PMID seed list, downloads article metadata and abstracts from PubMed through NCBI E-utilities, and uses Snakemake to orchestrate data acquisition, input preparation, LLM-based extraction, record normalization, SQLite database construction, and summary generation. The extraction schema is based on a previously designed field table for a phospholipid-regulated protein database. The prompt instructs the model to remain faithful to the title and abstract, avoid inventing external identifiers, and provide evidence sentences. All extracted records are marked as pending for later manual review. In the current run, 10 PubMed articles were processed, producing 16 structured records with 0 failed records. The result demonstrates that the framework can convert raw literature records into an auditable structured database and provides a foundation for future full-text mining, identifier normalization, and manual curation.

Keywords: phospholipid-regulated protein; large language model; literature mining; PubMed; Snakemake; SQLite

## 前言 Introduction

细胞膜并不是被动的结构边界，而是蛋白质功能调控的重要环境。磷脂，尤其是磷脂酰肌醇磷酸类、磷脂酰丝氨酸和其他带电膜脂，能够通过直接结合、膜招募、构象调节、通道门控、复合体稳定或改变膜微区分布等方式影响蛋白质功能。许多膜相关蛋白的功能并不能仅从氨基酸序列或静态结构解释，还需要结合脂质环境和实验体系进行理解。因此，建立一个面向“受磷脂调控蛋白质”的结构化数据库具有实际研究价值。

本项目的前期基础是已经完成的字段设计与检索策略整理，包括蛋白主体字段、磷脂字段、调控事件字段、实验方法字段、结合位点字段、膜定位字段、疾病字段和证据质控字段。已有成果说明数据库建设并不是简单收集论文标题，而是需要围绕“蛋白质-磷脂-调控关系-证据”构建可追溯的数据结构。本课程项目的重点不是在本次作业中完成大规模高精度文献整理，而是搭建一个完整、可运行、可复现的工程框架，使后续课题能够在此基础上继续扩展。

本项目提出的科学与工程问题是：能否使用公开论文数据库和大语言模型，自动从论文摘要中识别受磷脂调控的蛋白质信息，并输出可审计的结构化数据库？围绕该问题，本项目采用 PubMed 作为原始数据来源，以 PMID 列表作为输入，使用 Snakemake 构建模块化 workflow，并用 SQLite 保存数据库结果。项目特别强调 LLM 幻觉风险控制：模型只能依据题名和摘要输出，不允许补造外部数据库编号，必须给出 evidence sentence，且所有结果均标记为待人工复核。

## 数据集与方法 Methods

### 数据来源

本项目使用 PubMed 论文数据库作为原始数据来源。输入数据为 `data/input/pmids.txt` 中的一组 PMID，每行一个编号，支持以 `#` 开头的注释行。workflow 的第一步通过 NCBI E-utilities 的 PubMed efetch 接口下载题名、摘要、DOI、期刊、年份和来源数据库等元数据，并保存为 `data/intermediate/articles_pubmed.csv`。当前演示数据集中包含 10 篇与 PIP2、磷脂酰丝氨酸、磷脂酰肌醇结合结构域或膜招募相关的 PubMed 文章。

实际运行结果显示，当前版本成功处理 `article_count=10` 篇文献，并将下载结果转化为 JSONL 形式供 LLM 抽取。数据获取过程不依赖人工复制摘要，因此符合“从论文数据库下载原始数据”的项目要求。

### 计算环境与工具版本

项目使用 Conda 管理计算环境，环境文件为 `environment.yml`。当前环境名称为 `phospholipid-llm-mining`，主要依赖包括 Python 3.11、Snakemake、requests、python-dotenv、pandas、PyYAML 和 pytest。Snakemake 用于 workflow 管理，requests 用于 PubMed 和 LLM API 请求，python-dotenv 用于读取本地 `.env` 中的 LLM API 配置，SQLite 用于保存结构化数据库。

项目已经在 Windows 本地环境中完成验证。当前 Snakemake 版本为 9.23.1，Python 版本为 3.11.15。测试命令 `pytest -q` 通过 3 个单元测试，`snakemake --dry-run --cores 1` 能正常构建 DAG。

### 流程设计

本项目的核心 workflow 由 `Snakefile` 管理，包含以下步骤：

1. `fetch_pubmed`：读取 PMID 列表，通过 PubMed E-utilities 下载论文元数据和摘要。
2. `prepare_inputs`：检查输入表字段，去重 PMID，输出标准 JSONL。
3. `llm_extract`：调用 OpenAI-compatible LLM API，按固定 prompt 抽取结构化 JSON，并保存原始模型响应。
4. `normalize_records`：解析 LLM 输出，统一字段名和控制词，生成主结果 CSV 和失败记录表。
5. `build_database`：将文章信息、运行信息、结构化记录和 raw output 索引写入 SQLite 数据库。
6. `make_summary`：统计文章数、记录数、失败数、蛋白数、脂质数、证据等级分布和调控关系分布。

流程图文件位于 `docs/flowchart.mmd`，核心数据流为：

```text
PMID 列表
  -> PubMed 元数据和摘要下载
  -> JSONL 输入准备
  -> LLM 结构化抽取
  -> 字段规范化
  -> CSV / SQLite 数据库
  -> summary JSON
```

### 字段设计与数据库结构

字段设计参考前期 Excel 字段表，MVP 版本采用“宽表主记录 + 元数据表”的结构。SQLite 数据库文件为 `results/phospholipid_protein.sqlite`，包含四张表：

- `articles`：保存 PMID、题名、摘要、DOI、期刊、年份和来源数据库。
- `extraction_runs`：保存本次运行的 run_id、模型、prompt 版本、温度参数和运行模式。
- `phospholipid_protein_records`：保存核心结构化抽取记录。
- `llm_raw_outputs`：保存 PMID 到 raw LLM 输出文件的索引和解析状态。

核心抽取字段包括 `protein_name_reported`、`gene_symbol`、`organism`、`lipid_name_reported`、`regulation_relationship`、`effect_direction`、`functional_effect`、`mechanism_summary`、`original_evidence_sentence`、`experimental_method`、`evidence_level` 和 `review_status` 等。数据库检索类字段如 `uniprot_id`、标准蛋白名和标准脂质 ID 在本次 MVP 中允许为空，避免模型凭空补造。

### LLM 抽取约束

LLM prompt 位于 `prompts/extraction_prompt.md`。核心约束包括：

- 只能依据 title 和 abstract 抽取。
- 不允许使用外部知识。
- 不确定字段填 `null`。
- 不允许编造 UniProt、PDB、LIPID MAPS、ChEBI 等数据库编号。
- 顶层输出必须为 JSON array。
- 没有明确磷脂调控蛋白证据时返回空数组。
- 每条记录必须尽量提供 `original_evidence_sentence`。
- `review_status` 默认为 `pending`。

这些约束的目的是降低 LLM 幻觉风险，并使输出适合人工复核。

## 结果 Results

### 数据获取结果

当前运行从 PubMed 成功获取 10 篇论文的题名、摘要和元数据。下载后的原始元数据保存为 `data/intermediate/articles_pubmed.csv`，供后续 JSONL 转换和 LLM 抽取使用。

### LLM 抽取与数据库构建结果

真实 API 运行结果保存于 `results/extraction_summary.json`。统计结果如下：

```json
{
  "article_count": 10,
  "record_count": 16,
  "failed_count": 0,
  "unique_pmids_with_records": 10,
  "unique_reported_proteins": 15,
  "unique_reported_lipids": 9
}
```

这说明当前 10 篇输入文献均产生了至少一条结构化记录，共生成 16 条蛋白质-磷脂调控证据记录，失败记录为 0。SQLite 数据库中 `articles` 表有 10 行，`llm_raw_outputs` 表有 10 行，`phospholipid_protein_records` 表有 16 行。抽取样例包括 KCNQ5 与 PIP2 的 activation 关系、TMEM16A/ANO1 与 PI(4,5)P2 的 gating 关系、TASK-2 与 PI(4,5)P2 的 direct_binding 关系，以及 PDK1 与 phosphatidylserine 的 membrane_recruitment 关系。

### 证据等级与调控关系分布

当前抽取结果中，证据等级分布为 A 类 4 条、B 类 1 条、C 类 6 条、E 类 5 条。调控关系包括 activation、gating、direct_binding、membrane_recruitment 和 inhibition。其中 membrane_recruitment 数量最多，说明当前 PMID 种子集中包含较多与膜招募和磷脂结合结构域相关的论文。

需要强调的是，证据等级由 LLM 根据摘要信息进行初步判断，尚未经过人工复核，因此不能直接作为正式数据库中的最终证据评级。项目将所有记录标记为 `review_status=pending`，以体现自动抽取结果必须经过人工校验。

### 一键化运行结果

为降低验收和复现实操门槛，项目提供了 `run_project.bat` 和 `run_project.ps1`。Windows 用户可以双击 `run_project.bat`，按照提示输入 PMID 列表路径、输出目录和运行模式。第一次运行时，脚本会检查 Conda、项目环境和 LLM 配置；缺失时会引导用户下载 Miniforge、创建 Conda 环境并填写 API 信息。命令行用户也可以运行：

```powershell
.\run_project.ps1 -PmidsFile "D:\path\pmids.txt" -OutDir "D:\path\output" -Mode append
```

输出目录包含 `input/`、`cache/`、`results/` 和 `logs/`。其中 `results/extracted_records.csv` 是主结果表，`results/phospholipid_protein.sqlite` 是数据库，`results/extraction_summary.json` 是统计摘要。

## 讨论 Discussion

本项目的主要价值在于把“文献阅读与字段整理”转化为一个可复现的自动化流程。与单纯手动整理相比，Snakemake workflow 能明确记录每一步输入和输出，使数据获取、LLM 抽取、字段规范化和数据库构建之间的关系更清楚。与直接让 LLM 自由回答相比，本项目通过固定 schema、控制词表、证据句要求和 raw output 留痕提高了结果的可审计性。

从生物学意义上看，当前抽取结果集中出现的 KCNQ、TMEM16A、TASK-2、PDK1 等蛋白均与膜脂调控、离子通道活动或膜定位有关，说明所选 PMID 种子与“受磷脂调控蛋白质”主题吻合。PIP2 在多种离子通道门控中发挥关键调节作用，磷脂酰丝氨酸则常与蛋白膜招募和信号转导相关。这些结果展示了数据库未来可以支持的查询方向，例如按磷脂种类检索蛋白、按调控关系筛选 evidence、或按实验方法比较证据强度。

项目的局限性也很明显。第一，本次 MVP 主要使用题名和摘要，没有解析全文和图表，因此很多结合位点、突变实验、定量参数和图表编号无法完整提取。第二，LLM 对证据等级和机制总结的判断仍可能受到摘要表达方式影响，存在过度概括或遗漏细节的风险。第三，标准化数据库检索尚未接入 UniProt、LIPID MAPS、ChEBI、PDB 等外部资源，因此 `uniprot_id` 和脂质标准 ID 等字段在当前版本中主要留空。第四，当前数据集只有 10 篇文献，适合作为课程项目演示和工程框架验证，但不足以代表完整研究领域。

后续改进方向包括：接入 PubMed 自动检索式扩展 PMID；增加 PDF 或开放全文解析模块；使用 UniProt REST API、LIPID MAPS、ChEBI 和 RCSB PDB 进行标准化映射；设计人工复核界面；建立抽取准确率评估集；将 evidence_level 从 LLM 判断改为规则加人工校验的混合机制。

## AI 协同反思

本项目使用大语言模型辅助实现两个层面的工作：一是作为被研究流程中的信息抽取工具，二是辅助编写脚本、调试 workflow 和组织项目结构。AI 辅助编程提高了开发效率，尤其是在拆分 Snakemake 规则、设计 SQLite 表结构、编写 prompt 和处理 Windows PowerShell 兼容性问题时，能够快速生成可运行的初始版本。然而，AI 也可能带来幻觉风险。例如模型可能根据常识补全数据库编号，或把摘要中较弱的相关性表述成强因果机制。为控制这种风险，本项目在 prompt 中明确要求“忠于原文”和“不编造外部 ID”，并保存 raw LLM 输出供人工审计。所有结构化记录默认设置为 `pending`，这提醒使用者：LLM 抽取结果是候选记录，而不是最终数据库事实。

从学习角度看，AI 协作促进了对“流程边界”的思考。项目没有把抽取效果优化作为唯一目标，而是优先搭建环境、数据来源、workflow、缓存、数据库和文档。这种工程化拆分使复杂课题可以被分解为可验证模块，也更符合可复现生物信息项目的基本要求。

## 结论

本项目完成了一个基于 PubMed 与 LLM 的受磷脂调控蛋白质文献信息挖掘 MVP。它能够从 PMID 列表自动下载论文元数据和摘要，调用 LLM 按固定 schema 抽取结构化记录，规范化输出 CSV，构建 SQLite 数据库，并生成统计摘要。项目使用 Conda 管理环境，使用 Snakemake 管理 workflow，并提供双击式一键运行脚本，满足课程对计算环境、数据获取、流程管理、结果发布和文档说明的主要要求。当前版本已经适合用于课程作业展示，后续可在全文解析、外部数据库标准化、人工复核和大规模数据集方面继续扩展。

## 参考文献 References

Köster, J., & Rahmann, S. (2012). Snakemake: A scalable bioinformatics workflow engine. *Bioinformatics, 28*(19), 2520-2522.

National Center for Biotechnology Information. (n.d.). *Entrez Programming Utilities Help*. https://www.ncbi.nlm.nih.gov/books/NBK25499/

SQLite Consortium. (n.d.). *SQLite Documentation*. https://www.sqlite.org/docs.html

UniProt Consortium. (2023). UniProt: The Universal Protein Knowledgebase in 2023. *Nucleic Acids Research, 51*(D1), D523-D531.

Fahy, E., Subramaniam, S., Murphy, R. C., Nishijima, M., Raetz, C. R. H., Shimizu, T., Spener, F., van Meer, G., Wakelam, M. J. O., & Dennis, E. A. (2009). Update of the LIPID MAPS comprehensive classification system for lipids. *Journal of Lipid Research, 50*, S9-S14.

## 附录 Appendix

### environment.yml

```yaml
name: phospholipid-llm-mining
channels:
  - defaults
  - conda-forge
dependencies:
  - python=3.11
  - pyyaml[version='>=6.0']
  - pip
  - requests[version='>=2.31']
  - pandas[version='>=2.2']
  - python-dotenv[version='>=1.0']
  - snakemake-minimal[version='>=8']
  - pytest[version='>=8']
```

### 核心运行命令

```powershell
.\run_project.ps1 -PmidsFile "D:\path\pmids.txt" -OutDir "D:\path\output" -Mode append
```

或直接运行 Snakemake：

```powershell
C:\Users\xyc\miniforge3\Scripts\conda.exe run -n phospholipid-llm-mining snakemake --cores 1
```

### 关键输出文件

```text
results/extracted_records.csv
results/failed_records.csv
results/phospholipid_protein.sqlite
results/extraction_summary.json
results/raw_llm_outputs/
```

