# 贡献指南

感谢你改进 Northwest IoT Observatory。本项目同时包含 Python 服务端、浏览器看板和 ESP32 固件，请让每次变更保持小而可验证。

## 本地开发

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pre-commit install
```

提交前运行：

```bash
ruff check .
ruff format --check .
pytest --cov=iot_platform --cov-fail-under=65
```

固件变更还需要：

```bash
cp firmware/esp32/include/secrets.h.example firmware/esp32/include/secrets.h
pio run -d firmware/esp32
```

## 分支与提交

- 从最新的 `main` 创建短生命周期分支，例如 `feat/offline-buffer`；
- 提交信息使用 Conventional Commits，例如 `feat: add offline telemetry buffer`；
- 一个 Pull Request 只解决一个主题，并写清验收方式；
- 行为变化必须添加测试，UI 变化必须附截图；
- 不要提交真实设备密钥、Wi-Fi 凭据、数据库或构建产物。

## 代码设计

- API 端点只处理协议转换，业务校验放在 `service.py`；
- 数据访问集中在 `database.py`，不要在路由中直接写 SQL；
- 告警规则保持纯函数，便于单元测试；
- 固件必须考虑断网、重启、时钟未同步和消息重放。
