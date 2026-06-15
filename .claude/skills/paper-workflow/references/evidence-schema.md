# 证据矩阵与论点-引文映射 Schema

## evidence-matrix.csv

文献 → 论据映射。每行一条文献的证据记录。

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|:---:|
| ref_citekey | string | 文献 citekey（如 `wang2024RockyDesertification`） | ● |
| topic | string | 研究主题 | ● |
| region | string | 研究区/对象 | ○ |
| data_source | string | 数据来源 | ○ |
| method | string | 方法 | ● |
| key_finding | string | 关键结论/摘录（≤500字） | ● |
| limitation | string | 局限性 | ○ |
| usable_sections | string | 可用于哪些章节（逗号分隔，如 `introduction, literature_review`） | ● |
| page_ref | string | 原文页码/段落 | ○ |

### 示例

```csv
ref_citekey,topic,region,data_source,method,key_finding,limitation,usable_sections,page_ref
wang2024RockyDesertification,rocky_desertification_impacts,karst_region_southwest_china,remote_sensing+field_survey,spatial_analysis+statistical_modeling,"Rocky desertification significantly reduced ecosystem service value by 23%","single time point, no temporal trend",introduction+literature_review,p.3-5
```

## claim-citation-map.csv

论点 → 引文映射。每行一个待表达命题。

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|:---:|
| claim_id | string | 论点编号（C001, C002, ...） | ● |
| section | string | 所属章节 | ● |
| claim | string | 待表达命题（一句话，≤300字） | ● |
| supporting_refs | string | 支撑文献 citekey（逗号分隔） | ● |
| strength | enum | strong / medium / weak | ● |
| verified | enum | yes / pending / no | ● |

### 示例

```csv
claim_id,section,claim,supporting_refs,strength,verified
C001,introduction,"Rocky desertification is a major environmental challenge in karst regions","wang2024RockyDesertification,li2023KarstDegradation",strong,yes
C002,literature_review,"Existing studies focus on single ecosystem service indicators","chen2022ReviewEcosystem,zhang2021BiodiversityKarst",medium,pending
```

## 引用规则

1. **正文引用使用稳定 citekey**：`[@wang2024RockyDesertification]`，不使用 `canonical_id`（`ref-0001`）
2. **参考文献单一事实来源**：`references.bib` 和 `references.csl.json` 的 citekey 与 `catalog.jsonl` 一致
3. **写作阶段引用限制**：仅允许使用已进入 `evidence-matrix.csv` 且 `usable_sections` 匹配当前章节的文献
4. **[CITE NEEDED] 占位符**：无法核验的观点写 `[CITE NEEDED]`，由 `citation_verification` 阶段统一处理
5. **编号稳定性**：citekey 基于「第一作者姓 + 年份 + 标题关键词」，修改元数据后不变
