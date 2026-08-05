[English](README.en.md) | **中文**

# Tianji Calendar

离线优先的中国市场交易日历工具。

Tianji Calendar 是 [Tianji](https://github.com/Angryshark128/tianji) 开源市场研究工具生态的组成部分。运行时无需联网，提供简洁的交易日查询 API 与 CLI。

## 特性

- 离线优先：运行时完全不需要网络
- 市场感知的交易日历模型（`CN_A_SHARE`、`SSE`、`SZSE`、`BSE`）
- 内置中国 A 股交易日历（1990–2035）
- 判断某天是否交易日、前后交易日、区间交易日查询
- 简洁的 Python API 与 CLI
- 显式导入与更新流程（数据版本与代码版本分离）
- 不需要 Tushare token

## 安装

```bash
pip install tj-calendar
```

## 快速开始

```python
from tj_calendar import is_trade_day, next_trade_day, trade_days_between

is_trade_day("2026-08-04")
# True

is_trade_day("2025-10-01")  # 国庆节
# False

next_trade_day("2025-09-30")
# datetime.date(2025, 10, 9)

trade_days_between("2026-08-03", "2026-08-07")
# [datetime.date(2026, 8, 3), datetime.date(2026, 8, 4),
#  datetime.date(2026, 8, 5), datetime.date(2026, 8, 6),
#  datetime.date(2026, 8, 7)]
```

### 市场感知查询

```python
from tj_calendar import is_trade_day

is_trade_day("2021-11-15", market="BSE")  # 北交所首个交易日
# True

is_trade_day("2018-01-02", market="BSE")  # 北交所成立之前
# 抛出 tj_calendar.CalendarRangeError：
#   2018-01-02 is outside BSE calendar range 2021-11-15 to 2035-12-31.
```

每个市场有独立的覆盖范围。查询超出市场范围的日期会抛出 `CalendarRangeError`，而不是猜测。

### CLI

```bash
tjcal check 2026-08-04
# 2026-08-04 is a trading day.

tjcal next 2025-09-30
# 2025-10-09

tjcal range 2026-08-03 2026-08-07
# 2026-08-03
# 2026-08-04
# 2026-08-05
# 2026-08-06
# 2026-08-07

tjcal info
# market: CN_A_SHARE
# coverage_start: 1990-12-19
# coverage_end: 2035-12-31
# trade_day_count: 9226

tjcal check 2025-10-01 --json
# {"date": "2025-10-01", "is_trade_day": false, "market": "CN_A_SHARE"}
```

## 日期输入与输出

查询 API 接受 ISO 日期字符串（`"2026-08-04"`）、`datetime.date` 或 `YYYYMMDD` 整数（`20260804`），返回 `datetime.date`。

## CLI 参考

```text
tjcal today [--market M] [--json]
tjcal check <date> [--market M] [--json]
tjcal next <date> [--market M] [--json]
tjcal prev <date> [--market M] [--json]
tjcal range <start> <end> [--market M] [--json]
tjcal info [--market M] [--json]
tjcal check-update [--json]
tjcal update [--json]
```

## 数据更新

内置日历覆盖到 2035 年，普通查询完全离线。每年节假日安排公布后，可以显式更新日历数据：

```bash
# 配置更新源（元数据地址，必填；多镜像用冒号分隔）
export TIANJI_CALENDAR_METADATA_URL="https://tj-1310342032.cos.ap-beijing.myqcloud.com/calendar/latest/metadata.json"

tjcal check-update   # 只拉取几百字节的 metadata，判断是否需要更新
tjcal update         # 版本一致则跳过；不一致才下载完整 bundle（sha256 校验）
```

Python 中每次调用前保证数据最新：

```python
from tj_calendar import ensure_fresh, is_trade_day

ensure_fresh()       # 数据已最新时静默跳过，仅拉 metadata
is_trade_day("2026-08-04")
```

`update` 通过 sha256 校验下载内容，失败时保留现有数据，绝不破坏当前可用的日历。

## 数据说明

- 覆盖范围：`CN_A_SHARE` / `SSE` / `SZSE` 自 1990-12-19 至 2035-12-31；`BSE` 自首个交易日 2021-11-15 起。
- 内置数据编码了已知的 A 股节假日休市（2019–2027）；更早和更晚的年份使用工作日近似，标记为 best-effort。
- 查询从不联网。更新日历是显式操作。

## 开发

```bash
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest -q
```

内置数据文件由 `scripts/build_calendar.py` 生成。

## Tianji 生态

Tianji 是一套面向市场研究的可组合开源工具生态。每个子项目都可以独立使用，也可以组合成完整的市场研究工作流。

- tj-calendar: 离线优先的交易日历
- tj-symbols: 证券代码标准化与格式转换
- tj-data: 市场数据适配与本地缓存
- tj-factors: 技术指标与因子
- tj-metrics: 绩效指标
- tj-backtest: 轻量回测
- tj-research: AI 辅助研究
- tj-terminal: 综合研究工作台

## Disclaimer / 免责声明

This project is for research and educational purposes only.
It does not provide investment advice, trading signals, or financial recommendations.
Calendar data is maintained on a best-effort basis; users should verify critical use cases independently.

本项目仅用于研究和教育目的，不构成投资建议、交易信号或金融建议。日历数据尽力维护，重要场景请自行核实。
