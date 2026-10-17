# 船群之眼 · USV SwarmEye

以「航迹档案」为视觉主题的无人船风险决策与复盘原型。Python 3.12 + Streamlit 1.66.0，采用 Custom Components v2 承载原创玻璃界面与 SVG 航迹；计算、事件和记录由 Python 统一管理。

## 本地运行

```powershell
uv venv --python 3.12 .venv
uv pip install --python .venv/Scripts/python.exe -r requirements.txt
.venv/Scripts/python.exe -m streamlit run app.py
```

也可使用 Python 3.12 的标准 `venv` 和 `pip`。无需 Node 构建、地图接口、数据库或 Secrets。

## 发布到 Streamlit Community Cloud

在 [Streamlit Community Cloud](https://share.streamlit.io/) 登录并连接 GitHub，创建应用：

| 设置 | 值 |
| --- | --- |
| Repository | `normazzz271828-prog/USV-SwarmEye` |
| Branch | `main` |
| Main file path | `app.py` |
| Advanced settings → Python version | `3.12` |
| Secrets | 无需填写 |

点击 Deploy。GitHub 推送不代表云端已运行；首次部署后应实际打开首页，开始演练并验证导出与恢复。

`.python-version` 用于本地工具选择解释器；云端 Python 版本应在部署界面的高级设置选择。依赖已在 `requirements.txt` 锁定。官方部署说明：https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy

## 当前功能

- V4 原创首页：中文衬线标题、轻玻璃场景卡、无框 SVG 会遇图谱、横向决策流程、真实会话记录入口。
- 场景实验室：交叉、对遇、追越三个 180 秒模板，六组预设；网页调整观测延迟、双方航速倍率、转向/离队时刻和队内间距。
- 工作台：1×/2×/4×/8× 目标回放速度、单步、下一事件、全局/聚焦、图层开关、船位短过渡；完整逐秒计算，告警升级自动暂停。
- 结果对比：两次已完成运行的配置差异、共享尺度双图、共同时间轴、首次事件、最高等级、L3 时长、数据不足时间及真实最近距离。
- 档案：完成后开放当时快照与事后真值对照，追加复核意见。
- 按需导出 HTML 报告和 JSON 记录，导入时重算并校验证据；保留 schema=1 的旧版记录恢复和继续演练。
- 桌面与手机布局，无外部字体或图片网络依赖。

## 数据和方法

这是自建仿真演练，非实船记录；不发送船控命令，不承诺实海安全性，不将工程规则描述为论文精确复现。

外部目标根据观测距离、航向和速度聚类，本船明确排除。船舶域为工程假设椭圆，群显示使用其凸包；硬约束使用可见的单船外接圆。风险判断采用恒速 CPA 和明确的演练阈值，不是碰撞概率。详见 [方法和验收](docs/METHOD_AND_VALIDATION.md)。

记录存放在隔离的 Streamlit 会话内，最多 20 次演练。浏览器刷新、会话失效或云端重启后，请通过自己下载的 JSON 恢复。没有永久云存储或账号系统。下载记录是可编辑的交换文件，重算校验用于检查一致性，不提供身份认证或防篡改签名。

## 测试

```powershell
uv pip install --python .venv/Scripts/python.exe -r requirements-dev.txt
.venv/Scripts/python.exe -m pytest -q
```

浏览器验收使用 Playwright，先安装 `playwright` 与 Chromium，再启动 `8510` 端口服务，执行 `python tests/browser_smoke.py`。截图和导出测试文件写入忽略的 `artifacts/`。见 [验收记录](docs/METHOD_AND_VALIDATION.md)。

升级验收运行 `python tests/browser_upgrade.py`；也可传入线上 URL。升级范围和限制见 [V2 发布说明](docs/UPGRADE_V2.md)。网站入口：[船群之眼](https://usv-swarmeye.streamlit.app/)。

## 文件结构

```text
app.py                    Streamlit 入口与会话事件处理
swarmeye/engine.py        场景、因果观测、风险规则、事件、保存恢复
swarmeye/graphics.py      原创 SVG 与等比例米制态势图
swarmeye/views.py         页面内容与报告
swarmeye/component.py     Streamlit CCv2 绑定
swarmeye/ui.css           V4 视觉与响应式布局
swarmeye/ui.js            输入传输、自动回放调度、文件下载
tests/                    计算与浏览器验收
```
