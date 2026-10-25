# ERPNext 核心业务模块 UI 自动化测试框架

## 📌 项目简介

本项目是针对开源 ERP 系统（ERPNext）的实战自动化测试项目。基于 **Python + Pytest + Playwright** 编写，采用企业级 **POM (Page Object Model)** 分层架构，验证系统在异常输入、边界值等场景下的健壮性。

## 🛠️ 技术栈

- **语言**：Python 3.12
- **测试框架**：Pytest
- **自动化工具**：Playwright

## 📂 架构设计（分层解耦）

- `config/`：全局配置（URL、账号等）
- `pages/`：页面对象层（基础操作、元素定位、页面动作）
- `utils/`：工具层（测试数据生成，如超长文本）
- `tests/`：测试用例层（断言和业务逻辑）

## 🐞 测试发现与缺陷报告

本地执行 5 条用例，3 条通过、2 条失败。详情见 [Test_Report.md](Test_Report.md)。

1. **异常输入反馈风险**：非法数字和日期输入后，测试未观察到明确的可见错误提示；尚不能证明非法日期被静默转换。
2. **重复保存响应问题**：快速重复点击“保存”时，校验模态框拦截第二次点击，等待约 15.7 秒，超过 8 秒阈值。

## 🚀 如何运行

先启动本地 ERPNext（默认 `http://localhost:8080`），然后在项目根目录运行：

```bash
pip install -r requirements.txt
playwright install chromium
pytest -v
```

本机 Chromium 下载因网络重置失败时，已使用安装好的 Microsoft Edge 完整执行：

```powershell
C:\Users\levi\AppData\Local\Programs\Python\Python312\python.exe -m pytest -q --browser-channel=msedge
```

默认账号配置见 `config/config.py`，可用 `ERPNEXT_BASE_URL`、`ERPNEXT_USERNAME`、`ERPNEXT_PASSWORD` 环境变量覆盖。公开仓库中不要提交真实生产凭据。

