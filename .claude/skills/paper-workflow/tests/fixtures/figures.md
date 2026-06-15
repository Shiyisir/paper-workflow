# 图片测试 Fixture

## 存在的图片引用

此图片文件 `figures/sample.png` 需要在测试前由测试脚本创建或提供。

![示例图表](figures/sample.png)

图1：示例图表

## 缺失的图片引用

以下引用指向不存在的文件，应触发校验 error：

![缺失图片](figures/missing.png)

## SVG 图片引用

SVG 缺工具时应触发 warning，不应导致测试崩溃。

![SVG 图表](figures/chart.svg)

图2：矢量图表

## Web URL（应跳过检查）

![外部图片](https://example.com/image.png)
