# paper-workflow 实现计划

> 日期：2026-06-12 | 基于 spec v1.0 | 状态：已通过（已按审核意见修正）
> 
> 本计划将 spec 的 18 项 MVP 拆解为 7 个里程碑、可独立提交的工程任务。

---

## 环境基线（已确认）

| 项目 | 版本/状态 |
|------|----------|
| Python | 3.12.7 |
| Pandoc | 3.9.0.2 |
| 叶子 skill 链接 | 21 个，全部正常 |
| 仓库地址 | `https://github.com/Shiyisir/paper-workflow` |
| 当前分支 | `master` |

---

# Milestone 0：基线核验与开发约束

> 目标：确保仓库结构正确、环境可用、测试入口能跑通，为后续开发建立安全基线。

## 任务 0.1：仓库结构检查与 .gitignore 补齐

- **目标**：确认仓库结构符合 spec 约定，`.gitignore` 覆盖所有不应提交的文件
- **前置依赖**：无
- **新增/修改文件**：`.gitignore`（修改）
- **核心接口**：无
- **实现步骤**：
  1. 检查 `.claude/skills/paper-workflow/` 目录是否存在，不存在则创建骨架
  2. 检查 `.agents/skills/` 下 21 个符号链接是否可解析
  3. 确认 `.codex/` 和 `.claude/` 目录位置正确
  4. 在 `.gitignore` 中追加（精确规则，避免影响模板和测试 fixture）：
     ```
     # 论文项目运行时产物
     .paper-workflow/
     outputs/
     !outputs/.gitkeep

     # Python 缓存
     __pycache__/
     *.pyc
     .pytest_cache/
     ```
     注意：`templates/docx/*.docx`、`tests/fixtures/**/*.docx` 等模板和测试用文件允许提交，不在忽略范围内
  5. 运行 `git status` 确认无意外文件
- **测试方法**：
  - `git status` 输出干净
- **验收标准**：
  - `.claude/skills/paper-workflow/` 目录存在
  - 21 个符号链接全部可解析
  - `.gitignore` 精确覆盖论文运行时产物和 Python 缓存，模板和测试 fixture 不受影响
- **提交建议**：`chore: verify repo structure and update .gitignore`

## 任务 0.2：Python 依赖声明与环境探测

- **目标**：声明 MVP 所需的 Python 依赖，提供环境探测脚本
- **前置依赖**：0.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/requirements.txt`
  - `.claude/skills/paper-workflow/scripts/check_env.py`
- **核心接口**：
  - `python scripts/check_env.py` → 输出环境报告 JSON
- **实现步骤**：
  1. 编写 `requirements.txt`，声明：`pyyaml`, `jsonschema`, `python-docx`, `lxml`, `bibtexparser`
  2. 编写 `check_env.py`：
     - 探测 Python 版本、依赖可用性
     - 探测 `pandoc` 是否在 PATH，并测试 `pandoc --citeproc` 是否可用（内置过滤器）。独立 `pandoc-citeproc` 只作为旧环境兼容项检测
     - 探测 LaTeX 引擎（`xelatex`/`pdflatex`）
     - 输出 JSON 格式的环境报告
  3. 安装依赖：`pip install -r requirements.txt`
- **测试方法**：
  - `python scripts/check_env.py` 输出有效 JSON，所有探测结果非空
  - `python -c "import yaml, jsonschema, docx"` 无错误
- **验收标准**：
  - `requirements.txt` 包含全部必需依赖
  - `check_env.py` 输出完整的环境报告
  - 所有依赖可导入
- **提交建议**：`feat: add Python dependencies and environment check script`

## 任务 0.3：pytest 最小入口

- **目标**：建立测试基础设施，确保后续每个里程碑都能跑测试
- **前置依赖**：0.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/tests/__init__.py`
  - `.claude/skills/paper-workflow/tests/conftest.py`
  - `.claude/skills/paper-workflow/tests/test_check_env.py`
  - `pytest.ini` 或 `pyproject.toml`（`[tool.pytest]`）
- **核心接口**：
  - `pytest .claude/skills/paper-workflow/tests/ -v`
- **实现步骤**：
  1. 创建 `tests/__init__.py`（空文件）
  2. 编写 `conftest.py`：
     - `tmp_paper_project` fixture：在 tmp_path 下创建最小论文项目目录结构
     - `sample_config` fixture：返回合法的 config.yaml dict
     - `sample_state` fixture：返回合法的 state.yaml dict
  3. 编写 `test_check_env.py`：验证 check_env.py 的输出 schema
  4. 在项目根 `pyproject.toml` 或 `pytest.ini` 配置测试路径
- **测试方法**：
  - `pytest .claude/skills/paper-workflow/tests/ -v` 全部通过
- **验收标准**：
  - 3 个 fixture 可用且可被测试引用
  - `test_check_env.py` 通过
  - 后续里程碑可仅靠新增 test 文件扩展
- **提交建议**：`test: add pytest entry point and base fixtures`

### Milestone 0 验收总结

```
✓ 仓库结构符号链接全部正常
✓ Python 依赖全部可导入
✓ Pandoc / LaTeX 路径已探测
✓ pytest 入口可用
→ 创建开发分支 dev/paper-workflow-mvp
```

> **关于 `outputs/latest/`**：workflow 仓库本体不提交论文运行产物。真实论文项目是否将 `outputs/latest/` 纳入版本管理，由用户项目自行决定。MVP 只提供推荐 `.gitignore` 模板，不强制替用户忽略最新终稿。

---

# Milestone 1：工作流骨架与项目初始化

> 目标：实现 `/paper-workflow init`，完成项目初始化闭环。

## 任务 1.1：SKILL.md 入口路由

- **目标**：编写 SKILL.md，定义触发条件、命令路由、阶段执行器映射
- **前置依赖**：M0 完成
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/SKILL.md`
- **核心接口**：
  - `/paper-workflow init|status|resume|run|qa|render` 命令路由
  - 自然语言路由表（"搜知网…" → cnki-search 等）
- **实现步骤**：
  1. 编写 SKILL.md（约 100 行），包含：
     1. `disable-model-invocation: true`（自然语言不自动加载）
     2. 触发条件：`/paper-workflow` 前缀
     3. 6 个核心命令的入口路由
     4. 单次任务路由表（自然语言 → 叶子 skill）
     5. 阶段标识符枚举
  2. 引用 `references/lifecycle.md` 作为详细阶段说明
  3. 引用 `references/routing-rules.md` 作为状态机规则
- **测试方法**：
  - 在 Claude Code 中输入 `/paper-workflow` 能触发 skill
  - 自然语言"搜知网储能论文"不触发工作流（走单次任务路由）
- **验收标准**：
  - SKILL.md 可被 Claude Code 识别
  - 6 个核心命令全部定义
  - 单次任务路由表覆盖 spec 3.2 全部 8 种场景
  - 文档引用路径正确
- **提交建议**：`feat: add paper-workflow SKILL.md entry point`

## 任务 1.2：references/ 基础文件（规划文档）

- **目标**：创建 9 个 references/ 文档骨架，为后续里程碑提供规范参考
- **前置依赖**：1.1
- **新增/修改文件**（9 个）：
  - `.claude/skills/paper-workflow/references/lifecycle.md`
  - `.claude/skills/paper-workflow/references/routing-rules.md`
  - `.claude/skills/paper-workflow/references/type-matrix.md`
  - `.claude/skills/paper-workflow/references/defaults.md`
  - `.claude/skills/paper-workflow/references/search-profiles.md`
  - `.claude/skills/paper-workflow/references/evidence-schema.md`
  - `.claude/skills/paper-workflow/references/quality-checklist.md`
  - `.claude/skills/paper-workflow/references/pandoc-workflow.md`
  - `.claude/skills/paper-workflow/references/latex-gotchas.md`
- **核心接口**：这些是参考文档，无程序接口
- **实现步骤**：
  1. `lifecycle.md`：17 阶段详细说明（从 spec 附录扩充）
  2. `routing-rules.md`：状态机、跳转、回退规则（从 spec 第 4 节提取）
  3. `type-matrix.md`：paper_type × research_type 矩阵，标注跳过逻辑
  4. `defaults.md`：默认值（字数范围、检索模式、引用格式）
  5. `search-profiles.md`：学科路由表（从 spec 6.2 提取）
  6. `evidence-schema.md`：evidence-matrix.csv 和 claim-citation-map.csv 字段说明
  7. `quality-checklist.md`：每阶段的质量检查项
  8. `pandoc-workflow.md`：渲染流程、命令模板、参数说明
  9. `latex-gotchas.md`：按 profile 分层的避坑规则（从 spec 7.3 提取）
- **测试方法**：
  - 每个文件可被 Markdown 渲染器正常解析
  - 文件间交叉引用路径正确
- **验收标准**：
  - 9 个文件全部创建
  - 内容覆盖 spec 对应章节
  - 文件大小合理（非空，非空洞模板）
- **提交建议**：`docs: add paper-workflow reference documentation`

## 任务 1.3：JSON Schema 定义

- **目标**：定义 3 个核心 JSON Schema，为脚本提供数据校验
- **前置依赖**：1.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/schemas/workflow-state.schema.json`
  - `.claude/skills/paper-workflow/schemas/literature-record.schema.json`
  - `.claude/skills/paper-workflow/schemas/render-profile.schema.json`
- **核心接口**：各脚本通过 `jsonschema.validate(data, schema)` 调用
- **实现步骤**：
  1. `workflow-state.schema.json`：基于 spec 4.1 state.yaml 结构
  2. `literature-record.schema.json`：基于 spec 5.1 catalog.jsonl 结构
  3. `render-profile.schema.json`：基于 spec 7.1 渲染 profile 结构
  4. 每个 schema 支持 `$schema: "http://json-schema.org/draft-07/schema#"`
- **测试方法**：
  - 用 `jsonschema` 库对合法 fixture 验证通过
  - 对非法 fixture 验证失败，错误信息明确
  - 在 `tests/test_schemas.py` 中覆盖
- **验收标准**：
  - 3 个 schema 文件创建，符合 JSON Schema draft-07
  - 合法 fixture 验证通过
  - 至少 3 类非法数据被正确拒绝
- **提交建议**：`feat: add JSON schemas for state, literature, and render profiles`

## 任务 1.4：`/paper-workflow init` — 项目初始化

- **目标**：实现交互式项目初始化，生成 config.yaml + state.yaml + artifact-manifest.jsonl + 项目目录
- **前置依赖**：1.1, 1.2, 1.3（可并行）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/init_project.py`
- **核心接口**：
  - `python scripts/init_project.py <project_dir> [--slug <slug>] [--paper-type <type>] [--language zh|en]`
  - 交互式提问：论文类型、研究类型、学科、语言、目标期刊、检索模式偏好
- **实现步骤**：
  1. 读取命令行参数和交互式输入
  2. 生成 `project_id`（slug）
  3. 根据 `paper_type` + `research_type` 计算自动跳过的阶段（spec 4.3）
  4. 生成 `.paper-workflow/config.yaml`
  5. 生成 `.paper-workflow/state.yaml`（所有阶段 status=pending，仅 requirements 为 in_progress）
  6. 生成 `.paper-workflow/artifact-manifest.jsonl`（空文件）
  7. 创建运行时目录：`manuscript/`、`literature/`、`citations/`、`figures/`、`tables/`、`outputs/latest/`、`outputs/qa/`
  8. 对于已有项目（state.yaml 已存在），只展示当前状态，不覆盖
- **测试方法**：
  - `python scripts/init_project.py /tmp/test-project --slug test-paper --paper-type course_paper --language zh` 成功
  - 生成的 state.yaml 通过 workflow-state.schema.json 校验
  - 生成的 config.yaml 包含所有必要字段
  - 重复运行不覆盖已有文件
  - `tests/test_init_project.py`
- **验收标准**：
  - 可初始化新论文项目，生成全部运行时文件
  - 重复运行幂等（不破坏已有状态）
  - 已有项目可被识别，输出当前状态摘要
- **提交建议**：`feat: implement /paper-workflow init command`

## 任务 1.5：模板 profile 与 CSL 文件准备

- **目标**：准备 4 个渲染 profile、3 个 CSL 文件、3 个 reference.docx 和 1 个 LaTeX 模板骨架
- **前置依赖**：1.3
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/templates/profiles/thesis-cn.yaml`
  - `.claude/skills/paper-workflow/templates/profiles/course-cn.yaml`
  - `.claude/skills/paper-workflow/templates/profiles/journal-word.yaml`
  - `.claude/skills/paper-workflow/templates/profiles/journal-latex.yaml`
  - `.claude/skills/paper-workflow/templates/csl/gb-t-7714.csl`
  - `.claude/skills/paper-workflow/templates/csl/apa.csl`
  - `.claude/skills/paper-workflow/templates/csl/chicago.csl`
  - `.claude/skills/paper-workflow/templates/docx/.gitkeep`（reference.docx 占位，说明需用户提供或脚本生成默认）
  - `.claude/skills/paper-workflow/templates/latex/journal.tex`
- **核心接口**：render.py 读取这些模板
- **实现步骤**：
  1. 创建 4 个 profile YAML（基于 spec 7.1 示例）
  2. 准备 3 个 CSL 文件（从 Zotero CSL 仓库获取，或使用 citationstyles.org 官方文件）
  3. 创建 reference.docx 占位说明
  4. 编写最小 `journal.tex` 模板（可编译通过为标准 LaTeX 文档）
- **测试方法**：
  - profile YAML 通过 render-profile.schema.json 校验
  - CSL 文件可被 pandoc `--citeproc` 内置过滤器或 citeproc-py 解析
  - `journal.tex` 可被 `xelatex` 编译（如果 LaTeX 引擎可用）
- **验收标准**：
  - 4 个 profile 文件内容符合 schema
  - 3 个 CSL 文件为合法 CSL 1.0.1
  - LaTeX 模板可编译
- **提交建议**：`feat: add render profiles, CSL files, and LaTeX template`

### Milestone 1 验收总结

```
✓ SKILL.md 可被识别，命令路由正确
✓ 9 个 references/ 文件就位
✓ 3 个 JSON Schema 通过校验
✓ init 命令可生成完整项目骨架
✓ 4 个 render profile + 3 个 CSL + 1 个 LaTeX 模板就位
```

---

# Milestone 2：状态机与断点恢复

> 目标：实现项目核心基础设施 — workflow_state.py，支持状态管理、依赖检查、断点恢复。

## 任务 2.1：workflow_state.py — 核心状态读写

- **目标**：实现状态文件的初始化、读取、写入、schema 校验
- **前置依赖**：M1 完成
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/workflow_state.py`
- **核心接口**：
  ```python
  def init_state(project_id: str, config: dict) -> dict
  def load_state() -> dict
  def save_state(state: dict) -> None
  def validate_state(state: dict) -> list[str]  # 返回错误列表，空列表表示通过
  ```
- **实现步骤**：
  1. 实现 `init_state()`：根据 paper_type + research_type 标记跳过阶段，返回完整 state dict
  2. 实现 `load_state()`：从 `.paper-workflow/state.yaml` 和 `config.yaml` 读取并合并
  3. 实现 `save_state()`：写回 `.paper-workflow/state.yaml`，原子写入（先写临时文件再 rename）
  4. 实现 `validate_state()`：用 workflow-state.schema.json 校验，返回错误列表
  5. 所有写操作追加到 `artifact-manifest.jsonl`
- **测试方法**：
  - `tests/test_workflow_state.py`
  - 合法 state 校验通过
  - 缺少 required 字段时返回非空错误列表
  - 原子写入：模拟写入中断，原文件未被破坏
- **验收标准**：
  - 初始化 state 正确标记跳过阶段
  - 读取/写入/校验三项功能正确
  - 原子写入保护原文件
- **提交建议**：`feat: implement core workflow state read/write/validate`

## 任务 2.2：workflow_state.py — 状态转换与依赖检查

- **目标**：实现阶段推进、依赖检查、blocked 状态
- **前置依赖**：2.1
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/workflow_state.py`（追加）
- **核心接口**：
  ```python
  def set_stage_status(stage_id: str, status: str, override: bool = False) -> dict
  def get_next_stages() -> list[str]
  def get_blocked_stages() -> list[dict]
  def mark_stage_blocked(stage_id: str, reason: str) -> None
  ```
- **实现步骤**：
  1. `set_stage_status()`：
     - 非 override：检查 `depends_on` 全部 `done` → 设置目标状态；否则 → 设置 `blocked`，记录缺失条件
     - override=True：跳过依赖检查，在 `state.yaml` 的 `overrides` 字段追加时间戳和操作记录
  2. `get_next_stages()`：返回 depends_on 满足且 status=pending 的阶段
  3. `get_blocked_stages()`：返回 status=blocked 的阶段及其 blockers 列表
  4. `mark_stage_blocked()`：记录 blocker 原因到 stage 的 `blockers` 字段
- **测试方法**：
  - `tests/test_workflow_state.py` 追加测试
  - 依赖未满足时推进 → 返回 blocked 状态，原状态不变
  - override 推进 → 依赖未满足也可推进，日志记录 overrides
  - get_next_stages 在依赖全部满足时返回正确列表
- **验收标准**：
  - 依赖未完成时禁止推进非 override 的阶段
  - override 记录日志
  - get_next_stages 返回符合依赖图的阶段列表
- **提交建议**：`feat: implement stage transitions with dependency checking`

## 任务 2.3：`status` / `resume` / `run <stage>` 命令

- **目标**：实现三个用户可见的命令，打通状态机完整交互
- **前置依赖**：2.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/commands.py`（命令分发入口）
- **核心接口**：
  ```bash
  python scripts/commands.py status [--verbose]
  python scripts/commands.py resume
  python scripts/commands.py run <stage> [--override]
  ```
- **实现步骤**：
  1. `status`：读取 state.yaml，输出：
     - 当前阶段 & 状态
     - 已完成阶段列表（含完成时间）
     - 下一可推进阶段
     - 产物列表（从 artifact-manifest.jsonl）
     - `--verbose` 时展示所有阶段详情
  2. `resume`：读取 current_stage → 输出下一步操作提示 → 等待用户确认 → 推进
  3. `run <stage>`：
     - 检查依赖 → 推进 → 调用对应阶段执行器
     - `--override` 传递 override=True 给 set_stage_status
  4. 每个阶段执行器初始为 stub（输出"阶段 X 执行逻辑尚未实现"），后续里程碑填充
- **测试方法**：
  - `tests/test_commands.py`
  - status 输出包含 current_stage 和 next_stages
  - resume 在 in_progress 阶段恢复正常
  - run 未满足依赖的阶段无 --override 时报错
- **验收标准**：
  - status 清晰展示项目进度
  - resume 可恢复中断的会话
  - run <stage> 正确执行依赖检查
  - 关闭终端后重启 Claude Code → resume 正常恢复
- **提交建议**：`feat: implement status, resume, and run commands`

### Milestone 2 验收总结

```
✓ init_state 正确标记跳过阶段
✓ 依赖未满足时禁止推进
✓ override 记录日志
✓ 关闭会话后可恢复进度
✓ 状态文件损坏时给出明确错误
✓ artifact-manifest.jsonl 记录所有产物
```

---

# Milestone 3：文献记录、检索日志与去重

> 目标：建立可靠的文献数据模型，实现去重和版本关联。先建结构，再接搜索。

## 任务 3.1：literature-record schema 与 catalog.jsonl 读写

- **目标**：实现文献记录的 CRUD 基础层
- **前置依赖**：M1（Schema 已定义）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/literature_store.py`
  - `.claude/skills/paper-workflow/scripts/search_logger.py`
- **核心接口**：
  ```python
  # literature_store.py
  def read_catalog() -> list[dict]
  def append_records(records: list[dict]) -> int  # 返回新增条数
  def update_record(canonical_id: str, updates: dict) -> None
  def get_by_doi(doi: str) -> dict | None
  def get_by_citekey(citekey: str) -> dict | None
  
  # search_logger.py
  def log_search(query: str, source: str, count: int, filters: dict) -> None
  def get_search_history() -> list[dict]
  ```
- **实现步骤**：
  1. `literature_store.py`：catalog.jsonl 的原子读写
  2. `search_logger.py`：search-log.jsonl 的追加写入
  3. 每条记录写入时用 literature-record.schema.json 校验
  4. 自动生成 `canonical_id`（ref-0001, ref-0002, ...）
  5. 自动生成 `citekey`（姓+年+关键词，如 `wang2024RockyDesertification`）
- **测试方法**：
  - `tests/test_literature_store.py`
  - 写入 3 条记录 → 读取 3 条
  - 用 DOI 查找 → 返回正确记录
  - 写入不符 schema 的记录 → 抛出 ValidationError
- **验收标准**：
  - catalog.jsonl 读写正确
  - search-log.jsonl 追加写入正确
  - schema 校验生效
  - citekey 生成规则一致
- **提交建议**：`feat: implement literature record store and search logger`

## 任务 3.2：dedup.py — DOI 规范化与精确去重

- **目标**：实现文献去重的核心引擎
- **前置依赖**：3.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/dedup.py`
- **核心接口**：
  ```python
  def normalize_doi(raw: str) -> str | None
  def normalize_title(title: str) -> str
  def deduplicate(records: list[dict]) -> dict
  ```
- **实现步骤**：
  1. `normalize_doi()`：
     - 统一为 `10.xxxx/...` 格式
     - 处理 `https://doi.org/` 前缀
     - 处理 URL 编码（`%2F` → `/`）
     - 大小写转小写
     - 空值/无效 DOI 返回 None
  2. `normalize_title()`：
     - 去标点、多余空格
     - 转小写
     - 英文撇号/引号归一化
  3. `deduplicate()` 去重优先级（spec 5 级匹配）：
     1. DOI 精确匹配
     2. 标准化标题完全一致 + 年份一致
     3. 标题相似度 ≥ 0.85 + 第一作者一致 + 年份差 ≤ 1
     4. 作者组匹配 + 期刊 + 卷期页码一致
     5. 跨语言标题 / arXiv ID 匹配 → 标记 `related_versions`，不删除
  4. 来源合并：同一文献多来源时，合并 `sources` 字段，保留最完整元数据
  5. 返回 `{"unique": [...], "merged": [...], "related": [...], "pending_review": [...]}`
- **测试方法**：
  - `tests/test_dedup.py`
  - 两条 DOI 相同记录 → 去重为 1 条
  - `10.1016/j.ecoser.2024.101650` 和 `https://doi.org/10.1016/j.ecoser.2024.101650` → 匹配
  - arXiv 预印本 + 正式发表版 → related_versions 关联，两条都保留
  - 跨语言疑似重复 → pending_review
- **验收标准**：
  - 同一 DOI 不重复保存
  - 不同格式 DOI 正确归一化
  - 预印本不被误删
  - 跨语言疑似重复进入 pending_review
- **提交建议**：`feat: implement deduplication engine with DOI normalization`

## 任务 3.3：dedup.py — 去重报告生成

- **目标**：生成人类可读的 `dedup-report.md`
- **前置依赖**：3.2
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/dedup.py`（追加）
- **核心接口**：
  ```python
  def generate_dedup_report(result: dict, output_path: str) -> str
  ```
- **实现步骤**：
  1. 遍历 `result["merged"]`：列出合并来源
  2. 遍历 `result["related"]`：列出关联版本（预印本 ↔ 正式发表）
  3. 遍历 `result["pending_review"]`：列出需人工判定的疑似重复，附理由
  4. 输出统计摘要：原始条数、去重后、合并数、关联数、待审核数
  5. 写入 `dedup-report.md`
- **测试方法**：
  - `tests/test_dedup.py` 追加测试
  - 生成的 report 包含统计摘要、合并列表、待审核列表
- **验收标准**：
  - 报告格式清晰，统计数字与 dedup 结果一致
  - pending_review 项有明确的审核理由
- **提交建议**：`feat: generate human-readable dedup report`

### Milestone 3 验收总结

```
✓ 文献 CRUD 层（catalog.jsonl）可读写
✓ search-log.jsonl 记录每次检索
✓ DOI 五种格式归一化
✓ 5 级去重优先级正确
✓ 预印本不被误删
✓ dedup-report.md 可读
```

---

# Milestone 4：证据矩阵与引文核验

> 目标：建立论点-引文-文献的完整证据链，实现双向核验。

## 任务 4.1：证据矩阵与论点引文映射初始化

- **目标**：创建 evidence-matrix.csv 和 claim-citation-map.csv 的读写层
- **前置依赖**：M3（文献去重后才有可靠 citekey）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/evidence_manager.py`
- **核心接口**：
  ```python
  def init_evidence_matrix() -> str  # 返回文件路径
  def add_evidence_entry(entry: dict) -> None
  def get_evidence_for_section(section: str) -> list[dict]
  def init_claim_map() -> str
  def add_claim(claim: dict) -> str  # 返回 claim_id (C001, ...)
  def get_claims_by_section(section: str) -> list[dict]
  def get_claims_by_citekey(citekey: str) -> list[dict]
  ```
- **实现步骤**：
  1. `evidence-matrix.csv`：按 spec 5.2 字段创建，CSV 读写
  2. `claim-citation-map.csv`：按 spec 5.3 字段创建，自动编号 C001+
  3. 实现 CSV 原子写入
  4. 索引：`get_evidence_for_section` 支持章节过滤
- **测试方法**：
  - `tests/test_evidence_manager.py`
  - 创建 evidence-matrix.csv → 写入 2 条 → 读取过滤
  - claim-citation-map 自动编号连续
- **验收标准**：
  - CSV 读写正确，字段完整
  - claim_id 自动递增不重复
  - 章节过滤正确
- **提交建议**：`feat: implement evidence matrix and claim-citation map`

## 任务 4.2：引用库生成（references.bib + references.csl.json）

- **目标**：从 catalog.jsonl 生成 BibTeX 和 CSL JSON 引用库，citekey 保持一致
- **前置依赖**：4.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/export_references.py`
- **核心接口**：
  ```python
  def export_bib(catalog: list[dict], output_path: str) -> int  # 返回导出条数
  def export_csl_json(catalog: list[dict], output_path: str) -> int
  def sync_citekeys(bib_path: str, csl_path: str) -> bool  # 确保两边 citekey 一致
  ```
- **实现步骤**：
  1. `export_bib()`：BibTeX 条目，类型映射（article/inproceedings/book/...）
  2. `export_csl_json()`：CSL JSON 格式
  3. `sync_citekeys()`：验证两边 citekey 完全一致
  4. citekey 稳定性规则：同一文献修改元数据后 citekey 不变（以 canonical_id 为准）
- **测试方法**：
  - `tests/test_export_references.py`
  - 3 条文献 → 导出 .bib 和 .csl.json → citekey 一致
  - citekey 与 catalog.jsonl 一致
- **验收标准**：
  - .bib 和 .csl.json 格式正确
  - citekey 与 catalog 一致
  - sync_citekeys 检测不一致
- **提交建议**：`feat: implement reference export (bib + csl-json)`

## 任务 4.3：validate_citations.py — 引文一致性校验

- **目标**：检查正文引用与文献库的一致性
- **前置依赖**：4.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/validate_citations.py`
- **核心接口**：
  ```python
  def check_citekey_consistency(manuscript_path: str, bib_path: str) -> dict
  def check_duplicate_citekeys(bib_path: str) -> list
  def cross_check_citations(manuscript_path: str, claim_map_path: str) -> dict
  ```
- **实现步骤**：
  1. `check_citekey_consistency()`：
     - 正则提取正文中 `[@citekey]` 引用
     - 对比 .bib 中的 citekey 集合
     - 返回：孤立引用（正文有、bib 无）、未使用引用（bib 有、正文无）
  2. `check_duplicate_citekeys()`：检测 .bib 中重复 citekey
  3. `cross_check_citations()`：正文引用 ↔ claim-citation-map.csv 交叉校验
  4. 检测 `[CITE NEEDED]` 残留，输出章节位置
- **测试方法**：
  - `tests/test_validate_citations.py`
  - 正文引用 bib 中没有 → 报孤立引用
  - 正文有 [CITE NEEDED] → 检测到并报告
  - 重复 citekey → 检测到
- **验收标准**：
  - 孤立引用能检测
  - [CITE NEEDED] 残留能检测
  - 重复 citekey 能检测
  - 输出明确的错误位置和修复建议
- **提交建议**：`feat: implement citation consistency validation`

## 任务 4.4：validate_catalog.py — 文献库质量校验

- **目标**：检查 catalog.jsonl 的数据质量
- **前置依赖**：4.3
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/validate_catalog.py`
- **核心接口**：
  ```python
  def validate_catalog() -> dict
  ```
- **实现步骤**：
  1. 检查每条的 schema 合规性
  2. 检查 canonical_id 唯一性
  3. 检查 citekey 唯一性
  4. 检查 DOI 格式合法性
  5. 标记缺失必填字段的记录
  6. 检查 references.bib 和 references.csl.json 是否与 catalog.jsonl 同步
  7. 返回错误和警告列表
- **测试方法**：
  - `tests/test_validate_catalog.py`
  - 重复 canonical_id → 报错
  - 缺失 DOI → 警告（非报错）
  - 格式错误 DOI → 警告
- **验收标准**：
  - 重复 ID / citekey 可检测
  - 缺失必填字段可检测
  - 错误与警告分级清晰
- **提交建议**：`feat: implement catalog quality validation`

### Milestone 4 验收总结

```
✓ evidence-matrix.csv + claim-citation-map.csv 可读写
✓ references.bib + references.csl.json 与 catalog 同步
✓ 正文引用 ↔ 文献库双向核验
✓ 孤立引用、[CITE NEEDED]、重复 citekey 可检测
✓ catalog 质量报告可生成
```

---

# Milestone 5：三轨渲染与 Word 后处理

> 目标：实现 Markdown → docx/tex/md 三条输出轨道，含 Word 后处理。

## 任务 5.1：validate_manuscript.py — 源稿校验

- **目标**：在渲染前检查 Markdown 源稿的结构和质量
- **前置依赖**：无（独立）
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/validate_manuscript.py`
- **核心接口**（spec 8.3）：
  ```python
  def validate_structure(md_path: str) -> dict
  def validate_formulas(md_path: str) -> dict
  def validate_attachments(md_path: str, figures_dir: str) -> dict
  ```
- **实现步骤**：
  1. `validate_structure()`：
     - 标题层级连续性（无跳跃）
     - 图表编号连续性（图1→图2→图3 无间隔）
     - [CITE NEEDED] 残留检测
  2. `validate_formulas()`：
     - `\tag{}` 违规（需提示 docx profile 下禁用）
     - Unicode 下标检测（Arial 缺字问题）
     - 公式括号匹配（`$$` 和 `$` 配对）
  3. `validate_attachments()`：
     - 扫描 `![]()` 引用，检查对应图片文件是否存在
     - 检查图片格式（SVG → 提示需转换）
- **测试方法**：
  - `tests/test_validate_manuscript.py`
  - 用 `tests/fixtures/formulas.md` 测试公式校验
  - 用 `tests/fixtures/citations.md` 测试 [CITE NEEDED] 检测
  - 用 `tests/fixtures/figures.md` 测试图片引用检测
- **验收标准**：
  - 标题跳跃可检测
  - 图表编号间隔可检测
  - [CITE NEEDED] 位置精确报告
  - 缺失图片精确报告路径
- **提交建议**：`feat: implement manuscript source validation`

## 任务 5.2：render.py — 渲染引擎核心

- **目标**：实现统一渲染入口，调用 Pandoc + citeproc 完成格式转换
- **前置依赖**：5.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/render.py`
- **核心接口**（spec 8.7）：
  ```python
  def render(profile: str, input_md: str, output_path: str, dry_run: bool = False) -> dict
  ```
- **实现步骤**：
  1. `--dry-run`：输出即将执行的全部操作，不生成文件
  2. 渲染链：
     1. `validate_manuscript.py` 校验源稿
     2. 加载 profile YAML → 构建 pandoc 参数
     3. 调用 `pandoc` + `--citeproc` + `--csl` + `--reference-doc`（docx）/ `--template`（tex）
     4. SVG 文件检测与转换（SVG → PNG/PDF，根据 profile）
     5. docx profile → 调用 `postprocess_docx.py`
     6. 调用 `validate_docx.py` 或 `validate_tex.py`
     7. 版本号自增：扫描 outputs/ 目录，`v001 → v002 → v003` ...
     8. 仅 QA 通过后复制到 `outputs/latest/`
  3. 错误处理：pandoc 返回非零 → 渲染失败，不继续进行后处理
- **测试方法**：
  - `tests/test_render.py`
  - `render markdown-draft --dry-run` → 输出操作列表，无文件生成
  - `render markdown-draft` → 生成 .md 文件
  - `render thesis-cn` → 生成 .docx 文件
  - 重复渲染 → 版本号递增
- **验收标准**：
  - Markdown 可成功输出 docx、tex 和 md
  - `--dry-run` 正确预览操作
  - 版本号自增
  - 只有 QA 通过才复制到 latest
- **提交建议**：`feat: implement render engine with pandoc pipeline`

## 任务 5.3：SVG 转换处理

- **目标**：处理 SVG 图片到 PNG/PDF 的转换
- **前置依赖**：5.2
- **修改文件**：
  - `.claude/skills/paper-workflow/scripts/render.py`（追加 SVG 转换逻辑）
- **核心接口**：
  ```python
  def convert_svg(profile: dict, manuscript_path: str, figures_dir: str) -> list[str]
  ```
- **实现步骤**：
  1. 扫描 Markdown 中 `![](*.svg)` 引用
  2. 根据 profile 的 `convert_svg_to` 决定目标格式（png / pdf）
  3. 使用 `cairosvg` 或 `rsvg-convert` 转换
  4. 替换 Markdown 中的图片引用（或输出转换后的路径映射）
  5. 无 SVG 图片时静默跳过
  6. 转换工具不可用时给出明确警告而非静默失败
- **测试方法**：
  - `tests/test_render.py` 追加 SVG 测试
  - fixture 包含 SVG 图片引用
  - 转换后文件存在且格式正确
  - 无 SVG 时不产生副作用
- **验收标准**：
  - SVG 正确转换为 PNG/PDF
  - 缺失转换工具时警告用户
  - 无 SVG 时不影响渲染流程
- **提交建议**：`feat: add SVG-to-PNG/PDF conversion in render pipeline`

## 任务 5.4：postprocess_docx.py — Word 后处理

- **目标**：对 pandoc 生成的 docx 进行幂等后处理
- **前置依赖**：5.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/postprocess_docx.py`
- **核心接口**：
  ```python
  def postprocess(input_path: str, output_path: str, profile: dict) -> dict
  ```
- **实现步骤**：
  1. 幂等性保证（旁车文件方案）：
     - 对输入 docx 计算 hash（SHA-256） + profile hash + postprocess 版本号
     - 旁车文件路径：`outputs/qa/<docx-name>.postprocess.json`
     - 记录上次处理的输入 hash 和处理时间
     - hash 未变化时直接跳过，返回 `{"skipped": true, "reason": "already postprocessed"}`
     - 该 JSON 文件不依赖 docx 内部 XML 结构，实现更简单可靠
  2. 处理 pandoc 已知 bug：
     - MS Gothic → 宋体（中文 Win 平台）
     - 三线表边框样式规范化
  3. 图表自动编号：检测 "图1"、"表1" 等模式，确保唯一
  4. 页边距：从 reference.docx 继承，脚本不硬编码
  5. 输出处理报告（哪些操作执行了，哪些因已处理跳过）
- **测试方法**：
  - `tests/test_postprocess_docx.py`
  - 重复运行 2 次 → 第 2 次无变化
  - 生成的 docx 可在 Word 中正常打开
- **验收标准**：
  - 幂等：重复运行不叠加边框、不重复编号
  - 已处理标记正确读写
  - 输出文档在 Word 中正常显示
- **提交建议**：`feat: implement idempotent docx post-processing`

## 任务 5.5：validate_docx.py + validate_tex.py

- **目标**：实现输出文件的自动校验
- **前置依赖**：5.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/validate_docx.py`
  - `.claude/skills/paper-workflow/scripts/validate_tex.py`
- **核心接口**：
  ```python
  # validate_docx.py
  def validate_docx(docx_path: str) -> dict
  
  # validate_tex.py
  def validate_tex(tex_path: str) -> dict
  ```
- **实现步骤**：
  1. `validate_docx.py`：
     - 文件可打开（python-docx）
     - 标题样式（Heading 1/2/3）存在且连贯
     - 公式为 OMML 对象（非图片粘贴）
     - 图表编号检测
     - 表格有边框
  2. `validate_tex.py`：
     - `\documentclass` 引用存在
     - `\begin{document}` / `\end{document}` 配对
     - 引用文件路径（图片、bib）存在
     - 常见编译风险：`\ref{}` 引用无 label、`\cite{}` 无 bib 条目
- **测试方法**：
  - `tests/test_validate_docx.py`
  - `tests/test_validate_tex.py`
  - 合法 docx 通过校验
  - 损坏 docx（无标题样式、公式丢失）被检测
  - 合法 tex 通过校验
  - 缺失图片引用被检测
- **验收标准**：
  - docx 可打开性检查、样式检查、公式检查
  - tex 模板引用、图片路径、引用库检查
  - 损坏文件给出明确错误信息
- **提交建议**：`feat: implement docx and tex output validation`

### Milestone 5 验收总结

```
✓ validate_manuscript 检查源稿结构、公式、图片
✓ render.py 三轨渲染（docx/tex/md）
✓ --dry-run 预览操作
✓ SVG 转换
✓ postprocess_docx 幂等
✓ validate_docx / validate_tex 检查输出
✓ 版本化输出 + latest/ 机制
```

---

# Milestone 6：质量核验与回归测试

> 目标：建立完整的测试体系和 QA 报告生成。

## 任务 6.1：测试 fixtures 创建

- **目标**：创建覆盖所有渲染路径的测试 fixture
- **前置依赖**：M5 完成
- **新增/修改文件**（5 个 fixture + 参考输出）：
  - `.claude/skills/paper-workflow/tests/fixtures/formulas.md`
  - `.claude/skills/paper-workflow/tests/fixtures/tables.md`
  - `.claude/skills/paper-workflow/tests/fixtures/figures.md`
  - `.claude/skills/paper-workflow/tests/fixtures/citations.md`
  - `.claude/skills/paper-workflow/tests/fixtures/chinese-headings.md`
  - `.claude/skills/paper-workflow/tests/fixtures/mini-paper/`（最小完整论文项目）
- **核心接口**：被各 test_*.py 引用
- **实现步骤**：
  1. `formulas.md`：含 `$$...$$` 块、`$...$` 行内、`\tag{}`（正例和反例）、Unicode 下标
  2. `tables.md`：三线表、复杂合并表、中文表头
  3. `figures.md`：`![]()` 引用（存在的和缺失的）、SVG 图片引用
  4. `citations.md`：`[@citekey]` 引用、`[CITE NEEDED]` 占位符、孤立引用
  5. `chinese-headings.md`：`#` 一级到 `######` 六级、编号/非编号混合、跳跃
  6. `mini-paper/`：一个完整的最小论文项目（中国知网引用风格、3 条参考文献、2 个图、1 个表）
- **测试方法**：
  - 每个 fixture 文件格式正确
  - mini-paper 可被 `init` → `render` 完整跑通
- **验收标准**：
  - 5 个 fixture 文件覆盖所有场景
  - mini-paper 是一个完整可渲染的论文项目
- **提交建议**：`test: add test fixtures for all validation paths`

## 任务 6.2：QA 报告生成

- **目标**：整合所有校验结果，生成统一的 QA 报告
- **前置依赖**：6.1
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/scripts/qa_report.py`
- **核心接口**：
  ```python
  def run_all_checks(project_dir: str) -> dict
  def generate_qa_report(results: dict, output_path: str) -> str
  ```
- **实现步骤**：
  1. `run_all_checks()`：依次调用 validate_manuscript → validate_citations → validate_catalog → validate_docx/tex
  2. 聚合结果：通过 / 失败 / 警告（带原因）
  3. 生成 Markdown 格式 QA 报告：
     - 摘要（通过率）
     - 详细错误列表（位置、严重程度、修复建议）
     - 警告列表
  4. 报告输出到 `outputs/qa/`
- **测试方法**：
  - `tests/test_qa_report.py`
  - 干净 fixture → QA 全部通过
  - 含错误的 fixture → QA 报告正确分类错误
- **验收标准**：
  - QA 报告格式清晰
  - 错误分类正确（error vs warning）
  - 与各独立校验脚本结果一致
- **提交建议**：`feat: implement unified QA report generation`

## 任务 6.3：完整回归测试

- **目标**：确保所有测试通过，render 失败时正确返回非零状态码
- **前置依赖**：6.2
- **新增/修改文件**：
  - `.claude/skills/paper-workflow/tests/test_render.py`（扩充）
  - `.claude/skills/paper-workflow/tests/test_integration.py`（新增）
- **核心接口**：
  - `pytest .claude/skills/paper-workflow/tests/ -v --tb=short`
- **实现步骤**：
  1. 扩充 `test_render.py`：三种 profile 的渲染测试
  2. 新增 `test_integration.py`：mini-paper 完整流程（init → dedup → evidence → render → validate）
  3. 验证 render 非零状态码（模拟源稿损坏）
  4. 验证 postprocess_docx 幂等
  5. 验证版本号递增
- **测试方法**：
  ```bash
  pytest .claude/skills/paper-workflow/tests/ -v
  ```
- **验收标准**：
  - 所有 fixture 测试通过
  - 集成测试通过
  - render 失败返回非零状态码
  - 幂等性测试通过
- **提交建议**：`test: complete regression test suite`

### Milestone 6 验收总结

```
✓ 5 个 fixture 文件覆盖公式、表格、图片、引用、中文标题
✓ mini-paper fixture 完整可渲染
✓ QA 报告整合所有校验结果
✓ 回归测试全部通过
✓ render 失败返回非零
```

---

# Milestone 7：端到端验收与文档更新

> 目标：用最小论文项目完整跑通全流程，更新 README 和 docs。

## 任务 7.1：端到端流程测试

- **目标**：从 init 到 render 完整跑通
- **前置依赖**：M6 完成
- **新增/修改文件**：无新增（使用已有 fixture 和脚本）
- **核心接口**：
  ```bash
  # 完整流程
  python scripts/init_project.py /tmp/e2e-test --slug e2e-test --paper-type course_paper --language zh
  # 手动添加 3 条文献到 catalog.jsonl
  python scripts/dedup.py --catalog /tmp/e2e-test/literature/catalog.jsonl
  # 构建证据矩阵
  # render
  python scripts/render.py thesis-cn manuscript/main.md /tmp/e2e-test/outputs/
  # QA
  python scripts/qa_report.py /tmp/e2e-test
  ```
- **实现步骤**：
  1. 初始化项目
  2. 导入 3 条模拟文献（含 1 条重复、1 条预印本关联）
  3. 运行 dedup
  4. 构建 evidence-matrix.csv + claim-citation-map.csv
  5. 编写最小 main.md（含引用、公式、表格、图片）
  6. render thesis-cn
  7. render journal-latex
  8. QA
  9. 模拟中断恢复：删除 state.yaml 中的 in_progress → resume
- **测试方法**：
  - 完整流程无错误
  - 中断恢复正常
  - 输出文件存在且可打开
- **验收标准**：
  - 完整流程可重复运行
  - 中断后可恢复
  - 输出文件有版本记录
  - QA 报告与输出文件一致
- **提交建议**：`test: end-to-end workflow validation`

## 任务 7.2：README 与文档更新

- **目标**：更新项目 README，提供最小使用示例
- **前置依赖**：7.1
- **新增/修改文件**：
  - `README.md`（修改）
  - `.claude/skills/paper-workflow/README.md`（新增，skill 使用说明）
- **核心接口**：人类阅读
- **实现步骤**：
  1. 项目 `README.md`：添加 `/paper-workflow` 常用命令速查
  2. skill `README.md`：
     - 最小使用示例（从 init 到 render）
     - 命令速查表
     - 叶子 skill 列表
     - 常见问题
  3. 更新 `docs/setup.md`：环境配置说明
- **测试方法**：
  - 按 README 中的示例操作，可跑通
- **验收标准**：
  - README 中有最小使用示例
  - 新用户按示例操作可跑通
- **提交建议**：`docs: add usage guide and getting started`

## 任务 7.3：MVP 发布检查清单

- **目标**：生成 MVP 完成度检查清单，确认所有功能达标
- **前置依赖**：7.1
- **新增/修改文件**：
  - `docs/design/2026-06-12-mvp-checklist.md`
- **核心接口**：人工逐项核验
- **实现步骤**：
  1. 列出 18 项 MVP 的完成状态
  2. 列出 7 个里程碑的验收结果
  3. 列出 6 个可用命令的测试结果
  4. 列出 3 种输出格式的测试结果
  5. 列出已知限制
- **测试方法**：
  - 人工逐项勾选
- **验收标准**：
  - 18 项全部勾选或标记为已知限制
- **提交建议**：`docs: add MVP release checklist`

### Milestone 7 验收总结

```
✓ 端到端流程无错误
✓ 中断恢复正常
✓ README 含最小使用示例
✓ MVP 检查清单完成
✓ → 合并 dev/paper-workflow-mvp → master
```

---

# 附录 A：任务依赖图

```
M0（基线）
├── 0.1 仓库结构检查 ──────────────────────────────────────────────────┐
├── 0.2 Python 依赖 + check_env ──────────────────────────────────────┤
└── 0.3 pytest 最小入口 ──────────────────────────────────────────────┤
                                                                       │
M1（工作流骨架）                                                        │
├── 1.1 SKILL.md ──────────────────────────────────────────────────┐   │
├── 1.2 references/ 基础文件 ──────────────────────────────────────┤   │
├── 1.3 JSON Schema 定义 ──────────────────────────────────────────┤   │
├── 1.4 /init 项目初始化 ──→ 依赖 1.1, 1.2, 1.3 ───────────────────┤   │
└── 1.5 模板 profile + CSL ──→ 依赖 1.3 ───────────────────────────┤   │
                                                                   │   │
M2（状态机）                                                        │   │
├── 2.1 workflow_state.py 核心 ──→ 依赖 M1 ────────────────────────┤   │
├── 2.2 状态转换 + 依赖检查 ──→ 依赖 2.1 ──────────────────────────┤   │
└── 2.3 status/resume/run ──→ 依赖 2.2 ────────────────────────────┤   │
                                                                   │   │
M3（文献记录与去重）                                                 │   │
├── 3.1 literature_store.py ──→ 依赖 M1（Schema） ─────────────────┤   │
├── 3.2 dedup.py 核心 ──→ 依赖 3.1 ───────────────────────────────┤   │
└── 3.3 dedup 报告 ──→ 依赖 3.2 ──────────────────────────────────┤   │
                                                                   │   │
M4（证据矩阵与引文核验）                                             │   │
├── 4.1 evidence_manager.py ──→ 依赖 M3 ───────────────────────────┤   │
├── 4.2 export_references.py ──→ 依赖 4.1 ─────────────────────────┤   │
├── 4.3 validate_citations.py ──→ 依赖 4.2 ────────────────────────┤   │
└── 4.4 validate_catalog.py ──→ 依赖 4.3 ─────────────────────────┤   │
                                                                   │   │
M5（渲染与后处理）                                                   │   │
├── 5.1 validate_manuscript.py ──→ 独立 ───────────────────────────┤   │
├── 5.2 render.py ──→ 依赖 5.1 ───────────────────────────────────┤   │
├── 5.3 SVG 转换 ──→ 依赖 5.2 ─────────────────────────────────────┤   │
├── 5.4 postprocess_docx.py ──→ 依赖 5.2 ──────────────────────────┤   │
└── 5.5 validate_docx.py + validate_tex.py ──→ 依赖 5.2 ───────────┤   │
                                                                   │   │
M6（QA 与测试）                                                      │   │
├── 6.1 fixtures ──→ 依赖 M5 ─────────────────────────────────────┤   │
├── 6.2 QA 报告 ──→ 依赖 6.1 ─────────────────────────────────────┤   │
└── 6.3 回归测试 ──→ 依赖 6.2 ─────────────────────────────────────┤   │
                                                                   │   │
M7（验收与文档）                                                      │   │
├── 7.1 端到端测试 ──→ 依赖 M6 ─────────────────────────────────────┤   │
├── 7.2 README 更新 ──→ 依赖 7.1 ──────────────────────────────────┤   │
└── 7.3 MVP 检查清单 ──→ 依赖 7.1 ──────────────────────────────────┘   │
```

### 并行化说明

| 可并行的任务组 | 条件 |
|---------------|------|
| 1.2 + 1.3 | 与 1.1 同时进行 |
| 5.1 + 3.1 + 3.2 | validate_manuscript.py 独立于文献层 |
| 5.4 + 5.5 | 基于 5.2，互不依赖 |
| 5.1 + 5.5 + 3.1 | 源稿校验、输出校验、文献存储互不依赖 |
| 6.1 + 5.3 | 独立任务 |
| 7.2 + 7.3 | 基于 7.1，互不依赖 |

> **注意**：M5 的 `validate_manuscript.py`、`postprocess_docx.py`、`validate_docx.py`、`validate_tex.py` 可与 M3/M4 并行开发。但 `render.py` 的 citeproc 集成测试依赖 M4 生成的 `references.bib` / `references.csl.json`，需等 M4 完成后再验证完整的端到端渲染。

---

# 附录 B：建议的 Git 提交顺序

```
 1  chore: verify repo structure and update .gitignore            [0.1]
 2  feat: add Python dependencies and environment check script     [0.2]
 3  test: add pytest entry point and base fixtures                [0.3]
    → M0 完成，创建分支 dev/paper-workflow-mvp
 4  feat: add paper-workflow SKILL.md entry point                  [1.1]
 5  docs: add paper-workflow reference documentation               [1.2]
 6  feat: add JSON schemas for state, literature, and render       [1.3]
 7  feat: implement /paper-workflow init command                   [1.4]
 8  feat: add render profiles, CSL files, and LaTeX template       [1.5]
    → M1 完成
 9  feat: implement core workflow state read/write/validate        [2.1]
10  feat: implement stage transitions with dependency checking     [2.2]
11  feat: implement status, resume, and run commands               [2.3]
    → M2 完成
12  feat: implement literature record store and search logger      [3.1]
13  feat: implement deduplication engine with DOI normalization    [3.2]
14  feat: generate human-readable dedup report                     [3.3]
    → M3 完成
15  feat: implement evidence matrix and claim-citation map         [4.1]
16  feat: implement reference export (bib + csl-json)              [4.2]
17  feat: implement citation consistency validation                [4.3]
18  feat: implement catalog quality validation                     [4.4]
    → M4 完成
19  feat: implement manuscript source validation                   [5.1]
20  feat: implement render engine with pandoc pipeline             [5.2]
21  feat: add SVG-to-PNG/PDF conversion in render pipeline         [5.3]
22  feat: implement idempotent docx post-processing                [5.4]
23  feat: implement docx and tex output validation                 [5.5]
    → M5 完成
24  test: add test fixtures for all validation paths               [6.1]
25  feat: implement unified QA report generation                   [6.2]
26  test: complete regression test suite                           [6.3]
    → M6 完成
27  test: end-to-end workflow validation                           [7.1]
28  docs: add usage guide and getting started                      [7.2]
29  docs: add MVP release checklist                                [7.3]
    → M7 完成 → 合并到 master
```

---

# 附录 C：MVP 验收清单

## 功能验收

- [ ] `/paper-workflow init`：可初始化新项目
- [ ] `/paper-workflow status`：展示阶段、产物、下一建议
- [ ] `/paper-workflow resume`：从 state.yaml 恢复
- [ ] `/paper-workflow run <stage>`：推进阶段（含依赖检查）
- [ ] `/paper-workflow run <stage> --override`：跳过依赖
- [ ] `/paper-workflow qa`：运行质量核验
- [ ] `/paper-workflow render thesis-cn`：输出 Word 文档
- [ ] `/paper-workflow render journal-latex`：输出 LaTeX
- [ ] `/paper-workflow render markdown-draft`：输出 Markdown
- [ ] `render --dry-run`：预览操作不生成文件

## 数据验收

- [ ] catalog.jsonl 支持 CRUD
- [ ] search-log.jsonl 记录检索历史
- [ ] dedup.py 去重（DOI + 标题 + 作者 + 版本关联）
- [ ] dedup-report.md 可读
- [ ] evidence-matrix.csv 可编辑
- [ ] claim-citation-map.csv 可编辑
- [ ] references.bib 与 catalog 同步
- [ ] references.csl.json 与 catalog 同步

## 校验验收

- [ ] validate_manuscript.py：结构、公式、图片、[CITE NEEDED]
- [ ] validate_citations.py：citekey 一致性、重复、交叉校验
- [ ] validate_catalog.py：ID 唯一、必填字段、与 bib 同步
- [ ] validate_docx.py：可打开、样式、公式、图表编号
- [ ] validate_tex.py：模板、图片路径、bib 引用

## 质量验收

- [ ] postprocess_docx.py 幂等
- [ ] 版本号自增
- [ ] QA 报告整合所有校验
- [ ] 状态文件损坏时给出明确错误
- [ ] render 失败返回非零
- [ ] 所有测试通过

---

# 附录 D：风险清单

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:---:|:---:|----------|
| Python-docx OMML 公式处理不充分 | 中 | 高 | 优先从 reference.docx 继承样式，脚本只修已知 bug |
| Pandoc 版本差异导致参数不兼容 | 低 | 中 | check_env.py 探测版本，render.py 做版本适配 |
| LaTeX 引擎未安装导致 tex profile 不可用 | 中 | 中 | check_env.py 探测；缺失时只用 docx/md profile |
| CSL 文件格式不兼容 citeproc | 低 | 中 | 用 Zotero CSL 仓库官方文件 |
| Windows 路径/编码问题 | 中 | 中 | 统一 UTF-8，路径用 pathlib，原子写用 rename |
| postprocess_docx 幂等标记被 Word 覆盖 | 中 | 低 | 采用旁车文件方案（`outputs/qa/<docx-name>.postprocess.json`），不依赖 docx 内部 XML |
| SVG 转换工具不可用 | 中 | 低 | check_env.py 探测；缺失时警告跳过 |
| 状态文件并发写入冲突 | 低 | 低 | 原子写入（临时文件 + rename） |

---

# 附录 E：可回滚点

每个里程碑完成后提交一次。如果后续里程碑出现问题，可回滚到：

| 回滚点 | 触发条件 | 回滚动作 |
|--------|----------|----------|
| M0 后 | 环境配置问题 | `git reset --hard M0-commit` |
| M1 后 | 初始化逻辑问题 | `git reset --hard M1-commit` |
| M2 后 | 状态机逻辑问题 | `git reset --hard M2-commit` |
| M3 后 | 去重逻辑问题 | `git reset --hard M3-commit` |
| M4 后 | 引文核验问题 | `git reset --hard M4-commit` |
| M5 后 | 渲染问题 | `git reset --hard M5-commit` |

回滚原则：不回滚到已合并 milestone 之前（每个 milestone 独立可验证）。

---

# 附录 F：MVP 完成后进入增强版的判断标准

满足以下条件后，可进入增强版（v2）开发：

1. **全部 18 项 MVP 验收通过**（附录 C 全部勾选）
2. **至少 1 篇真实论文项目完整跑通**（非 fixture，真实写作场景）
3. **用户确认 MVP 功能稳定**（至少使用 2 周无阻塞性 bug）
4. **已知限制已记录**（非阻塞性）

增强版将解锁：
- `systematic` 检索模式（系统综述完整流程）
- `revision-log.jsonl` + `/paper-workflow revise`（投稿返修）
- 多 Subagent 并行阅读
- Hook 二次校验
- 更多学校/期刊模板
- 批量 PDF 下载
- 完整数据分析适配器
