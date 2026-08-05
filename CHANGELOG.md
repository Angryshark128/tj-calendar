# Changelog

本项目遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/) 与 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Planned
- `tjcal import`：支持自定义日历数据导入。
- 数据交叉校验：对齐 AkShare / Tushare 节假日安排。

## [0.1.0] - 2026-08-05

### Added
- 内置中国 A 股交易日历（1990–2035），覆盖 `CN_A_SHARE` / `SSE` / `SZSE` / `BSE` 四档市场，北交所成立前日期抛 `CalendarRangeError`。
- Python API：`is_trade_day` / `next_trade_day` / `prev_trade_day` / `trade_days_between` / `get_calendar_info`，对象接口 `TradingCalendar`。
- CLI `tjcal`：`today` / `check` / `next` / `prev` / `range` / `info` / `check-update` / `update`，支持 `--market` 与 `--json`。
- 显式更新流程：`check-update` 先拉取小体积 `metadata.json`（版本 + sha256 + bundle URL），版本一致则跳过；`update` 下载时做 sha256 校验 + 原子替换，失败不破坏现有数据。更新源通过 `TIANJI_CALENDAR_METADATA_URL` / `TIANJI_CALENDAR_MIRROR_URLS` 配置。
- 数据加载优先级：用户本地数据 > 内置数据；本地数据损坏时回退并告警。
- 数据生成脚本 `scripts/build_calendar.py`（离线编码节假日 + `--fetch` 合并 AkShare 实盘），数据版本独立于代码版本。
- 离线优先：查询 API 不联网。
- 首个版本通过 trusted publishing（OIDC）发布到 PyPI。

[Unreleased]: https://github.com/Angryshark128/tj-calendar/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Angryshark128/tj-calendar/releases/tag/v0.1.0
