# paper-workflow v0.2: Stage Executor Bridge — Implementation Plan

> 日期：2026-06-16 | 基于 spec v0.2 | 状态：待审核
>
> 本计划将 spec 中的 6 阶段桥接设计拆解为 8 个里程碑、可独立提交的工程任务。

---

## 环境基线

| 项目 | 版本/状态 |
|------|----------|
| Python | 3.12.7 |
| Pandoc | 3.9.0.2 |
| 当前版本 | v0.1.2 |
| 当前分支 | `master` |
| 测试 | 296/296 通过 |
| 真实 Smoke Test | 2 次通过（石漠化综述 + 降雨预测复现） |
| v0.2 spec | `docs/design/2026-06-16-paper-workflow-v0.2-stage-executor.md` |

---

# Milestone 0：v0.2 基线确认

> 目标：确认开发基线干净，创建开发分支。

## 任务 0.1：基线核验

- **目标**：确认在 v0.1.2 上开发，所有测试通过
- **前置依赖**：无
- **新增/修改文件**：无
- **核心接口**：无
- **实现步骤**：
  1. `git log --oneline -3` 确认最新 commit 为 `ce881a9 fix: standardize project path handling across CLI`
  2. `git tag -l` 确认 `v0.1.2` 存在
  3. `pytest .claude/skills/paper-workflow/tests/ -v --tb=short` 确认 296/296 通过
  4. 确认 spec 文件存在：`docs/design/2026-06-16-paper-workflow-v0.2-stage-executor.md`
  5. 创建开发分支：`git checkout -b dev/paper-workflow-v0.2-stage-executor`
- **测试方法**：上述命令全部执行无报错
- **验收标准**：
  - 基线 commit = `ce881a9`
  - tag `v0.1.2` 存在
  - 296 测试全部通过
  - spec 文件存在
  - 开发分支已创建
- **提交建议**：无需提交（仅环境确认）

### Milestone 0 验收总结

```
✓ 基线 v0.1.2 确认
✓ 296 测试通过
✓ spec 文件存在
✓ 创建分支 dev/paper-workflow-v0.2-stage-executor
→ 开始 M1
```

---

# Milestone 1：Contract Registry + Schema

> 目标：建立 execution contract 静态定义层。这是 v0.2 的数据模型基础，所有执行器依赖此层。

## 任务 1.1：stage-execution.schema.json

- **目标**：定义 execution contract 的 JSON Schema，所有 contract 文件必须通过校验
- **前置依赖**：M0
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/schemas/stage-execution.schema.json`
- **核心接口**：
  - `jsonschema.validate(contract, schema)` → 所有 contract 文件必须通过
- **实现步骤**：
  1. 基于 spec §4 的 JSON Schema 草案编写正式 schema
  2. 定义 `executor_type` enum: `["script", "skill_handoff", "manual", "hybrid"]`
  3. 定义 `has_waiting_state` 可选字段
  4. 定义 `handoff_done` 和 `stage_done` 为 contract 顶层字段（不是 done_conditions 的子结构），skill_handoff 型必须同时包含两者
  5. 定义 `required_skill` 支持两种格式：
     - 字符串：`required_skill: nature-reader`
     - 语言映射对象：`required_skill: { zh: cnki-search, en: nature-academic-search }`
     - schema 使用 `oneOf: [{type: string}, {type: null}, {type: object, additionalProperties: {type: string}}]`
  6. 定义 `user_confirmation_required` 默认 false
  7. 定义 `fallback_on_failure` enum
  8. 在测试中覆盖两种 required_skill 格式
- **测试方法**：
  - `tests/test_schemas.py` 追加测试
  - 合法 contract 通过校验
  - 非法 executor_type 被拒绝
  - 缺少 required 字段被拒绝
- **验收标准**：
  - schema 文件符合 JSON Schema draft-07
  - 现有 schemas/ 目录下的其他 schema 不受影响
- **提交建议**：`feat: add stage-execution contract JSON Schema`

## 任务 1.2：17 个阶段 contract YAML 文件

- **目标**：为全部 17 个阶段编写 execution contract
- **前置依赖**：1.1
- **新增/修改文件**（17 个）：
  - `.claude/skills/paper-workflow/contracts/requirements.yaml`
  - `.claude/skills/paper-workflow/contracts/material_prep.yaml`
  - `.claude/skills/paper-workflow/contracts/literature_search.yaml`
  - `.claude/skills/paper-workflow/contracts/literature_dedup.yaml`
  - `.claude/skills/paper-workflow/contracts/deep_reading.yaml`
  - `.claude/skills/paper-workflow/contracts/evidence_matrix.yaml`
  - `.claude/skills/paper-workflow/contracts/research_design.yaml`
  - `.claude/skills/paper-workflow/contracts/data_analysis.yaml`
  - `.claude/skills/paper-workflow/contracts/charts_and_tables.yaml`
  - `.claude/skills/paper-workflow/contracts/outline.yaml`
  - `.claude/skills/paper-workflow/contracts/writing.yaml`
  - `.claude/skills/paper-workflow/contracts/citation_verification.yaml`
  - `.claude/skills/paper-workflow/contracts/polishing.yaml`
  - `.claude/skills/paper-workflow/contracts/formatting.yaml`
  - `.claude/skills/paper-workflow/contracts/originality_check.yaml`
  - `.claude/skills/paper-workflow/contracts/quality_qa.yaml`
  - `.claude/skills/paper-workflow/contracts/revision.yaml`
- **核心接口**：
  - 每个 `.yaml` 文件的顶层结构符合 `stage-execution.schema.json`
- **实现步骤**：
  1. 按 spec §5 中的设计为每个阶段编写 contract
  2. 对于 `outline`、`writing`、`formatting`、`quality_qa`、`polishing`、`requirements` 阶段，`input_artifacts` 中增加：
     - `materials/requirements/`（可选）
     - `materials/templates/`（可选）
     - `materials/examples/`（可选）
     - `materials/notes/`（可选）
     全部标记为 optional：不存在时不应 blocked
  3. 确认 executor_type 分布：
     - script × 4：`literature_dedup`、`evidence_matrix`、`formatting`、`quality_qa`
     - hybrid × 1：`citation_verification`
     - skill_handoff × 6：`literature_search`、`deep_reading`、`outline`、`writing`、`polishing`、`charts_and_tables`
     - manual × 6：`requirements`、`material_prep`、`research_design`、`data_analysis`、`originality_check`、`revision`
  4. `literature_search` 必须区分 `handoff_done` 和 `stage_done`
  5. `evidence_matrix` 的 `executor_type: script` 且 `user_confirmation_required: true`
  6. `revision` 的 `executor_type: manual`，标注 `not_in_v0.2_mvp: true`
  7. 所有 handoff 阶段指定 `has_waiting_state: true`
  8. 每个 contract 通过 schema 校验
- **测试方法**：
  - `tests/test_schemas.py` 追加：遍历 contracts/ 目录，每个文件通过 schema 校验
  - executor_type 分布统计正确
- **验收标准**：
  - 17 个 contract 文件全部存在
  - 全部通过 schema 校验
  - executor_type 分布与 spec 一致
- **提交建议**：`feat: add 17 stage execution contracts`

## 任务 1.3：参考文档

- **目标**：编写 3 个 references/ 文档，为后续开发和用户提供阶段执行器说明
- **前置依赖**：1.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/references/stage-executors.md`
  - `.claude/skills/paper-workflow/references/execution-contracts.md`
  - `.claude/skills/paper-workflow/references/phase6-workflow.md`
- **核心接口**：无（参考文档）
- **实现步骤**：
  1. `stage-executors.md`：每个阶段的执行器类型、输入输出、完成条件、用户确认点
  2. `execution-contracts.md`：contract 字段说明、executor_type 语义、done_conditions 表达式语法
  3. `phase6-workflow.md`：用户视角 6 阶段流程说明，17→6 映射表，每阶段调用的 skill
- **测试方法**：文件可被 Markdown 渲染器解析，交叉引用正确
- **验收标准**：3 个文件存在，内容非空
- **提交建议**：`docs: add stage executor reference documentation`

## 任务 1.4：workflow state schema / status 枚举扩展

- **目标**：v0.2 引入 `waiting_for_user` 和 `pending_confirmation` 状态，必须更新 workflow-state schema 和 workflow_state.py 的合法状态集合
- **前置依赖**：1.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/schemas/workflow-state.schema.json`
  - `.claude/skills/paper-workflow/scripts/workflow_state.py`
- **核心接口**：
  - `set_stage_status()` 的合法 status 集合
  - workflow-state.schema.json 的 status enum
- **实现步骤**：
  1. 更新 `workflow-state.schema.json`：stages 中 status 的 enum 从 `["pending", "in_progress", "done", "skipped", "blocked"]` 扩展为 `["pending", "in_progress", "waiting_for_user", "pending_confirmation", "done", "skipped", "blocked"]`
  2. 更新 `workflow_state.py` 中 `set_stage_status()` 的 `valid_statuses` 集合
  3. 更新测试 fixture（`conftest.py`）中合法状态
  4. 增加测试：`waiting_for_user` 和 `pending_confirmation` 合法；未知状态非法
- **状态语义**：

  | 状态 | 含义 |
  |------|------|
  | `pending` | 尚未开始 |
  | `in_progress` | 正在执行 |
  | `waiting_for_user` | handoff 已生成或 manual 指令已输出，等待用户/skill 完成 |
  | `pending_confirmation` | 产物已生成，需要用户 confirm 后才能标记 done |
  | `done` | 完成 |
  | `skipped` | 已跳过 |
  | `blocked` | 前置依赖未满足或 done_conditions 检查失败 |
- **测试方法**：
  - `tests/test_workflow_state.py` 追加
  - `set_stage_status(state, "deep_reading", "waiting_for_user")` 成功
  - `set_stage_status(state, "evidence_matrix", "pending_confirmation")` 成功
  - 非法状态 → 返回 error
  - schema 校验：含 `waiting_for_user` 的 state 通过校验
- **验收标准**：
  - schema 和代码同步更新
  - 旧有合法状态不受影响
  - 新状态通过 schema 校验
- **提交建议**：`feat: extend workflow state with waiting_for_user and pending_confirmation`

## 任务 1.5：per-paper materials directory 设计与初始化

- **目标**：为每篇论文项目新增 `materials/` 目录，存放用户提供的参考材料、格式要求和模板。这是基础设施，不是 v0.3 功能。
- **前置依赖**：1.4（可并行）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/init_project.py`（可选，v0.2 可推迟）
  - `materials/README.md`（模板，随 skill 分发）
- **核心接口**：无（目录结构 + input_artifacts 约定）
- **目录设计**：
  ```
  materials/
  ├── requirements/        # 论文要求、课程要求、投稿指南、格式规范
  ├── templates/           # Word 模板、reference.docx、LaTeX 模板、封面模板
  ├── examples/            # 参考范文、往年论文、示例样稿
  ├── notes/               # 用户研究想法、导师要求、特殊说明
  └── README.md            # 本目录说明
  ```
- **设计原则**：
  1. `materials/` 是 per-paper 上下文材料入口，不是正式文献库
  2. 不参与 citation validation，不写入 `references.bib`
  3. 不替代 `literature/catalog.jsonl`
  4. `formatting` 阶段可读取 `materials/templates/reference.docx` 作为可选模板
  5. skill_handoff 阶段的 prompt 可列出 `materials/` 文件清单作为上下文
  6. 没有 `materials/` 目录时，所有阶段不应 blocked（全部可选）
- **实现步骤**：
  1. 创建 `materials/README.md` 作为模板（说明每种子目录的用途）
  2. 在 `init_project.py` 中默认创建空 `materials/` 及子目录（或在 v0.2 实现阶段手动补充）
  3. 在 `init_project.py` 的目录创建列表中增加 `materials/requirements/`、`materials/templates/`、`materials/examples/`、`materials/notes/`
  4. 各子目录放置 `.gitkeep` 确保被 git track（如果纸项目在仓库内）
- **测试方法**：
  - 新初始化项目 → `materials/` 及其 4 个子目录存在
  - `materials/README.md` 存在且非空
- **验收标准**：
  - 目录结构正确
  - 与 `literature/`、`citations/`、`references.bib` 不混淆
  - README 说明清晰
- **提交建议**：`feat: add per-paper materials directory with subdirectories`

### Milestone 1 验收总结

```
✓ stage-execution.schema.json 就位
✓ 17 个 contract YAML 全部通过 schema 校验
✓ workflow-state schema 状态枚举扩展为 7 种合法状态
✓ 4 个 references 文档就位
✓ materials/ 目录设计就位（init 自动创建）
✓ executor_type 分布：script=4, hybrid=1, skill_handoff=6, manual=6
```

---

# Milestone 2：stage_executor.py 框架

> 目标：实现阶段执行器核心框架（分发器 + done_conditions + artifact logging），但不接入 commands.py。

## 任务 2.1：stage_executor.py 核心

- **目标**：实现 contract 加载、校验、分发框架
- **前置依赖**：M1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`
- **核心接口**：
  ```python
  def load_contract(stage_id: str) -> dict
  def list_contracts() -> list[dict]
  def validate_contract(contract: dict) -> list[str]
  def get_contracts_by_type(executor_type: str) -> list[dict]
  ```
- **实现步骤**：
  1. `load_contract()`：从 `contracts/<stage_id>.yaml` 读取并解析 YAML
  2. `list_contracts()`：遍历 contracts/ 目录，返回全部 contract 列表
  3. `validate_contract()`：用 `stage-execution.schema.json` 校验
  4. `get_contracts_by_type()`：按 executor_type 过滤
  5. 所有路径基于 `project_dir` 参数或 `contracts/` 相对于脚本目录解析
- **测试方法**：
  - `tests/test_stage_executor.py`（新增）
  - `load_contract("literature_dedup")` 返回正确 contract
  - `list_contracts()` 返回 17 条
  - `get_contracts_by_type("script")` 返回 4 条
  - 不存在的 stage_id → 抛明确异常
- **验收标准**：
  - contract 加载/列表/过滤/校验 四项功能正确
  - 错误的 contract 被校验捕获
- **提交建议**：`feat: implement stage executor contract loader`

## 任务 2.2：done_conditions 与 artifact logging

- **目标**：实现完成条件检查引擎和产物日志
- **前置依赖**：2.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（追加）
- **核心接口**：
  ```python
  def check_done_conditions(stage_id: str, project_dir: Path) -> tuple[bool, list[str]]
  def check_handoff_done(stage_id: str, project_dir: Path) -> tuple[bool, list[str]]
  def log_artifacts(project_dir: Path, stage_id: str, artifacts: list[str], executor: str) -> None
  ```
- **实现步骤**：
  1. `check_done_conditions()`：
     - 根据 executor_type 自动选择条件字段：
       - `script`、`manual`、`hybrid` → 读取 `contract["done_conditions"]`
       - `skill_handoff` → 读取 `contract["stage_done"]`（检查用户/skill 执行后的真实产物，不是 handoff 生成状态）
     - 支持条件表达式：`file_exists:<path>`、`record_count:<path> > N`、`csv_has_rows:<path>`、`no_unresolved_cite_needed:<path>`、`qa_errors == 0`
     - 返回 `(all_met, unmet_list)`
  2. `check_handoff_done()`：
     - 读取 `contract["handoff_done"]`（skill_handoff 型专用）
     - 检查 `.paper-workflow/handoffs/<stage_id>.json` 存在
  3. `log_artifacts()`：
     - 追加 JSON 行到 `.paper-workflow/artifact-manifest.jsonl`
     - 包含 timestamp、stage_id、action、artifacts、executor
  4. 条件表达式解析器（独立函数 `_evaluate_condition()`）
- **测试方法**：
  - `tests/test_stage_executor.py` 追加
  - `file_exists`：存在/不存在/空文件
  - `record_count`：0 条 / 3 条 / 边界
  - `csv_has_rows`：空 CSV / 有数据
  - `no_unresolved_cite_needed`：有/无 [CITE NEEDED]
  - artifact logging：记录写入后可从 manifest 读回
- **验收标准**：
  - 每种条件表达式正确评估
  - 不存在的条件语法返回明确错误
  - artifact 正确写入 manifest
- **提交建议**：`feat: implement done conditions checker and artifact logger`

## 任务 2.3：execute_stage() 分发器

- **目标**：实现主分发函数，按 executor_type 路由到对应内部 stub
- **前置依赖**：2.2
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（追加）
- **核心接口**：
  ```python
  def execute_stage(stage_id: str, project_dir: Path, state: dict, config: dict,
                    *, override: bool = False) -> dict
  ```
- **实现步骤**：
  1. `load_contract(stage_id)` → 获取 contract
  2. 检查 `preconditions`
  3. 按 `executor_type` 分发：
     - `script` → `_execute_script_stage()`（stub，M3 实现）
     - `skill_handoff` → `_execute_skill_handoff_stage()`（stub，M4 实现）
     - `manual` → `_execute_manual_stage()`（stub，M5 实现）
     - `hybrid` → `_execute_hybrid_stage()`（stub，M6 实现）
  4. 返回结构化结果 dict。所有字段由 `stage_executor` 统一返回，`commands.py` 在 M7 中根据结果调用 `set_stage_status()`。
     返回结构：

     ```python
     # script 型成功
     {"executed": True, "stage_id": "formatting", "executor_type": "script",
      "recommended_status": "done", "artifacts": [...], "warnings": [], "blocked_reason": None}

     # handoff 生成
     {"executed": False, "handoff_generated": True, "recommended_status": "waiting_for_user",
      "handoff_path": ".paper-workflow/handoffs/outline.json", "artifacts": [...],
      "warnings": []}

     # 需要用户确认的 script
     {"executed": True, "requires_confirmation": True,
      "recommended_status": "pending_confirmation", "artifacts": [...]}

     # 失败
     {"executed": False, "recommended_status": "blocked",
      "blocked_reason": "precondition: catalog.jsonl is empty"}
     ```

     **关键约束**：`stage_executor.py` 不直接调用 `set_stage_status()` 或写 `state.yaml`。状态写入由 `commands.py` 在 M7 中统一处理，保持状态机单一出口。
  5. 此时所有内部函数为 stub：打印 `[v0.2 stub]` 并返回占位结果（recommended_status = "done"）
- **测试方法**：
  - `tests/test_stage_executor.py` 追加
  - `execute_stage("literature_dedup", ...)` 返回 script stub 结果
  - `execute_stage("outline", ...)` 返回 skill_handoff stub 结果
  - 未知 stage_id → 返回错误
  - `override=True` 不影响分发路由
- **验收标准**：
  - 分发路由正确
  - stub 结果结构统一
  - `commands.py` 未被修改
- **提交建议**：`feat: implement stage execution dispatcher with typed stubs`

### Milestone 2 验收总结

```
✓ load_contract / list_contracts / validate_contract 可用
✓ check_done_conditions 表达式引擎可用
✓ log_artifacts 可用
✓ execute_stage 分发路由正确
✓ 4 个 executor stub 就位（script/skill_handoff/manual/hybrid）
✓ commands.py 未被修改
```

---

# Milestone 3：script 型阶段执行器

> 目标：将 4 个 script 型阶段从 stub 改为真实调用。

## 任务 3.1：literature_dedup 执行器

- **目标**：`literature_dedup` 阶段调用 `dedup.py` 执行去重
- **前置依赖**：M2
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（`_execute_script_stage()` 实现）
- **核心接口**：
  - `stage_executor._execute_script_stage()` → 根据 stage_id 分发到具体实现
- **实现步骤**：
  1. 在 `_execute_script_stage()` 中为 `literature_dedup` 实现调用逻辑
  2. 读取 `literature/catalog.jsonl`
  3. 调用 `dedup.py` 的核心函数（import + 函数调用）
  4. 检查 `literature/dedup-report.md` 是否生成
  5. `log_artifacts()` 记录产物
  6. 失败时返回 `{"executed": false, "blocked_reason": "..."}`
- **测试方法**：
  - `tests/test_stage_executor.py` 追加
  - 有重复记录的 catalog → 去重后条数减少
  - 无重复的 catalog → 正常完成，report 存在
  - 空 catalog → blocked（precondition 不满足）
- **验收标准**：
  - `literature_dedup` 可真实运行
  - 产物正确写入 manifest
- **提交建议**：`feat: implement literature_dedup script executor`

## 任务 3.2：evidence_matrix 执行器

- **目标**：`evidence_matrix` 阶段调用 `evidence_manager.py`
- **前置依赖**：3.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（追加）
- **核心接口**：同上
- **实现步骤**：
  1. 检查 `user_confirmation_required: true`
  2. 调用 `evidence_manager.py` 初始化/校验
  3. 检查 evidence-matrix.csv 和 claim-citation-map.csv
  4. **不直接标记 done**，返回 `{"executed": true, "requires_confirmation": true}`
  5. 产物记录到 manifest
- **测试方法**：
  - evidence 文件存在且格式正确 → 执行成功，需确认
  - evidence 文件缺失 → 初始化空文件，提示用户填充
- **验收标准**：
  - evidence_matrix 脚本部分正常工作
  - 返回 `requires_confirmation: true`
- **提交建议**：`feat: implement evidence_matrix script executor`

## 任务 3.3：formatting 执行器

- **目标**：`formatting` 阶段调用 `render.py`
- **前置依赖**：3.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（追加）
- **实现步骤**：
  1. 检查 `manuscript/main.md` 存在
  2. 读取 config 中的 `default_profile`（默认 thesis-cn）
  3. 检查 `materials/templates/reference.docx` 是否存在——如果存在，作为 Word 渲染的可选参考模板传给 `render.py`；**不存在不是错误，不能 blocked**
  4. 调用 `render.py` 的 `render()` 函数
  5. 检查 `outputs/latest/` 中有渲染产物
  6. 失败时 blocked
- **测试方法**：
  - 有 manuscript 的项目 → 渲染成功
  - 无 manuscript → blocked
- **验收标准**：
  - formatting 可真实渲染
  - 版本号自增
- **提交建议**：`feat: implement formatting script executor`

## 任务 3.4：quality_qa 执行器

- **目标**：`quality_qa` 阶段调用 `qa_report.py`
- **前置依赖**：3.3
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（追加）
- **实现步骤**：
  1. 调用 `qa_report.py` 的 `run_all_checks()`
  2. 检查 QA report 中的 errors 计数
  3. `qa_errors == 0` → 可 done
  4. `qa_errors > 0` → blocked 或 passed_with_warnings
- **测试方法**：
  - 干净项目 → QA 全通过
  - 有 warning 无 error → passed_with_warnings，仍可 done
  - 有 error → blocked
- **验收标准**：
  - QA 正确运行
  - errors > 0 时 blocked
- **提交建议**：`feat: implement quality_qa script executor`

### Milestone 3 验收总结

```
✓ literature_dedup 真实调用 dedup.py
✓ evidence_matrix 真实调用 evidence_manager.py + requires_confirmation
✓ formatting 真实调用 render.py
✓ quality_qa 真实调用 qa_report.py
✓ 4 个 script 阶段全部可工作
```

---

# Milestone 4：skill_handoff 引擎

> 目标：实现 skill_handoff 阶段的任务包生成，不调用 skill 本身。

## 任务 4.1：stage_prompts.py

- **目标**：实现 handoff prompt 模板渲染引擎
- **前置依赖**：M1（contract 定义完成）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_prompts.py`
- **核心接口**：
  ```python
  def render_handoff_prompt(stage_id: str, project_dir: Path, state: dict, config: dict) -> str
  def get_template_variables(stage_id: str, project_dir: Path, state: dict, config: dict) -> dict
  ```
- **实现步骤**：
  1. 加载 contract → 读取 `handoff_prompt_template`
  2. 从 `config.yaml` / `state.yaml` / `catalog.jsonl` 中提取模板变量
  3. 用 Python `str.format()` 渲染模板
  4. 每个阶段有预设的 fallback prompt（模板渲染失败时使用）
  5. 变量至少包括：`{topic}`, `{discipline}`, `{language}`, `{paper_type}`, `{research_type}`, `{skill}`
- **测试方法**：
  - `tests/test_stage_prompts.py`（新增）
  - `render_handoff_prompt("outline", ...)` 返回包含 "nature-writing" 的 prompt
  - 缺失的模板变量 → 警告但不崩溃
  - 模板为空 → 使用 fallback prompt
- **验收标准**：
  - 6 个 skill_handoff 阶段都能渲染出有效 prompt
  - 模板变量替换正确
- **提交建议**：`feat: implement handoff prompt template engine`

## 任务 4.2：handoff 文件生成

- **目标**：实现 `.paper-workflow/handoffs/<stage_id>.json` 文件写入
- **前置依赖**：4.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（`_execute_skill_handoff_stage()` 实现）
- **核心接口**：
  ```python
  def generate_handoff(stage_id: str, project_dir: Path, state: dict, config: dict) -> Path
  ```
- **实现步骤**：
  1. 创建 `.paper-workflow/handoffs/` 目录
  2. 收集 input_artifacts 状态（存在、大小、行数、缺失文件列表）
  3. 扫描 `materials/` 目录（如果存在），生成文件清单摘要（只列文件名和类型，**不**把全文塞进 prompt）
  4. 调用 `stage_prompts.render_handoff_prompt()` 生成 task_prompt，将 materials 清单作为模板变量 `{materials_summary}` 注入
  5. 写入 `.paper-workflow/handoffs/<stage_id>.json`
  6. 更新 `.paper-workflow/handoffs/latest.json`（写入 `{"stage_id": "...", "timestamp": "..."}`）
  7. 返回 handoff 文件路径
  8. 阶段状态 → `waiting_for_user`
- **测试方法**：
  - `tests/test_stage_executor.py` 追加
  - handoff JSON 包含所有必要字段
  - `latest.json` 正确更新
  - 连续生成不同阶段的 handoff → 各自文件独立，不覆盖
- **验收标准**：
  - 6 个 skill_handoff 阶段的 handoff 文件生成正确
  - 文件内容包含 stage_id、skill、task_prompt、expected_outputs
- **提交建议**：`feat: implement skill handoff file generation`

### Milestone 4 验收总结

```
✓ stage_prompts.py 模板渲染可用
✓ 6 个 handoff JSON 文件生成正确
✓ handoffs/ 目录结构符合 spec 要求
✓ waiting_for_user 状态可被设置
```

---

# Milestone 5：manual 阶段与 confirm 命令

> 目标：实现 manual 阶段提示和 `confirm <stage>` 命令。

## 任务 5.1：_execute_manual_stage() 实现

- **目标**：manual 阶段输出结构化任务说明
- **前置依赖**：M2
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`
- **核心接口**：`_execute_manual_stage(stage_id, contract, project_dir) → dict`
- **实现步骤**：
  1. 读取 contract 的 input/output artifacts、done_conditions
  2. 检查 input_artifacts 状态
  3. 打印任务说明（中文）：任务描述、输入文件状态、期望输出、完成标准、确认命令
  4. 返回 `{"executed": false, "requires_manual_action": true}`
  5. 6 个 manual 阶段各自有清晰的任务说明
- **测试方法**：
  - `research_design` → 输出中包含 "实验方案" 等关键词
  - `requirements` → 输出中包含论文需求说明
  - `revision` → 输出标注 future/v0.3
- **验收标准**：
  - 6 个 manual 阶段输出有意义的中文说明
  - revision 阶段标注为 future
- **提交建议**：`feat: implement manual stage task descriptions`

## 任务 5.2：confirm 命令

- **目标**：在 `commands.py` 中添加 `confirm <stage>` 子命令
- **前置依赖**：5.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/commands.py`
- **修改范围限制**：
  - ✅ 可以修改 argparse 和新增 `cmd_confirm()` 函数
  - ✅ 可以新增 `confirm` 子命令解析
  - ❌ 不允许修改 `cmd_run()` / `cmd_status()` / `cmd_resume()` 的现有行为
  - ❌ 不允许替换 `_execute_stage()` stub
  - ❌ 真正接入 `stage_executor` 只在 M7 做
- **核心接口**：
  ```bash
  python scripts/commands.py confirm <stage_id> --project /path
  python scripts/commands.py confirm <stage_id> --override --project /path
  ```
- **实现步骤**：
  1. 在 `commands.py` 的 argparse 中添加 `confirm` 子命令
  2. 实现 `cmd_confirm(stage_id, override, project)` 函数：
     - 加载 state/config
     - 调用 `stage_executor.check_done_conditions()`
     - 全部满足 → `set_stage_status(state, stage_id, "done")`
     - 不满足 → 保持 in_progress 或标记 blocked
     - `--override` → 强制 done，记录 override 日志
  3. `confirm` 只能用于 `in_progress` 或 `waiting_for_user` 状态的阶段
  4. 已经 `done` 的阶段 → 提示"已完成，无需确认"
- **测试方法**：
  - `tests/test_commands.py` 追加
  - 产物满足 done_conditions → confirm 成功，阶段 done
  - 产物不满足 → confirm 失败，阶段不 done
  - `--override` → 强制 done
  - 对 `done` 阶段的 confirm → 提示已 done
- **验收标准**：
  - `confirm` 不能直接绕过 done_conditions
  - `--override` 可强制，记录日志
- **提交建议**：`feat: implement confirm command with done_conditions check`

### Milestone 5 验收总结

```
✓ _execute_manual_stage() 输出任务说明
✓ commands.py confirm 子命令可用
✓ done_conditions 检查在 confirm 中生效
✓ --override 强制逻辑正确
```

---

# Milestone 6：hybrid 阶段 citation_verification

> 目标：实现唯一 hybrid 阶段——先走 script 检查，有问题时生成 skill handoff。

## 任务 6.1：citation_verification 执行器

- **目标**：citation_verification 先调 validate_citations.py，有问题时生成 nature-citation handoff
- **前置依赖**：M3（script executor）、M4（handoff engine）
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/stage_executor.py`（`_execute_hybrid_stage()` 实现）
- **实现步骤**：
  1. 先走 script 路径：调用 `validate_citations.py`
  2. 检查结果：
     - 0 missing citekey + 0 [CITE NEEDED] + 0 evidence gap → 直接 done
     - 有问题 → 生成 `nature-citation` handoff prompt
     - 写入 `.paper-workflow/handoffs/citation_verification.json`
     - 状态进入 `waiting_for_user`
  3. 不直接调用 nature-citation skill
  4. 产物：`outputs/qa/citation-report.md`
- **测试方法**：
  - 干净 manuscript（所有 citekey 在 bib 中）→ 直接 done
  - manuscript 有 missing citekey → 生成 handoff，waiting_for_user
  - manuscript 有 [CITE NEEDED] → 生成 handoff
  - 生成 handoff 内容包含问题 citekey 列表
- **验收标准**：
  - 干净路径自动完成
  - 问题路径正确生成 handoff
- **提交建议**：`feat: implement hybrid citation_verification executor`

### Milestone 6 验收总结

```
✓ citation_verification 干净路径自动 done
✓ citation_verification 有问题的路径生成 handoff
✓ handoff 中包含具体问题 citekey 列表
```

---

# Milestone 7：commands.py 接入 stage_executor

> 目标：用 stage_executor 替换 `_execute_stage()` stub，完成全部阶段执行器的集成。

## 任务 7.1：_execute_stage() 替换

- **目标**：`commands.py` 的 `cmd_run()` 调用 `stage_executor.execute_stage()`
- **前置依赖**：M3, M4, M5, M6
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/commands.py`
- **实现步骤**：
  1. 在 `commands.py` 顶部 import `stage_executor`
  2. 修改 `cmd_run()`：
     - 将 `_execute_stage(stage_id)` 替换为：
       ```python
       exec_result = stage_executor.execute_stage(
           stage_id, root, state, config, override=override
       )
       ```
     - 解析 exec_result：
       - `executed=True` + `requires_confirmation=False` → 调用 `stage_executor.check_done_conditions()` → 通过则 done
       - `executed=True` + `requires_confirmation=True` → 保持 in_progress，提示用户 confirm
       - `handoff_generated=True` → 设置 waiting_for_user，打印 handoff prompt
       - `handoff_generated=True` → **不标记 done**
       - `requires_manual_action=True` → 保持 in_progress
       - 执行失败 → 保持 in_progress 或 blocked
  3. 删除旧的 `_execute_stage()` stub
  4. 保留 `cmd_status()`、`cmd_resume()` 中已有的状态展示逻辑
- **实现步骤**：
  1. 旧有测试全部通过（不能破坏 M2 测试）
  2. `cmd_run("literature_dedup")` → 真实执行 dedup
  3. `cmd_run("outline")` → 生成 handoff 文件，不标记 done
  4. `cmd_run("research_design")` → 输出 manual 任务说明
  5. `cmd_run("nonexistent")` → 报错
- **测试方法**：
  - `tests/test_commands.py` 追加
  - `tests/test_stage_executor.py` 追加集成测试
  - 现有 TestRun / TestStatus / TestResume 全部通过
- **验收标准**：
  - `run <stage>` 调度到正确的执行器
  - 状态机不被破坏
  - 旧有 296 测试全部通过
- **提交建议**：`feat: replace _execute_stage stub with stage_executor`

## 任务 7.2：status / resume 适配

- **目标**：`status` 和 `resume` 命令能正确展示 v0.2 新增的状态信息
- **前置依赖**：7.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/commands.py`
- **实现步骤**：
  1. `cmd_status()`：
     - 展示 `waiting_for_user` 阶段（区别于 `in_progress`）
     - 展示 handoff 文件路径（如果存在）
     - 展示 `requires_confirmation` 标记
  2. `cmd_resume()`：
     - `waiting_for_user` 阶段 → 提示"此阶段需要你执行对应 skill 后运行 confirm"
     - `requires_confirmation` → 提示运行 confirm
- **测试方法**：
  - `tests/test_commands.py` 追加
- **验收标准**：
  - status 正确区分 in_progress / waiting_for_user / blocked
- **提交建议**：`feat: adapt status and resume for v0.2 stage states`

### Milestone 7 验收总结

```
✓ _execute_stage() stub 已删除
✓ cmd_run() 通过 stage_executor 分发
✓ status 展示 waiting_for_user / requires_confirmation
✓ resume 提示用户下一步操作
✓ 旧有 296 测试仍通过 + 新增测试
```

---

# Milestone 8：集成测试与烟雾测试

> 目标：新增集成测试，确保 v0.2 所有执行器类型可正常工作，并跑通一次完整的 6 阶段 smoke test。

## 任务 8.1：执行器集成测试

- **目标**：新增覆盖所有 executor_type 的集成测试
- **前置依赖**：M7
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/tests/test_stage_executor.py`（扩充）
- **测试覆盖**：
  1. **script 阶段**：
     - `literature_dedup`：真实去重
     - `evidence_matrix`：初始化 + requires_confirmation
     - `formatting`：真实渲染 + 版本号
     - `quality_qa`：QA 运行 + errors 检查
  2. **skill_handoff 阶段**：
     - handoff 文件内容验证
     - prompt 模板渲染检查
     - 连续多次 handoff 不覆盖
  3. **manual 阶段**：
     - 任务说明输出
     - confirm 正常路径
     - confirm 失败路径
     - confirm --override
  4. **hybrid 阶段**：
     - citation_verification 干净路径
     - citation_verification 问题路径 → handoff
- **测试方法**：
  - `pytest .claude/skills/paper-workflow/tests/test_stage_executor.py -v`
- **验收标准**：
  - 每个 executor_type 至少有 1 个正常路径 + 1 个异常路径测试
  - 总测试数 ≥ 原本 296 + 新增
- **提交建议**：`test: add integration tests for all executor types`

## 任务 8.2：完整 6 阶段端到端测试

- **目标**：用 `mini-paper` fixture 跑通全部 6 个 Phase
- **前置依赖**：8.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/tests/test_e2e_v02.py`（新增）
- **测试流程**：
  ```
  Phase 1: literature_dedup（script）
  Phase 2: evidence_matrix（script + confirm）
  Phase 3: outline（skill_handoff → 验证 handoff 生成）
  Phase 4: writing（skill_handoff → 验证 handoff 生成）
           + citation_verification（hybrid）
  Phase 5: charts_and_tables（skill_handoff → 验证 handoff 生成）
  Phase 6: formatting（script）+ quality_qa（script）
  ```
- **测试方法**：
  - `pytest .claude/skills/paper-workflow/tests/test_e2e_v02.py -v`
- **验收标准**：
  - 6 阶段端到端可跑通
  - 每个阶段的产物正确生成
  - 状态流转正确
- **提交建议**：`test: add end-to-end 6-phase workflow test`

## 任务 8.3：真实 smoke test

- **目标**：在已有真实论文项目上跑通 v0.2 阶段执行器
- **前置依赖**：8.2
- **使用项目**：
  - 优先使用已有真实项目副本（如 `papers/ml-rainfall-prediction/`）
  - **如果真实项目路径不存在，则复制 `tests/fixtures/mini-paper/` 到临时目录进行 smoke test**
  - 原则：所有自动测试必须能在干净 clone 的仓库中运行，不依赖本机私有路径
- **执行步骤**：
  1. `run literature_dedup` → 验证去重执行
  2. `run evidence_matrix` → 验证 evidence_manager 调用
  3. `run formatting` → 验证渲染
  4. `run quality_qa` → 验证 QA
  5. 验证 `status` 正确展示
  6. 验证 `outputs/latest/` 更新
- **验收标准**：
  - script 型阶段在真实项目上可运行
  - 产物与之前 manual 调用的结果一致
  - QA report 状态正确
- **提交建议**：`test: real project smoke test for v0.2 executors`

### Milestone 8 验收总结

```
✓ 所有 executor_type 有集成测试
✓ 6 阶段端到端测试通过
✓ 真实 smoke test 通过
✓ 总测试数 ≥ 296 + 新增
```

---

## 附录 A：任务依赖图

```
M0（基线确认）
└── M1（Contract Registry + Schema + Materials）
    ├── 1.1 schema ───────────────────────────────────────┐
    ├── 1.2 17 contracts ──→ 依赖 1.1 ────────────────────┤
    ├── 1.3 参考文档 ──→ 依赖 1.2 ────────────────────────┤
    ├── 1.4 state schema 扩展 ──→ 依赖 1.1 ──→ 可并行 1.2/1.3 ┤
    └── 1.5 materials 目录 ──→ 独立，可并行 1.1–1.4 ──────┘
                                                            │
M2（stage_executor.py 框架）← 依赖 M1                        │
    ├── 2.1 load/validate ─────────────────────────────────┤
    ├── 2.2 done_conditions + artifact log ──→ 依赖 2.1 ───┤
    └── 2.3 execute_stage 分发器 ──→ 依赖 2.2 ─────────────┤
                                                            │
M3（script 执行器）← 依赖 M2                                  │
    ├── 3.1 literature_dedup ──────────────────────────────┤
    ├── 3.2 evidence_matrix ──→ 可并行 3.1 ─────────────────┤
    ├── 3.3 formatting ──→ 可并行 3.1 ─────────────────────┤
    └── 3.4 quality_qa ──→ 可并行 3.1                      │
                                                            │
M4（skill_handoff 引擎）← 依赖 M1 ──→ 可与 M2/M3 并行        │
    ├── 4.1 stage_prompts.py ──────────────────────────────┤
    └── 4.2 handoff 文件生成 ──→ 依赖 4.1 + M2 ─────────────┤
                                                            │
M5（manual + confirm）← 依赖 M2 ──→ 可与 M3/M4 并行         │
    ├── 5.1 _execute_manual_stage ─────────────────────────┤
    └── 5.2 confirm 命令 ──→ 依赖 5.1 ─────────────────────┤
                                                            │
M6（hybrid）← 依赖 M3 + M4                                  │
    └── 6.1 citation_verification ─────────────────────────┤
                                                            │
M7（commands.py 接入）← 依赖 M3 + M4 + M5 + M6               │
    ├── 7.1 _execute_stage 替换 ───────────────────────────┤
    └── 7.2 status / resume 适配 ──→ 依赖 7.1 ─────────────┤
                                                            │
M8（集成测试 + smoke test）← 依赖 M7                         │
    ├── 8.1 集成测试 ──────────────────────────────────────┤
    ├── 8.2 端到端测试 ──→ 可并行 8.1 ─────────────────────┤
    └── 8.3 真实 smoke test ──→ 依赖 8.1, 8.2 ─────────────┤
```

### 并行化建议

| 可并行组 | 条件 |
|----------|------|
| M1.5 + M1.1–M1.4 | materials 目录独立于 contract/schema |
| M3（script）+ M4（handoff）+ M5（manual） | 都只依赖 M2 框架，互不依赖 |
| M3.1 + M3.2 + M3.3 + M3.4 | 4 个 script 阶段各自独立 |
| M5.1 + M4.1 | 都不依赖 M3 |
| M8.1 + M8.2 | 不同测试文件 |

---

## 附录 B：建议 Git 提交顺序

```
 1  feat: add stage-execution contract JSON Schema               [1.1]
 2  feat: add 17 stage execution contracts                        [1.2]
 3  feat: extend workflow state with new statuses                 [1.4]
 4  feat: add per-paper materials directory                       [1.5]
 5  docs: add stage executor reference documentation              [1.3]
    → M1 完成
 4  feat: implement stage executor contract loader               [2.1]
 5  feat: implement done conditions checker and artifact logger  [2.2]
 6  feat: implement stage execution dispatcher with typed stubs  [2.3]
    → M2 完成
 7  feat: implement literature_dedup script executor             [3.1]
 8  feat: implement evidence_matrix script executor              [3.2]
 9  feat: implement formatting script executor                   [3.3]
10  feat: implement quality_qa script executor                   [3.4]
    → M3 完成
11  feat: implement handoff prompt template engine               [4.1]
12  feat: implement skill handoff file generation                [4.2]
    → M4 完成
13  feat: implement manual stage task descriptions               [5.1]
14  feat: implement confirm command with done_conditions check   [5.2]
    → M5 完成
15  feat: implement hybrid citation_verification executor        [6.1]
    → M6 完成
16  feat: replace _execute_stage stub with stage_executor        [7.1]
17  feat: adapt status and resume for v0.2 stage states          [7.2]
    → M7 完成
18  test: add integration tests for all executor types           [8.1]
19  test: add end-to-end 6-phase workflow test                   [8.2]
20  test: real project smoke test for v0.2 executors             [8.3]
    → M8 完成 → 合并到 master
```

---

## 附录 C：v0.2 验收清单

### 功能验收

- [ ] `run literature_dedup` → 真实调用 dedup.py
- [ ] `run evidence_matrix` → 调用 evidence_manager + requires_confirmation
- [ ] `run formatting` → 真实调用 render.py
- [ ] `run quality_qa` → 真实调用 qa_report.py
- [ ] `run literature_search` → 生成 handoff 文件 + waiting_for_user
- [ ] `run deep_reading` → 生成 handoff 文件 + waiting_for_user
- [ ] `run outline` → 生成 handoff 文件 + waiting_for_user
- [ ] `run writing` → 生成 handoff 文件 + waiting_for_user
- [ ] `run polishing` → 生成 handoff 文件 + waiting_for_user
- [ ] `run charts_and_tables` → 生成 handoff 文件 + waiting_for_user
- [ ] `run citation_verification`（干净）→ auto done
- [ ] `run citation_verification`（有问题）→ handoff + waiting_for_user
- [ ] `run research_design` → manual 任务说明
- [ ] `confirm <stage>` → 检查 done_conditions，通过才 done
- [ ] `confirm <stage> --override` → 强制 done + 日志
- [ ] `status` → 正确展示 waiting_for_user / requires_confirmation
- [ ] `resume` → 识别 handoff 阶段并提示

### 质量验收

- [ ] 17 个 contract 全部通过 schema 校验
- [ ] executor_type 分布：4 script + 1 hybrid + 6 skill_handoff + 6 manual
- [ ] 旧有状态机测试全部通过（不破坏 M2）
- [ ] 所有执行器有测试覆盖
- [ ] 6 阶段端到端可跑通
- [ ] 真实 smoke test 通过
- [ ] 总测试数 ≥ 296 + 新增
- [ ] `materials/` 目录在 init 时自动创建
- [ ] `materials/` 不参与 citation validation
- [ ] `materials/templates/reference.docx` 缺失时 formatting 不 blocked
- [ ] skill_handoff prompt 包含 materials 文件清单摘要（不全文塞入）

---

## 附录 D：风险清单

| 风险 | 概率 | 影响 | 缓解 |
|------|:---:|:---:|------|
| commands.py 改造破坏旧状态机 | 中 | 高 | `_execute_stage()` 替换时保留旧的依赖检查逻辑；M7 前不碰 commands.py |
| stage_executor import 现有脚本时出现循环引用 | 低 | 中 | 使用延迟 import 或函数内 import |
| handoff prompt 模板变量不足 | 中 | 中 | 设 fallback prompt；变量缺失 warning 但不崩溃 |
| contract 定义与脚本实际接口不匹配 | 中 | 中 | M3 实现时同步校验，不匹配 → blocked |
| waiting_for_user 状态在旧 schema 中不存在 | 低 | 中 | 在 workflow_state.py 中新增该状态值或复用 in_progress 的子状态 |
| Windows GBK 编码再次出现 | 低 | 低 | 所有 print 用 ASCII，handoff JSON 用 utf-8 |

---

## 附录 E：可回滚点

| 回滚点 | 触发条件 | 回滚动作 |
|--------|----------|----------|
| M0 后 | 基线问题 | `git checkout master` |
| M1 后 | contract 设计问题 | `git reset --hard M1-commit` |
| M2 后 | 框架问题 | `git reset --hard M2-commit` |
| M5 后 | commands.py 接入前 | M7 前最安全的回滚点 |
| M7 后 | 集成问题 | 不回滚，优先修 bug |

---

## 附录 F：v0.2 完成后打 tag 建议

```bash
git tag -a v0.2.0 -m "paper-workflow v0.2.0: Stage Executor Bridge + 6-phase workflow"
```

tag 应在 M8 全部验收通过、合并 master 后创建。

---

## 附录 G：v0.2 完成后进入 v0.3 的判断标准

1. v0.2 全部验收通过（附录 C 全部勾选）
2. 至少 1 个真实论文项目完整跑通 6 阶段
3. 用户确认 executor bridge 稳定
4. 收集至少 5 条 v0.2 gotchas

v0.3 将解锁：revision-log、系统综述纳排流程、Hook 二次校验、LaTeX PDF 编译。
