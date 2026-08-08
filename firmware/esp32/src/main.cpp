#include <Adafruit_BME280.h>
#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <Wire.h>
#include <mbedtls/md.h>
#include <time.h>

#include "secrets.h"

namespace {
constexpr uint32_t kSampleIntervalMs = 5000;
constexpr uint8_t kAirQualityPin = 34;
constexpr uint8_t kBatteryPin = 35;

Adafruit_BME280 bme;
Preferences preferences;
bool sensorReady = false;
uint32_t lastSampleAt = 0;

String hmacSha256(const String &message, const char *secret) {
  byte digest[32];
  const mbedtls_md_info_t *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
  mbedtls_md_hmac(info, reinterpret_cast<const unsigned char *>(secret),
                  strlen(secret),
                  reinterpret_cast<const unsigned char *>(message.c_str()),
                  message.length(), digest);

  char hex[65];
  for (size_t index = 0; index < sizeof(digest); ++index) {
    snprintf(hex + index * 2, 3, "%02x", digest[index]);
  }
  hex[64] = '\0';
  return String(hex);
}

void connectWifi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to Wi-Fi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print('.');
  }
  Serial.printf("\nWi-Fi connected, IP=%s\n", WiFi.localIP().toString().c_str());
}

void synchronizeClock() {
  configTime(8 * 3600, 0, "ntp.aliyun.com", "pool.ntp.org");
  Serial.print("Synchronizing clock");
  const uint32_t startedAt = millis();
  while (time(nullptr) < 1700000000 && millis() - startedAt < 15000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
}

uint64_t nextSequence(uint64_t timestamp) {
  const uint64_t stored = preferences.getULong64("sequence", 0);
  const uint64_t clockBased = timestamp * 1000ULL;
  const uint64_t next = max(stored + 1, clockBased);
  preferences.putULong64("sequence", next);
  return next;
}

float readBatteryPercent() {
  const int raw = analogRead(kBatteryPin);
  const float pinVoltage = raw / 4095.0f * 3.3f;
  const float batteryVoltage = pinVoltage * 2.0f;  // 1:1 分压电阻
  return constrain((batteryVoltage - 3.3f) / (4.2f - 3.3f) * 100.0f, 0.0f, 100.0f);
}

int readAirQualityIndex() {
  // MQ-135 仅用于演示。正式项目需经过 Rs/R0 标定并做温湿度补偿。
  return map(analogRead(kAirQualityPin), 0, 4095, 0, 500);
}

bool publishTelemetry() {
  if (WiFi.status() != WL_CONNECTED) {
    connectWifi();
  }

  const uint64_t timestamp = static_cast<uint64_t>(time(nullptr));
  if (timestamp < 1700000000) {
    synchronizeClock();
    return false;
  }

  const float temperature = sensorReady ? bme.readTemperature() : 24.0f;
  const float humidity = sensorReady ? bme.readHumidity() : 50.0f;
  const int airQuality = readAirQualityIndex();
  const float battery = readBatteryPercent();
  const int rssi = WiFi.RSSI();
  const uint64_t sequence = nextSequence(timestamp);

  // 小数作为固定两位字符串发送，确保 ESP32 与 Python 生成完全一致的签名文本。
  char temperatureText[16];
  char humidityText[16];
  char batteryText[16];
  snprintf(temperatureText, sizeof(temperatureText), "%.2f", temperature);
  snprintf(humidityText, sizeof(humidityText), "%.2f", humidity);
  snprintf(batteryText, sizeof(batteryText), "%.2f", battery);

  char canonicalBuffer[512];
  snprintf(
      canonicalBuffer, sizeof(canonicalBuffer),
      "{\"device_id\":\"%s\",\"metrics\":{\"air_quality\":%d,\"battery\":\"%s\","
      "\"humidity\":\"%s\",\"rssi\":%d,\"temperature\":\"%s\"},"
      "\"sequence\":%llu,\"timestamp\":%llu}",
      DEVICE_ID, airQuality, batteryText, humidityText, rssi, temperatureText,
      static_cast<unsigned long long>(sequence),
      static_cast<unsigned long long>(timestamp));
  const String signature = hmacSha256(String(canonicalBuffer), DEVICE_SECRET);

  StaticJsonDocument<768> document;
  document["device_id"] = DEVICE_ID;
  document["timestamp"] = timestamp;
  document["sequence"] = sequence;
  JsonObject metrics = document.createNestedObject("metrics");
  metrics["temperature"] = temperatureText;
  metrics["humidity"] = humidityText;
  metrics["air_quality"] = airQuality;
  metrics["battery"] = batteryText;
  metrics["rssi"] = rssi;
  document["signature"] = signature;

  String body;
  serializeJson(document, body);
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("Content-Type", "application/json");
  const int status = http.POST(body);
  const String response = http.getString();
  http.end();

  Serial.printf("POST status=%d seq=%llu temp=%s response=%s\n", status,
                static_cast<unsigned long long>(sequence), temperatureText,
                response.c_str());
  return status == HTTP_CODE_ACCEPTED;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  preferences.begin("iot-node", false);
  analogReadResolution(12);
  Wire.begin();
  sensorReady = bme.begin(0x76);
  Serial.printf("BME280: %s\n", sensorReady ? "ready" : "not found, using fallback");
  connectWifi();
  synchronizeClock();
}

void loop() {
  if (millis() - lastSampleAt >= kSampleIntervalMs || lastSampleAt == 0) {
    lastSampleAt = millis();
    publishTelemetry();
  }
  delay(50);
}
