# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Added
- 首个 MVP 版本：离线优先的中国市场交易日历。

### 说明
- 内置日历数据编码 2019–2027 已知节假日休市，其余年份为工作日近似（best-effort）。
- 数据版本 `2026.08.04` 独立于代码版本。

## [0.1.0] - 2026-08-04

### Added
- 内置中国 A 股交易日历（2000–2035），覆盖 `CN_A_SHARE` / `SSE` / `SZSE` / `BSE` 四档市场。
- Python API：`is_trade_day` / `next_trade_day` / `prev_trade_day` / `trade_days_between` / `get_calendar_info`。
- 对象接口 `TradingCalendar`。
- CLI `tjcal`：`today` / `check` / `next` / `prev` / `range` / `info`，支持 `--market` 与 `--json`。
- 超出市场覆盖范围抛出 `CalendarRangeError`，北交所成立前日期同样报错。
- 数据加载优先级：用户本地数据 > 内置数据；本地数据损坏时回退并告警。
- 数据生成脚本 `scripts/build_calendar.py`。
- 离线优先：查询 API 不联网。

[Unreleased]: https://github.com/Angryshark128/tj-calendar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Angryshark128/tj-calendar/releases/tag/v0.1.0
