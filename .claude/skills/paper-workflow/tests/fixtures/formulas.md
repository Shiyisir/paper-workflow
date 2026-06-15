# 公式测试 Fixture

## 合法块公式

玻尔兹曼方程：

$$
S = k_B \ln W
$$

## 合法行内公式

熵变定义为 $dS = \delta Q / T$，其中 $T$ 为绝对温度。

## docx-safe 下应 warning 的 \tag{}

在 docx profile 中，以下公式可能因 Pandoc OMML 转换失败：

$$
E = mc^2 \tag{1}
$$

## Unicode 下标反例

错误写法：H₂O 和 CO₂ 不应使用 Unicode 下标字符 x₁、x₂。

正确写法应为 $H_2O$ 和 $CO_2$。

## 公式闭合问题（故意制造）

$$
S = k_B \ln W
$$

$$
x + y = z
