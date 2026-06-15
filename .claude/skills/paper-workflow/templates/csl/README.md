# CSL 引用格式文件

此目录存放 Citation Style Language (CSL) 文件，供 Pandoc `--citeproc` 使用。

## 获取 CSL 文件

运行以下命令下载官方 CSL 文件：

```bash
# 下载全部
python scripts/fetch_csl.py --all

# 或单独下载
python scripts/fetch_csl.py gb-t-7714
python scripts/fetch_csl.py apa
python scripts/fetch_csl.py chicago
```

## 手动获取

也可以从以下来源手动下载 `.csl` 文件：

- [Zotero Style Repository](https://www.zotero.org/styles)
- [citationstyles.org](https://github.com/citation-style-language/styles)
- 将 `.csl` 文件放入此目录即可

## 需要的文件

| 文件 | 用途 | Profile |
|------|------|---------|
| `gb-t-7714.csl` | GB/T 7714-2015 中文引用格式 | thesis-cn, course-cn |
| `apa.csl` | APA 7th edition | journal-word, journal-latex |
| `chicago.csl` | Chicago Author-Date | 可选 |

## 验证

```bash
# 测试 CSL 文件是否可被 pandoc 解析
pandoc --citeproc --to plain --csl gb-t-7714.csl <<< "test"
```
