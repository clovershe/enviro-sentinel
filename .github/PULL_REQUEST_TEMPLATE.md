## 变更说明

<!-- 说明为什么改、改了什么。 -->

## 验证

- [ ] `ruff check .`
- [ ] `ruff format --check .`
- [ ] `pytest --cov=iot_platform --cov-fail-under=65`
- [ ] 如涉及固件：`pio run -d firmware/esp32`
- [ ] 如涉及界面：附更新前后截图

## 安全检查

- [ ] 没有提交 Wi-Fi 密码、设备密钥、Token 或本地数据库
- [ ] 新增配置已同步到 `.env.example` 或 `secrets.h.example`
