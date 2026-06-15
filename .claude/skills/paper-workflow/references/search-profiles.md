# 学科 → 数据库组合路由表

## 数据库角色

| 数据库 | 角色 | 适用条件 |
|--------|------|----------|
| CNKI | 中文核心库 | 中国语境、中文论文、区域/政策研究 |
| Scopus | 英文综合核心库 | 有 API 权限 |
| PubMed | 条件库：医学/生命科学 | 医学、生物、公共卫生 |
| arXiv | 条件库：前沿预印本 | 计算机、数学、物理、统计、AI、部分经济学 |
| Crossref | 元数据补全库 | DOI 补全、题名核验、去重 |
| ScienceDirect | 全文补充库 | 目标文章来自 Elsevier 平台 |

## 学科路由表

| 学科方向 | 默认数据库组合 |
|----------|---------------|
| 人文、民族学 | CNKI + Scopus（英文综合）；不启用 PubMed 和 arXiv |
| 社科、经管 | CNKI + Scopus；计量研究可选 arXiv |
| 生态环境、地理 | CNKI + Scopus + Crossref；按主题选 ScienceDirect |
| 医学、生物 | PubMed + Scopus + Crossref；按需补 ScienceDirect |
| 计算机、AI、统计 | Scopus + arXiv + Crossref |
| 工科 | Scopus + Crossref + ScienceDirect；按主题选 arXiv |

## 能力降级

`config.yaml` 记录实际可用能力：

```yaml
search_capabilities:
  cnki_search: available       # available | unavailable | browser_only
  cnki_download: available
  scopus: unavailable
  crossref: available
  pubmed: available
  arxiv: available
  sciencedirect: browser_only
```

### 降级规则

1. 理想组合中某库不可用 → 记录降级原因到 `search-log.jsonl`
2. 使用可用库补搜索
3. 用 Crossref 补元数据（DOI、题名、作者）
4. 不自带静默失败——降级时必须告知用户

### 降级示例

```
理想：PubMed + Scopus + Crossref（医学）
实际：PubMed API 不可用
降级：Scopus + Crossref + 手动 PubMed Web 搜索
记录：search-log.jsonl 中写入降级原因
```

## 检索流程

```
第一轮：核心关键词检索（主要库）
→ 标题与摘要初筛 → screening.csv
第二轮：同义词、缩写、近义概念补检
第三轮：针对论证缺口定向补检
第四轮（可选）：参考文献追溯
→ PDF 下载只在摘要初筛后，不通篇批量下载
```
