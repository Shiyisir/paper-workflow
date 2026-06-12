# CNKI 导出 API 参考

## API 端点

| 参数 | 值 | 来源 |
|------|----|------|
| API URL | `https://kns.cnki.net/dm8/API/GetExport` | 固定，可从任何页面调用 |
| filename | 加密 ID | 详情页: `#export-id`；结果页: `input.cbItem` value |
| displaymode | `GBTREFER,elearning,EndNote` | 逗号分隔的导出格式 |
| uniplatform | `NZKPT` | 必填 |

## 注册的 displaymode 值

| mode | 输出格式 |
|------|----------|
| `GBTREFER` | GB/T 7714 引用文本 |
| `elearning` | 结构化元数据（用于 Zotero 导入） |
| `EndNote` | EndNote 格式（含 ISSN `%@` 字段） |

## Zotero Local API

```
POST http://127.0.0.1:23119/connector/saveItems
Content-Type: application/json
X-Zotero-Connector-API-Version: 3
```

- **201** = 创建成功
- **500** = 错误
- **0**（Python 返回）= Zotero 未运行

论文保存到 Zotero 当前选中的合集。

查询合集列表：
```bash
python "scripts/push_to_zotero.py" --list
```

## 模式选择

| 场景 | 模式 | Tool call 数 |
|------|------|-------------|
| 在论文详情页 | 单篇导出 | 1 evaluate + 1 bash = 2 |
| 在搜索结果页，全部/部分导出 | **批量导出（推荐）** | 1 evaluate + 1 bash = 2 |
| 需搜索后导出 | 先 cnki-search，再批量导出 | 4 总计 |

**始终优先批量导出**：9 篇论文批量导出节省约 90% tool call（33 → 3）。
