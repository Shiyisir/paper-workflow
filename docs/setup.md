# 环境准备

本文档记录项目运行所需的前提条件。

## 1. Chrome 远程调试（知网相关技能必需）

使用 CNKI 技能前，需要 Chrome 可被自动化工具访问。

步骤：
1. 关闭所有 Chrome 窗口
2. 启动带远程调试端口的 Chrome
3. 保持窗口运行

示例命令：
`ash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
`

如果路径不对，可先查找本机 Chrome 安装位置。

## 2. 知网登录（下载文献时才需要）

下载 PDF/CAJ 前，需要在 Chrome 中手动登录：
- 访问 https://www.cnki.net
- 使用机构账号或校园网环境登录

遇到验证码时，由你手动完成。

## 3. Python 依赖（部分技能可选）

如果使用论文阅读、PPT 等功能，可能需要：
`ash
pip install pymupdf pillow python-pptx
`

## 4. R 依赖（仅 R 图表后端可选）

如果使用 R 绘图，需要先确认 Rscript 可用。

## 5. MCP / 检索工具

如果项目已配置：
- PubMed
- CrossRef
- arXiv

可直接用于国际文献检索。

## 自检建议

使用前先确认：
- 知网流程：Chrome 可达
- Python 流程：依赖已安装
- R 流程：Rscript 可用

缺失时不要直接报错，应明确告知缺少什么。
