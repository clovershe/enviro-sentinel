from dataclasses import dataclass

from .schemas import Metrics


@dataclass(frozen=True)
class RuleAlert:
    code: str
    severity: str
    message: str


def evaluate(metrics: Metrics) -> list[RuleAlert]:
    alerts: list[RuleAlert] = []
    if metrics.temperature >= 35:
        alerts.append(RuleAlert("HIGH_TEMPERATURE", "critical", "温度达到 35°C 以上"))
    elif metrics.temperature >= 30:
        alerts.append(RuleAlert("HIGH_TEMPERATURE", "warning", "温度达到 30°C 以上"))

    if metrics.air_quality >= 200:
        alerts.append(RuleAlert("POOR_AIR_QUALITY", "critical", "空气质量指数达到重度污染"))
    elif metrics.air_quality >= 120:
        alerts.append(RuleAlert("POOR_AIR_QUALITY", "warning", "空气质量指数偏高"))

    if metrics.battery <= 15:
        alerts.append(RuleAlert("LOW_BATTERY", "warning", "设备电量低于 15%"))
    return alerts
