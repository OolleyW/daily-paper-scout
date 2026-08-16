# Daily Paper Scout（每日论文猎人）

每天自动抓取土木工程**组合结构**方向 Q1 顶刊论文（ScienceDirect），生成**中英双语报告**，并通过 **Claude Code** 摄入到你的 LLM Wiki 知识库（Obsidian + qmd 可检索）。

## 核心流程

```
06:00  Fetch1  启动 Edge（已登录）→ ScienceDirect 检索 → 抓 12 篇摘要+引言
06:30  Fetch2  再抓 12 篇（避开 ScienceDirect 限流）
07:00  Report  8大类分类 + 深度校验 + 优先今年排序 + 去重
                → 中英双语报告(.md) → 存入 output_dir
                → 调用 Claude Code 批量 ingest + lint 健康检查
                → Server酱 微信推送
```

## 目录结构

```
daily_paper_scout/
├── sciencedirect_fetch.py   抓取（Playwright 连 Edge CDP）
├── report_from_sd.py        分类/排序/去重/双语报告/调 Claude Code 摄入
├── common.py                共享工具（配置/通知/启发式兜底）
├── run_fetch.ps1            Edge 启动包装器
├── setup.ps1                一键安装
├── config.example.json      配置模板（复制为 config.json 后填密钥）
└── .gitignore               忽略 config.json / edge_profile / 状态文件
```

## 依赖

- **Python 3.10+**（`requests`、`playwright`）
- **Edge 浏览器**（已登录 ScienceDirect 的机构账号）
- **Claude Code**（`claude` 命令，用于 ingest；需配置为你的 LLM）
- 可选：**Server酱** SendKey（微信通知）、**DeepSeek** API key（报告归纳）

## 前置要求：LLM Wiki 知识库（数据库）

报告生成后的「摄入」步骤依赖一套 **LLM Wiki 知识库**（`CLAUDE.md` + `wiki/` 目录 + Claude Code 命令）。

- **使用前，请先按此文档建立数据库**：https://hcn9zwu8a0fz.feishu.cn/wiki/AM3ewXySViopPdkE8Gic90BDnRb
- 若暂不摄入（只想抓论文 → 双语报告 → 微信提醒），把 `config.json` 的 `ingest.enabled` 设为 `false` 即可跳过。

## 安装

```powershell
.\setup.ps1
```

然后手动两步：

1. 编辑 `config.json`：填入 `llm.api_key`（DeepSeek）、`serverchan.sendkey`、`output_dir`。
2. **首次登录 Edge**：运行一次 `run_fetch.ps1` 会弹出专用 Edge 窗口（独立配置目录 `edge_profile/`），在里面登录一次 ScienceDirect，登录态即持久化。

## 配置说明（config.json）

| 字段 | 说明 |
|---|---|
| `scopus.apikey` | Scopus key（仅用于期刊元数据，可留空，当前抓取用 ScienceDirect） |
| `serverchan.sendkey` | Server酱 SendKey，微信提醒 |
| `llm.api_key` | DeepSeek key，用于分类/归纳/总结 |
| `output_dir` | 报告输出目录（如 `E:\...\raw\reports_literature`） |
| `max_papers` | 每日最多篇数（默认 20） |
| `batch_size` | 每批抓取篇数（默认 12，两批合计 ≈ 20，避开限流） |
| `ingest.enabled` | 是否调用 Claude Code 摄入知识库（false 则跳过，仅出报告） |
| `ingest.cwd` | LLM Wiki 知识库根目录（含 CLAUDE.md，ingest 时作为工作目录） |
| `ingest.source_dir` | 报告源目录（ingest 读取报告的位置） |
| `journals` | Q1 期刊白名单（name / issn / if 影响因子） |

## 手动运行

```powershell
.\run_fetch.ps1          # 抓取一批
python report_from_sd.py # 生成报告 + 摄入 + 通知
```

## 注意事项

- `edge_profile/`、`config.json`、`sciencedirect_results.json`、`sd_state.json` 均为本地运行时文件，已通过 `.gitignore` 排除，**切勿提交**。
- ScienceDirect 有约 13 次翻页/次的限流，故拆成两批、间隔 30 分钟。
- 去重：已推送的论文 DOI 记录在 `sd_state.json`，每日不重复推送。
