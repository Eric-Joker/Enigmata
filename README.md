<div align="center">

[![](https://img.shields.io/github/v/release/Eric-Joker/Enigmata?color=purple)](https://github.com/Eric-Joker/Enigmata/releases)
[![](https://img.shields.io/badge/license-GPLv3-blue)](https://github.com/Eric-Joker/Enigmata/blob/main/LICENSE)
[![](https://img.shields.io/badge/python-3.12-yellow)](https://www.python.org)

[🛠Install](#install) |
[📖Usage](#usage) |
[💡New insights](https://github.com/Eric-Joker/Enigmata/issues) |
[💖Sponsor](#donation)

[简体中文](./docs/README.zh-CN.md) | English

</div>

Due to the fact that resource packs developed by the community for Minecraft cannot be encrypted like those in the Marketplace, there will always be a few unethical individuals who steal the code from our hard-developed resource packs and publish it without attribution.

**We do not want this script to be used too frequently, as it goes against the spirit of collaboration and sharing within the community. If you are willing to contribute to the community, please do not release only obfuscated resource packs.**

# Enigmata

> **Enigmata** is the Mythus Aeon from Honkai: Star Rail, it is a fallacy that all things can be experienced and recognized.

Enigmata is an open-source resource pack obfuscator for Minecraft Bedrock Edition. It adds markers to files and obfuscates Json key values while ensuring the game can read them correctly. Currently, it has several features, such as:

-  Randomly permute and combine some visually similar characters to replace some JSON keys, values, and some file names.
-  Adding specific information to the tEXt of each PNG and to the id section of each TGA.
-  Merge JSON files in a folder.

## Supported Resource Pack

This obfuscator has some limitations regarding the RP it supports. Most of these limitations are not difficult to resolve, but since I do not need them. [Pull requests](https://github.com/Eric-Joker/Enigmata/pulls) are welcome.

- NOT ADDON
- The JsonUI obfuscation feature will only obfuscate the controls in all JSON files within a specific folder. eg:

  ```
  ui/
  ├── hud_screen.json
  ├── inventory_screen.json
  └── namespace/
      ├── hud.json
      └── inventory.json
  ```
  It will only obfuscate the JsonUI in the `namespace`. If the JsonUI in the `ui` references controls from the former, the references will be obfuscated accordingly.
- When using the filename obfuscation feature, the obfuscated images should preferably not be in the root directory of the RP, as this may lead to unexpected results.
- When using the JsonUI and Entity series file merging features, files in subpacks are not merged. (The logic for excluding subpacks has not been tested.)
- When using the merging feature for Entity series files, filenames must comply with the standards for /.+?\\.(animation_controllers|animations|renderer_controllers|geo)\\.json/.
- and more?
  
## Install

Your device needs to have Python 3.12 or higher version installed.

First, Download the source zip and unzip or using git to clone this repository:

```sh
git clone https://github.com/Eric-Joker/Enigmata.git
cd Enigmata
```

Next, use pip to install the dependencies:

```sh
pip install -r requirements.txt
```

## Usage

Take a look at `config_example.yaml` for configuration, modify it and rename it to `config.yaml`.

Then, try running the following:
```sh
python main.py
```

All configurations in config.yaml have corresponding flags, which will take precedence over the file. Use `-h` to see details.

The obfuscated package will be output in the `./output`, where `obfuscation_reference.json` will list the corresponding strings before and after obfuscation."

Under certain conditions, you may be required to update the Vanilla Data. You need to change the `vanillas_path` configuration to the directory containing all the vanilla RP of the latest version of Minecraft. Use `-e` to enter the data extraction process.

## Donation

[PayPal](https://www.paypal.com/paypalme/Airkk426)

[afdian](https://afdian.com/a/Eric_Joker)

Thank you very much for your willingness to support the author. Your avatar will appear on my Github profile and in the Readme of this project.

## Thanks

Thanks to all the contributors of this project!

Thanks for the help in finding more circle characters [TangTang](https://github.com/404).
