# 安全政策

## 支持范围

当前维护分支为 `main`。这是教学与作品集项目，不应直接用于生命安全、工业控制或未经评估的生产环境。

## 报告漏洞

请不要在公开 Issue 中披露可利用细节。发布到个人 GitHub 后，请通过仓库的 **Security → Report a vulnerability** 私密报告；仓库所有者应在 7 天内确认，并在修复发布后再公开说明。

## 部署注意事项

- `.env.example` 和 `secrets.h.example` 中的密钥只用于本地演示；
- 公网部署前必须轮换设备密钥，并为 HTTP/MQTT 启用 TLS；
- `infra/mosquitto/mosquitto.conf` 允许匿名连接，仅限本地开发；
- SQLite 中的设备共享密钥未加密，生产环境应迁移到专用密钥管理服务；
- 日志、截图和 Issue 中不得包含 Wi-Fi 密码、Token 或完整设备密钥。
