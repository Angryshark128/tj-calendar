# tj-calendar API

> 离线优先的中国市场交易日历。查询 API 不联网，数据更新显式触发。

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [查询函数](#查询函数)
  - [is_trade_day](#is_trade_day)
  - [next_trade_day](#next_trade_day)
  - [prev_trade_day](#prev_trade_day)
  - [trade_days_between](#trade_days_between)
  - [get_calendar_info](#get_calendar_info)
- [TradingCalendar 类](#tradingcalendar-类)
- [更新函数](#更新函数)
- [市场](#市场)
- [日期输入](#日期输入)
- [异常](#异常)
- [CLI：tjcal](#cli-tjcal)

## 安装

```bash
pip install tj-calendar
```

## 快速开始

```python
from datetime import date

from tj_calendar import is_trade_day, next_trade_day, trade_days_between

is_trade_day("2026-08-06")                 # True（工作日）
is_trade_day(date(2026, 8, 8))             # False（周六）
next_trade_day("2026-08-07")               # datetime.date(2026, 8, 10)

trade_days_between("2026-08-03", "2026-08-07")
# [date(2026,8,3), date(2026,8,4), date(2026,8,5), date(2026,8,6), date(2026,8,7)]
```

## 查询函数

所有查询函数签名一致：第一个参数是日期，`market` 默认 `"CN_A_SHARE"`，底层按市场 `lru_cache`，重复查询无额外开销。

### is_trade_day

```python
def is_trade_day(value: DateInput, market: str = "CN_A_SHARE") -> bool
```

`value` 是否为交易日。

```python
from tj_calendar import is_trade_day

is_trade_day("2026-08-06")            # True
is_trade_day("2026-08-08")            # False
is_trade_day("2026-10-01")            # False（国庆节）
is_trade_day(20260806)                # True（int 格式）
```

### next_trade_day

```python
def next_trade_day(value: DateInput, market: str = "CN_A_SHARE") -> date
```

`value` **之后**的第一个交易日。`value` 本身是交易日也不返回自身。范围末尾无更晚交易日抛 [`CalendarRangeError`](#异常)。

```python
from tj_calendar import next_trade_day

next_trade_day("2026-08-07")  # date(2026, 8, 10)（跨周末）
next_trade_day("2026-08-06")  # date(2026, 8, 7)
```

### prev_trade_day

```python
def prev_trade_day(value: DateInput, market: str = "CN_A_SHARE") -> date
```

`value` **之前**的最后一个交易日。范围开头无更早交易日抛 [`CalendarRangeError`](#异常)。

```python
from tj_calendar import prev_trade_day

prev_trade_day("2026-08-10")  # date(2026, 8, 7)
prev_trade_day("2026-08-08")  # date(2026, 8, 7)（周六→周五）
```

### trade_days_between

```python
def trade_days_between(start: DateInput, end: DateInput, market: str = "CN_A_SHARE") -> list[date]
```

闭区间 `[start, end]` 内的全部交易日，升序。`start > end` 抛 [`CalendarRangeError`](#异常)。

```python
from tj_calendar import trade_days_between

trade_days_between("2026-10-01", "2026-10-09")
# 仅含节后交易日；升序返回
```

### get_calendar_info

```python
def get_calendar_info(market: str = "CN_A_SHARE") -> dict
```

返回市场日历元信息。

```python
from tj_calendar import get_calendar_info

get_calendar_info()
# {
#   "market": "CN_A_SHARE",
#   "coverage_start": "1990-12-19",
#   "coverage_end": "2035-12-31",
#   "trade_day_count": 11584,
# }
```

## TradingCalendar 类

需要复用同一市场上下文或自定义市场时使用类接口；方法等价于顶层函数。

```python
from tj_calendar.calendar import TradingCalendar

cal = TradingCalendar.load("SSE")
cal.market                 # "SSE"
cal.is_trade_day("2026-08-06")
cal.next_trade_day("2026-08-07")
cal.trade_days_between("2026-08-03", "2026-08-07")
cal.info()                 # 同 get_calendar_info()
```

| 方法 | 说明 |
| --- | --- |
| `TradingCalendar.load(market)` / `TradingCalendar(market)` | 构造并加载 |
| `.market` | 市场名 |
| `.is_trade_day(value)` / `.next_trade_day(value)` / `.prev_trade_day(value)` | 同顶层函数 |
| `.trade_days_between(start, end)` | 同顶层函数 |
| `.info()` | 同 `get_calendar_info()` |

## 更新函数

查询数据是包内置的；要让日历保持最新，需要显式触发在线更新。**更新源不内置**，必须通过环境变量配置：

```bash
export TIANJI_CALENDAR_METADATA_URL="https://<bucket>.cos.<region>.myqcloud.com/tj-publish/calendar/metadata.json"
# 或镜像列表（冒号分隔）
export TIANJI_CALENDAR_MIRROR_URLS="https://<url1>:https://<url2>"
```

更新流程：先拉小体积 `metadata.json`（版本 + sha256 + bundle URL）→ 版本一致则跳过 → 否则下载 bundle、校验 sha256、原子替换。失败不破坏当前可用数据。

```python
from tj_calendar import check_for_update, ensure_fresh, update_calendar

# 只检查，不下载
check_for_update()
# {"calendar_version": "...", "bundle_url": "...", "sha256": "...",
#  "local_version": "...", "remote_version": "...", "update_needed": False}

# 按需更新：版本一致返回 updated=False
update_calendar()
# {"updated": False, "reason": "already up to date", ...}

# 查询前保证最新：已最新时静默、开销仅为拉 metadata
ensure_fresh()
```

| 函数 | 说明 |
| --- | --- |
| `check_for_update(metadata_urls=None)` | 拉 metadata，返回含 `update_needed` 的 dict；未配置源或全部镜像失败抛 [`CalendarUpdateError`](#异常) |
| `update_calendar(metadata_urls=None)` | 按需下载 + sha256 校验 + 原子替换，返回状态 dict |
| `ensure_fresh(metadata_urls=None)` | 保证最新，已最新静默；适合每次查询前调用 |

`metadata_urls` 参数可覆盖环境变量；本地数据路径：`~/.tianji/calendar/`（受 `TIANJI_HOME` 影响）。

## 市场

| market | coverage_start | coverage_end |
| --- | --- | --- |
| `CN_A_SHARE`（默认） | 1990-12-19 | 2035-12-31 |
| `SSE` | 1990-12-19 | 2035-12-31 |
| `SZSE` | 1990-12-19 | 2035-12-31 |
| `BSE` | 2021-11-15 | 2035-12-31 |

## 日期输入

`DateInput = str | date | int`：

| 类型 | 示例 | 说明 |
| --- | --- | --- |
| `str` | `"2026-08-06"` | ISO 格式 |
| `date` | `date(2026, 8, 6)` | datetime.date |
| `int` | `20260806` | YYYYMMDD |

非法输入抛 [`CalendarRangeError`](#异常)。

## 异常

| 异常 | 父类 | 触发条件 |
| --- | --- | --- |
| `TianjiCalendarError` | `Exception` | 本包异常基类 |
| `CalendarRangeError` | `TianjiCalendarError` | 日期超出市场覆盖范围；非法日期输入；`start > end`；范围边界无前/后交易日 |
| `CalendarDataError` | `TianjiCalendarError` | bundle 损坏/格式错误/校验失败 |
| `CalendarUpdateError` | `TianjiCalendarError` | 未配置更新源、镜像全部失败、sha256 不匹配 |

## CLI：tjcal

```bash
# 今天是否交易日
tjcal today
tjcal today --json

# 市场信息
tjcal info
tjcal info --market SSE --json

# 查询
tjcal check 2026-08-06
tjcal next 2026-08-07
tjcal prev 2026-08-10
tjcal range 2026-08-03 2026-08-07

# 更新
tjcal check-update
tjcal update
```

全部命令支持 `--market`（`CN_A_SHARE`/`SSE`/`SZSE`/`BSE`）与 `--json`。遇到本包异常输出 `error: <message>` 到 stderr 并返回 2。
