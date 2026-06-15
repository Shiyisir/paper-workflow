# 默认值与参数

## 检索默认值

| 参数 | 默认值 | 可选值 |
|------|--------|--------|
| 检索模式 | `standard` | `quick` / `standard` / `systematic` |
| quick 初筛规模 | 15–30 条 | — |
| standard 初筛规模 | 40–100 条 | — |
| quick 深度阅读 | 5–10 篇 | — |
| standard 深度阅读 | 10–30 篇 | — |
| 检索轮次 | 3 轮（核心→补检→定向） | 可加第 4 轮参考文献追溯 |
| PDF 下载时机 | 摘要初筛后 | 不批量下载 |

## 写作默认值

| 参数 | 默认值 |
|------|--------|
| 默认语言 | 英文投稿，中文草稿可接受 |
| 润色标准 | Nature-level academic English |
| 章节结构 | IMRaD（Introduction, Methods, Results, Discussion） |
| 引用格式 | 按目标期刊要求或 GB/T 7714（中文） |
| 图表格式 | SVG 源文件 + PNG/PDF 导出 |

## 学科默认值

| 学科 | 默认引用格式 | 默认写作语言 |
|------|-------------|:---:|
| humanities | Chicago | zh 或 en |
| social_science | APA | zh 或 en |
| economics_management | APA 或 GB/T 7714 | zh 或 en |
| engineering | IEEE 或 GB/T 7714 | zh 或 en |
| medicine | Vancouver 或 APA | en |
| computer_science | IEEE 或 APA | en |
| interdisciplinary | APA | en |

## 渲染默认值

| Profile | 默认 CSL | 公式格式 | SVG 转换 |
|---------|----------|:---:|:---:|
| course-cn | gb-t-7714 | OMML | PNG |
| thesis-cn | gb-t-7714 | OMML | PNG |
| journal-word | apa | OMML | PNG |
| journal-latex | apa | LaTeX | PDF |
| markdown-draft | — | 原样保留 | 不转换 |

## 可配置项（config.yaml）

```yaml
search_mode: standard         # quick | standard | systematic
citation_style: gb-t-7714     # CSL 文件名（不含 .csl）
writing_language: zh          # zh | en | bilingual
word_count_target: null       # 目标字数（null = 按论文类型默认）
auto_skip_stages: true        # 是否根据 paper_type 自动跳过
qa_strict_mode: false         # QA 模式：false = 警告继续，true = 阻塞
```
