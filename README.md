# EzyAssistanceSS-N

EzyAssistanceSS-N (EAS-N)

基于图像识别技术，为《铃兰之剑》提供刷图、爬塔、清体力和日常领取等自动化辅助。

## 安装

本项目使用 `uv` 管理依赖，需要 Python 3.10 到 3.12。

```bash
uv sync
```

## 运行

```bash
uv run python main.py
```

请在仓库根目录运行程序。脚本会读写 `app_config.yaml`、`active_config.yaml`、`Icons/` 和 `img/` 等相对路径。

## 官方模拟器模式

新版适配优先使用官方模拟器前台窗口模式，不再要求 Root 或 ADB：

- 将模拟器画面固定为 `1280x720`。
- 运行脚本时保持模拟器窗口可见，脚本会把窗口置前并接管鼠标点击/拖拽。
- 在设置页选择控制模式 `window`，填写官方模拟器窗口标题关键字，例如 `铃兰之剑` 或模拟器窗口名。
- 如果仍需旧 MuMu/ADB 方式，可选择控制模式 `adb` 并填写 ADB 路径和连接地址。

## 新版素材准备

新版游戏 UI 变化后，需要重新采集 `Icons/` 下的模板图。建议每张只截取稳定的小区域：

- 登录开始按钮、公告关闭按钮、主页资源入口、返回按钮。
- 每日/资源菜单标识、各资源本入口、难度/关卡编号区域。
- 代行、开始战斗、免费代行确认、战斗加速/自动按钮。
- 战斗结束、胜利、升级弹窗、奖励入口和领取按钮。

OCR 默认使用简体中文模型。角色选择和关卡识别如果不稳定，请优先更新小图模板或收窄裁剪区域。

完整模板文件名见 `ASSETS.md`。

## 项目结构

```text
.
├── main.py                 # PySide6 桌面 UI 入口，负责设置页、任务选择和流程调度
├── ADBClass.py             # 设备控制统一入口，支持 adb 与 window 两种控制模式
├── OCRClass.py             # EasyOCR 封装，默认使用简体中文与英文识别
├── OctoUtil.py             # 图像裁剪、模板匹配、配置写入等通用工具
├── EASLogger.py            # UI 日志文件写入工具
├── BaseFlow.py             # 流程执行框架
├── BaseNode.py             # 流程节点基类
├── DeciderNode.py          # 条件分支节点
├── workflow/               # 直接由 UI 调用的业务流程
├── Nodes/                  # 可组合的流程节点实现
├── Flows/                  # 基于节点组装的旧版/测试流程
├── Icons/                  # OpenCV 模板匹配素材，新版界面需要按 ASSETS.md 更新
├── configs/                # 任务预设配置
├── trainingData/           # OCR/角色识别训练与标注遗留数据
├── autoSelectCharRecon/    # 角色识别裁剪素材
├── res/                    # OCR 字典等资源
├── img/                    # 运行时截图输出目录
├── logs/                   # UI 日志输出目录
├── ASSETS.md               # 新版模板素材采集清单
├── app_config.yaml         # 全局配置：控制模式、窗口标题、OCR 语言、任务与角色清单
├── active_config.yaml      # 当前启用的刷图任务配置
├── pyproject.toml          # uv 项目依赖配置
└── uv.lock                 # uv 锁定文件
```

核心运行链路是 `main.py` 创建 UI，用户点击启动后构造 `workflow/` 下的流程；流程内部仍通过 `ADBClass.AdbSingleton.getInstance()` 调用 `screen_capture()`、`tap()`、`swipe()` 等统一设备 API。`controlMode: window` 时这些调用会转为官方模拟器前台窗口截图和鼠标输入，`controlMode: adb` 时继续走旧版 ADB。

`workflow/` 里的主要文件：

- `StartApp.py`：连接/激活模拟器窗口，处理登录、公告和登录奖励。
- `MainMaterial.py`：资源本导航、难度选择、代行/手动战斗和结算处理。
- `ReceiveReward.py`：回到主页并领取日常奖励。
- `WeekTower.py`：周常塔罗/爬塔相关流程。

`Nodes/` 和 `Flows/` 是较早的流程编排层，目前部分逻辑仍可复用，但主 UI 更常直接调用 `workflow/`。新增功能时优先复用 `ADBClass.py`、`OCRClass.py`、`OctoUtil.py` 这些公共边界，避免在业务流程里直接写窗口或 ADB 细节。

## 声明

本软件开源、免费，仅供学习交流使用。使用自动化工具可能违反游戏或平台服务条款，请自行承担相关风险。
