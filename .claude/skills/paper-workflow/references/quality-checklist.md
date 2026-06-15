# 各阶段质量检查项

## requirements
- [ ] 论文类型（paper_type）选择正确
- [ ] 研究类型（research_type）选择正确
- [ ] 语言设置正确
- [ ] 跳过逻辑与论文类型匹配
- [ ] 目标期刊明确（如适用）

## material_prep
- [ ] 材料清单完整
- [ ] 数据来源已确认可访问
- [ ] 无阻塞性缺项

## literature_search
- [ ] 检索覆盖核心库（按学科路由表）
- [ ] 补检库已执行（同义词/缩写）
- [ ] 检索日志记录完整（search-log.jsonl）
- [ ] 能力降级已记录（如某数据库不可用）

## literature_dedup
- [ ] DOI 重复已去除
- [ ] 标题相似重复已处理
- [ ] 预印本与正式发表版本已关联
- [ ] pending_review 列表已生成
- [ ] dedup-report.md 已生成

## deep_reading
- [ ] 核心文献均已创建阅读笔记
- [ ] screening.csv 中每条有明确的纳入/排除理由
- [ ] 阅读笔记带原文章节锚点

## evidence_matrix
- [ ] 每个论点有至少 1 条支撑文献
- [ ] evidence-matrix.csv 所有必填字段完整
- [ ] usable_sections 与实际章节匹配
- [ ] claim-citation-map.csv 的 strength 评级合理

## research_design
- [ ] 方法描述可复现
- [ ] 与论文类型匹配
- [ ] 伦理声明完整（如适用）

## data_analysis
- [ ] 分析脚本可运行
- [ ] data-dictionary.csv 字段说明完整
- [ ] 中间数据有备份

## charts_and_tables
- [ ] 图表分辨率 ≥300 dpi（打印）或 150 dpi（电子版）
- [ ] 编号唯一且连续
- [ ] 配色在灰度打印下可辨识
- [ ] 图例和轴标签完整
- [ ] SVG 源文件保留

## outline
- [ ] 层级 ≤4 级
- [ ] 逻辑连贯（IMRaD 或适合论文类型的结构）
- [ ] 覆盖所有必需章节
- [ ] 与证据矩阵的 usable_sections 对应

## writing
- [ ] 无 `[CITE NEEDED]` 残留（除有意保留的）
- [ ] 图表编号按出现顺序连续
- [ ] 公式：无 `\tag{}` 违规（docx profile），无 Unicode 下标
- [ ] 所有 `![]()` 引用的图片文件存在
- [ ] 标题层级无跳跃（## 接 # 正常，## 接 #### 异常）

## citation_verification
- [ ] 正文 citekey 全部在 references.bib 中存在
- [ ] 无孤立引用（正文有、bib 无）
- [ ] 无未使用引用（bib 有、正文无，可能遗漏引用）
- [ ] 无重复 citekey
- [ ] claim-citation-map.csv 的 verified 字段全部为 yes

## polishing
- [ ] 术语全文一致
- [ ] 无语法错误
- [ ] 符合目标期刊风格指南
- [ ] 句子长度合理（无过长复合句）

## formatting
- [ ] 字体/字号符合期刊/学校要求
- [ ] 页边距正确
- [ ] 表格为三线表
- [ ] 公式为 OMML 对象（docx）或 LaTeX 原生命令（tex）
- [ ] 图表编号连续且交叉引用正确

## originality_check
- [ ] 所有引用标记完整
- [ ] 无抄袭段落
- [ ] 数据来源可追溯
- [ ] 作者贡献声明完整

## quality_qa
- [ ] validate_manuscript 通过
- [ ] validate_citations 通过
- [ ] validate_docx / validate_tex 通过
- [ ] 所有 previous QA reports 中的 error 已修复
- [ ] 终稿复制到 outputs/latest/
