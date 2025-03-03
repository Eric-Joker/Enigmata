<div align="center">

[![](https://img.shields.io/github/v/release/Eric-Joker/Enigmata?color=purple)](https://github.com/Eric-Joker/Enigmata/releases)
[![](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/Eric-Joker/Enigmata/blob/main/LICENSE)
[![](https://img.shields.io/badge/python-3.12-yellow)](https://www.python.org)

[🛠安装](#安装) |
[📖使用](#使用) |
[💡议题](https://github.com/Eric-Joker/Enigmata/issues) |
[💖赞助](#给我打钱)

简体中文 | [English](../README.md)

</div>

由于社区为 Minecraft 开发的资源包不能像市场里的那样被加密，在庞大的人口基数下总会有几个没有道德的人窃取我们辛苦开发的资源包中的内容并在没有署名的情况下发布。

**我们不希望这个脚本被过于频繁地使用，因为这会违背社区的合作与共享的精神。如果你愿意为社区做出贡献，请不要只发布混淆的资源包。**

# Enigmata

> **Enigmata(迷思)** 是《崩坏：星穹铁道》的神秘星神，祂认为万物皆可体认乃是一派妄言。

Enigmata 是一款开源的 Minecraft Bedrock Edition 资源包混淆器，在保证游戏能正常读取的情况下为文件加上标志、对 Json 的键值进行混淆。目前它据有多项功能，比如：

- 随机排列组合一些样貌相似的字符替换一些 Json 键值和贴图文件名
- 为每个 PNG 的 tEXt 和 TGA 的 id section 添加特定信息
- 合并一个文件夹下的 Json 文件

## 支持的资源包

此混淆器适用的资源包具有一些限制，其实解决绝大部分限制并不算困难，但是因为我用不到所以不想做，欢迎 [Pull Request](https://github.com/Eric-Joker/Enigmata/pulls)。

- JsonUI 混淆功能只会混淆在单独文件夹下的所有 json 文件里的控件。举例：

  ```
  ui/
  ├── hud_screen.json
  ├── inventory_screen.json
  └── namespace/
      ├── hud.json
      └── inventory.json
  ```
  它将只会混淆 `namespace` 文件夹下的 JsonUI，如果 `ui` 文件夹下的 JsonUI 有引用前者中的控件，引用的地方会被正常混淆。
- 使用文件名混淆功能时，被混淆的图片尽量不能处于资源包根目录，不然可能会引发预期之外的结果。
- 使用 JsonUI、Entity 系文件合并功能时，子包的文件不进行合并。（排除子包的相关逻辑暂未经测试）
- 使用合并 Entity 系文件功能时，文件名必须符合 /.+?\\.(animation_controllers|animations|renderer_controllers|geo)\\.json/ 的规范。
- 也许有更多忌讳，想不起来了（）
  
## 安装

您的设备上需要装有 Python 3.12 或更高版本。

首先，下载由源代码打包的压缩包并解压或使用 Git 克隆仓库：

```sh
git clone https://github.com/Eric-Joker/Enigmata.git
cd Enigmata
```

然后，使用 pip 安装依赖：

```sh
pip install -r requirements.txt
```

## 使用

查看 `config_example.yaml`，根据里面的介绍修改配置, 然后更改其文件名为 `config.yaml`。

然后去命令行运行：
```sh
python main.py
```

所有在`config.yaml`的配置都有对应的命令行标志，优先级将高于文件，携带 `-h` 以查看详情。

混淆后的包体将输出在 `./output` 文件夹下，其中 `obfuscation_reference.json` 里将混淆前后的字符串一一对应。

在一定条件下可能会要求更新 Vanilla Data，需要将 `vanillas_path` 配置更改为包含 Minecraft 最新版的所有 vanilla 资源包的目录。可以携带 `-e` 进入提取数据流程。

## 给我打钱

<img src='receiving code.png' width=400>

[PayPal](https://www.paypal.com/paypalme/Airkk426)

[爱发电](https://afdian.com/a/Eric_Joker)

非常感谢您的支持\~您的头像会出现在我的 Github 主页和本项目的 Readme 中\~

## 感谢

感谢此项目的所有贡献者！

感谢群U [糖糖](https://github.com/404) 提供的更多圆圈字符（
