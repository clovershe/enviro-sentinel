# ESP32 真机节点

## 推荐硬件

- ESP32 DevKit V1
- BME280（温湿度；I²C 地址默认 `0x76`）
- MQ-135（空气质量演示，接 GPIO 34）
- 可选电池分压采样（GPIO 35，必须保证引脚电压不超过 3.3V）

## 接线

| BME280 | ESP32 |
|---|---|
| VIN | 3V3 |
| GND | GND |
| SCL | GPIO 22 |
| SDA | GPIO 21 |

## 烧录

1. 安装 VS Code 与 PlatformIO 插件；
2. 把 `include/secrets.h.example` 复制为 `include/secrets.h`；
3. 填写 Wi‑Fi、电脑局域网 IP、设备 ID 与密钥；
4. 在项目目录执行 `pio run -d firmware/esp32 -t upload`；
5. 执行 `pio device monitor -d firmware/esp32` 查看上报日志。

如果 BME280 未连接，固件会使用 24°C / 50%RH 的回退数据，方便先验证网络和认证链路。

## 工程细节

- NTP 校时后才允许上报，避免时间窗口校验失败；
- 序列号写入 ESP32 NVS，重启后继续递增，防止服务端判定为重放；
- 设备密钥独立放在被 Git 忽略的 `secrets.h`；
- 小数使用固定两位字符串参与签名，服务端在 Pydantic 校验时再转换为数值；
- MQ-135 的原始 ADC 映射只用于链路演示，做实验报告前应补传感器标定曲线。
