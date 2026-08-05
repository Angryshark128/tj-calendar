# Tianji Calendar 设计文档

> 本文档描述 tj-calendar 的当前设计与实现状态，与代码保持一致。文末附有与早期设计稿的差异说明。

## 1. 项目概述

### 1.1 项目名称

- 母品牌：Tianji
- 子项目：tj-calendar
- 展示名：Tianji Calendar
- Python 包名：tj-calendar
- Python 模块名：tj_calendar
- CLI 命令：tjcal

### 1.2 项目定位

Tianji Calendar 是一个离线优先的中国市场交易日历工具。

**英文定位**：Offline-first China market trading calendar for Python.

**中文定位**：离线优先的中国市场交易日历工具。

### 1.3 在 Tianji 生态中的角色

tj-calendar 是 Tianji 生态的基础模块，后续可被以下项目复用：

- tj-data：判断行情数据日期是否为交易日
- tj-backtest：推进回测交易日期
- tj-factors：对齐时间序列与因子计算窗口
- tj-terminal：展示市场状态与交易日信息

### 1.4 核心目标

- **离线可用**：安装后无需联网即可查询交易日历
- **结果可靠**：使用预生成、校验过的交易日列表，不临时推断
- **市场绑定**：交易日历与市场绑定（CN_A_SHARE / SSE / SZSE / BSE）
- **API 简洁**：稳定的 Python API
- **CLI 友好**：适合脚本和终端使用的命令行工具
- **可更新**：通过 metadata 预校验显式更新，数据版本与代码版本分离
- **可生态化**：作为 Tianji 后续子项目的基础依赖

### 1.5 非目标（MVP）

- 不做股票行情数据
- 不做策略回测
- 不做自动交易
- 不做荐股或预测
- 普通查询不联网
- 不要求用户提供 Tushare token
- 不让普通用户直接从 AkShare / Tushare / 交易所网页生成日历（那是维护者侧的事）

---

## 2. 核心原则

### 2.1 离线优先

所有查询 API 默认只读取本地数据，不发起网络请求：

```python
from tj_calendar import is_trade_day, next_trade_day

is_trade_day("2026-08-04")
next_trade_day("2026-08-04")
```

这些调用必须在完全无网络环境下可用。

### 2.2 显式更新

只有用户主动执行更新命令时才改变本地日历数据：

```bash
tjcal check-update   # 只拉取 metadata.json，判断是否需要更新
tjcal update         # 版本一致跳过；不一致才下载完整 bundle
```

普通查询绝不自动联网。Python 侧使用 `ensure_fresh()` 在每次调用前保证数据最新。

### 2.3 不猜测超范围日期

如果日期超出某市场覆盖范围，抛出明确异常，不基于工作日规则猜测：

```
CalendarRangeError: 2036-01-05 is outside CN_A_SHARE calendar range 2000-01-01 to 2035-12-31.
```

对市场成立前的日期同样抛异常（例如 BSE 于 2021-11-15 成立前）：

```
CalendarRangeError: 2018-01-02 is outside BSE calendar range 2021-11-15 to 2035-12-31.
```

这样区分两种情况：这一天不是交易日（返回 False）；该市场当时不存在或数据不覆盖（抛异常）。

### 2.4 数据版本独立于代码版本

代码包版本（如 `0.1.0`）与日历数据版本（如 `2026.08.04`）分开管理。

### 2.5 单一权威数据包

普通用户只消费 Tianji 官方发布的权威 bundle（calendar-bundle.json）。AkShare、Tushare、交易所公告只用于维护者侧生成与交叉校验，不作为普通用户运行时数据源。

### 2.6 更新源可配置，不内置默认地址

代码不硬编码更新源 URL。用户必须显式配置：

- `TIANJI_CALENDAR_METADATA_URL`：单个 metadata URL
- `TIANJI_CALENDAR_MIRROR_URLS`：冒号分隔的多镜像列表（可选）

未配置时 `tjcal update` 报清晰错误并提示如何配置。

---

## 3. 市场维度设计

### 3.1 为什么交易日要与市场绑定

- 北交所成立较晚，不能套用 2000 年以来的 A 股整体日历
- 沪深北交易所未来可能存在局部差异
- 未来扩展港股、美股、期货、基金等市场时需统一模型

### 3.2 MVP 市场

- `CN_A_SHARE`：中国 A 股整体日历（默认）
- `SSE`：上海证券交易所
- `SZSE`：深圳证券交易所
- `BSE`：北京证券交易所

### 3.3 市场覆盖范围

| 市场 | coverage_start | coverage_end |
| --- | --- | --- |
| CN_A_SHARE | 2000-01-01 | 2035-12-31 |
| SSE | 2000-01-01 | 2035-12-31 |
| SZSE | 2000-01-01 | 2035-12-31 |
| BSE | 2021-11-15 | 2035-12-31 |

### 3.4 API 市场参数

API 从第一版支持 `market` 参数，默认 `CN_A_SHARE`：

```python
is_trade_day("2026-08-04")
is_trade_day("2026-08-04", market="CN_A_SHARE")
is_trade_day("2026-08-04", market="BSE")
```

CLI 也支持：

```bash
tjcal check 2026-08-04 --market BSE
```

---

## 4. Python API

### 4.1 顶层函数

```python
from tj_calendar import (
    is_trade_day,
    next_trade_day,
    prev_trade_day,
    trade_days_between,
    get_calendar_info,
    check_for_update,
    update_calendar,
    ensure_fresh,
)
```

| 函数 | 说明 |
| --- | --- |
| `is_trade_day(value, market=...)` | 判断是否交易日，返回 bool |
| `next_trade_day(value, market=...)` | 下一个交易日，返回 date |
| `prev_trade_day(value, market=...)` | 上一个交易日，返回 date |
| `trade_days_between(start, end, market=...)` | 区间交易日列表，含两端 |
| `get_calendar_info(market=...)` | 日历元信息（覆盖范围、交易日数） |
| `check_for_update(metadata_urls=None)` | 拉取远端 metadata，返回是否需更新 |
| `update_calendar(metadata_urls=None)` | 按需下载并应用更新（sha256 校验） |
| `ensure_fresh(metadata_urls=None)` | 调用前保证数据最新，静默跳过已最新 |

### 4.2 对象接口

```python
from tj_calendar.calendar import TradingCalendar

cal = TradingCalendar.load(market="CN_A_SHARE")
cal.is_trade_day("2026-08-04")
cal.next_trade_day("2026-08-04")
cal.prev_trade_day("2026-08-04")
cal.trade_days_between("2026-08-01", "2026-08-31")
cal.info()
```

`TradingCalendar` 内部按市场缓存（`lru_cache`），重复加载同一市场复用已解析数据。

### 4.3 日期输入与输出

查询 API 接受三种日期输入：

- ISO 字符串：`"2026-08-04"`
- `datetime.date`
- `YYYYMMDD` 整数：`20260804`

返回 `datetime.date`。

---

## 5. CLI 设计

### 5.1 命令清单

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

`--market` 与 `--json` 可放在子命令前或后。

### 5.2 示例

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
# coverage_start: 2000-01-01
# coverage_end: 2035-12-31
# trade_day_count: 9226

tjcal check 2025-10-01 --json
# {"date": "2025-10-01", "is_trade_day": false, "market": "CN_A_SHARE"}
```

### 5.3 更新命令

```bash
tjcal check-update   # 输出 update available / already up to date
tjcal update         # 输出 calendar updated / already up to date
```

---

## 6. 更新机制

### 6.1 设计目标

- **先校验再下载**：只拉取几百字节的 metadata.json，版本一致则不下载完整 bundle
- **sha256 校验**：下载内容必须与 metadata 声明的 sha256 一致，否则拒绝
- **原子替换**：`os.replace` 写入，失败时保留现有数据，绝不破坏当前可用日历

### 6.2 流程

```
tjcal update
  │
  ├─ 1. 读取本地版本（本地 metadata → 本地 bundle → 内置 bundle）
  ├─ 2. 拉取远端 metadata.json（版本 + sha256 + bundle_url）
  ├─ 3. 版本一致 → 跳过下载，输出 "already up to date"
  ├─ 4. 版本不一致 → 下载 bundle
  ├─ 5. 校验 sha256（不一致 → 拒绝并保留旧数据）
  ├─ 6. 结构校验（calendar_version / markets 合法）
  └─ 7. 原子替换本地 bundle + 写本地 metadata.json
```

### 6.3 配置

更新源由环境变量配置，不内置默认地址：

```bash
export TIANJI_CALENDAR_METADATA_URL="https://<bucket>.cos.<region>.myqcloud.com/calendar/latest/metadata.json"
# 可选：多镜像
export TIANJI_CALENDAR_MIRROR_URLS="https://mirror-a/.../metadata.json:https://mirror-b/.../metadata.json"
```

未配置时报错：

```
error: no update source configured; set TIANJI_CALENDAR_METADATA_URL to the metadata.json URL (or TIANJI_CALENDAR_MIRROR_URLS for mirrors)
```

### 6.4 Python 侧保证数据最新

```python
from tj_calendar import ensure_fresh, is_trade_day

ensure_fresh()   # 数据已最新时静默跳过，仅拉 metadata
is_trade_day("2026-08-04")
```

---

## 7. 数据设计

### 7.1 为什么存交易日列表而非规则推断

A 股交易日历不适合只靠规则推断：

- 春节、国庆等长假每年不同
- 存在调休
- 存在临时休市（如 2020 疫情延长）
- 交易所安排可能变化
- 历史数据需要可复现

因此直接存储最终交易日列表。

### 7.2 覆盖范围

内置 `2000-01-01 ~ 2035-12-31`。BSE 自 2021-11-15 起。

### 7.3 数据包格式

文件名：`calendar-bundle.json`。顶层结构：

```json
{
  "schema_version": 1,
  "calendar_version": "2026.08.04",
  "bundle_id": "tj-calendar-2026.08.04",
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-08-04T00:00:00+08:00",
  "markets": {
    "CN_A_SHARE": {
      "name": "China A-share market",
      "coverage_start": "2000-01-01",
      "coverage_end": "2035-12-31",
      "years": {
        "2026": [20260803, 20260804, 20260805]
      }
    },
    "SSE": { "...": "同 CN_A_SHARE" },
    "SZSE": { "...": "同 CN_A_SHARE" },
    "BSE": {
      "coverage_start": "2021-11-15",
      "years": { "2021": [20211115, 20211116] }
    }
  },
  "special_closures": [
    {
      "date": 20200131,
      "market": "CN_A_SHARE",
      "reason": "COVID-19 extended Spring Festival holiday"
    }
  ],
  "sources": [
    {
      "name": "manual",
      "description": "Encoded public exchange holiday schedules for 2019-2027; ..."
    },
    {
      "name": "akshare_sina",
      "description": "Trade days for published years fetched from AkShare ...; years: 2019, 2020, ..."
    }
  ]
}
```

### 7.4 日期格式

- 内部：整数 `20260804`（紧凑、易排序、易查找）
- 对外 API：`datetime.date`
- CLI 输出：ISO 字符串

### 7.5 数据来源

内置 bundle 由 `scripts/build_calendar.py` 生成，两种模式：

- **offline（默认）**：内置权威节假日清单（2019-2027）+ 其余年份工作日近似
- **--fetch**：合并 AkShare（新浪接口）已公布年份的真实交易日，覆盖近似值

`bundle.sources` 记录数据来源与年份，保证可追溯。

---

## 8. 数据加载与存储

### 8.1 数据位置

- 包内置：`src/tj_calendar/data/calendar-bundle.json`
- 用户本地：`~/.tianji/calendar/calendar-bundle.json`
- 本地 metadata：`~/.tianji/calendar/metadata.json`

配置目录可经 `TIANJI_HOME` 覆盖（默认 `~/.tianji`）。

### 8.2 加载优先级

1. 用户本地导入/更新的数据
2. tj-calendar 内置基础数据
3. 超范围报错

### 8.3 数据损坏处理

本地数据损坏时回退到内置数据并发出 `warnings.warn`，不导致工具不可用。

---

## 9. 异常设计

```
TianjiCalendarError
├── CalendarRangeError    日期超出市场覆盖范围
├── CalendarDataError     数据文件格式错误/损坏/校验失败
└── CalendarUpdateError   导入或在线更新失败
```

---

## 10. 维护者侧：数据生成与发布

### 10.1 数据生成（scripts/build_calendar.py）

- 内置节假日清单编码在脚本中（2019-2027）
- `--fetch` 时从 AkShare 拉已公布年份交易日，**裁剪到覆盖窗口内**（AkShare 数据可能回溯到 1990 年），仅保留 `[2000-01-01, 2035-12-31]` 内日期
- `sources` 标注每份数据的来源与年份

### 10.2 数据校验（scripts/validate_calendar.py）

发布前检查：

- schema_version / calendar_version / bundle_id 一致
- 每个市场日期在覆盖范围内
- 每年交易日有序、不重复
- 日期不落在周末
- BSE 不早于成立日
- sources 非空

### 10.3 发布（scripts/publish.py）

自动化发布流程：

1. 构建 bundle（可选 --fetch 合并 AkShare）
2. 本地校验
3. 生成版本化 artifacts 与 metadata
4. 检查远端：版本+sha256 一致则跳过（幂等）
5. 上传版本目录 `calendar/v<version>/`
6. 拉回远端 bundle 对比 sha256 验证上传
7. 最后更新 `calendar/latest/metadata.json`

**latest 指针最后更新**，避免用户下载到半发布状态。

### 10.4 COS 配置

发布脚本的 COS 配置全部走环境变量：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TIANJI_COS_BUCKET` | tj-1310342032 | bucket 名 |
| `TIANJI_COS_REGION` | ap-beijing | 区域 |
| `TIANJI_COS_PREFIX` | calendar | bucket 内键前缀 |
| `TIANJI_COS_SECRET_ID` | — | 腾讯云 SecretId |
| `TIANJI_COS_SECRET_KEY` | — | 腾讯云 SecretKey |

密钥必须存在，缺失时报错并退出。上传子账号应使用最小权限（仅 `calendar/` 前缀写入）。

### 10.5 自动发布（GitHub Actions）

`.github/workflows/publish-calendar.yml`：

- 每天 02:00 UTC（北京时间 10:00）定时触发，也可手动 `workflow_dispatch`
- 安装 extras（akshare + cos sdk）到同一环境
- 运行 `python scripts/publish.py --fetch`
- 数据无变化时幂等跳过，不重复上传
- 密钥从 GitHub Secrets 注入：`COS_SECRET_ID` / `COS_SECRET_KEY`

---

## 11. 可选依赖与 extras

核心包零第三方运行时依赖（仅标准库）。

| Extra | 用途 | 命令 |
| --- | --- | --- |
| `[akshare]` | 维护者侧实时拉取交易日 | `pip install tj-calendar[akshare]` |
| `[cos]` | 发布上传 COS | `pip install tj-calendar[cos]` |

普通用户安装 `tj-calendar` 即含完整内置数据，无需任何 extra。

---

## 12. 项目结构

```
tj-calendar/
  pyproject.toml
  README.md / README.en.md
  LICENSE / CHANGELOG.md / CONTRIBUTING.md / CODE_OF_CONDUCT.md
  .editorconfig / .gitignore / .pre-commit-config.yaml
  pyrightconfig.json
  .github/
    workflows/
      ci.yml                  lint + type + test 矩阵
      release.yml             PyPI 发布
      publish-calendar.yml    每日 COS 自动发布
    ISSUE_TEMPLATE/
    PULL_REQUEST_TEMPLATE.md
  docs/
    design.md                 本文档
    contributing.md           开发约定
    data-format.md            数据格式
  releases/
    v2026.08.04/              versioned bundle + sha256 + metadata
    latest/metadata.json      最新 metadata（供 tjcal update 拉取）
  scripts/
    build_calendar.py         构建 bundle（offline / --fetch）
    validate_calendar.py      发布前校验
    publish.py                COS 发布流水线
  src/tj_calendar/
    __init__.py               顶层 API 导出
    calendar.py               核心查询（TradingCalendar + 顶层函数）
    loader.py                 数据加载与优先级
    update.py                 更新机制（metadata 预校验 + sha256）
    cli.py                    tjcal 命令行
    types.py                  类型定义（MarketCalendar）
    errors.py                 异常
    data/calendar-bundle.json 内置数据
  tests/
    test_calendar.py          查询测试
    test_update.py            更新机制测试（mock 远端）
```

---

## 13. 测试策略

### 13.1 核心查询

- 判断交易日/非交易日
- 已知节假日休市（2019-2027）
- 前后交易日、区间、边界
- 超范围抛 `CalendarRangeError`
- 市场成立前抛错（BSE）
- 三种日期输入形式

### 13.2 更新机制（mock HTTP 服务器）

- 版本一致 → 不下载 bundle（验证"先校验再下载"）
- 版本不一致 → 下载、校验 sha256、原子替换
- 连续同版本 → 幂等跳过
- sha256 不匹配 → 拒绝、保留旧数据
- 下载失败 → 保留旧数据
- 全镜像失败 → 抛 `CalendarUpdateError`
- 更新后查询使用新数据（缓存清理）

---

## 14. 与早期设计稿的差异

早期设计稿与当前实现的主要差异：

1. **在线更新提前落地**：早期 v0.1.0 不含在线更新（planned v0.3）。当前 v0.1.0 已实现 `tjcal update` / `ensure_fresh`，采用 metadata 预校验。
2. **`tjcal import` 未实现**：本地导入留待后续版本。
3. **不内置默认更新源 URL**：早期文档预设官方对象存储地址；当前改为环境变量必填，避免占位符泄漏。
4. **AkShare 合并进发布流水线**：早期文档仅列 AkShare 为维护者参考；当前 `--fetch` 自动拉取已公布年份并裁剪到覆盖窗口。
5. **数据来源可追溯**：`bundle.sources` 记录 manual / akshare_sina 及年份。
6. **发布流水线脚本化**：`build → validate → publish` 全流程脚本化，并支持 GitHub Actions 定时执行。
7. **COS 前缀可配置**：`TIANJI_COS_PREFIX`，默认 `calendar`。

---

## 15. 版本规划

- **v0.1.0（当前）**：内置日历、market 查询、CLI、metadata 预校验更新、发布流水线
- **v0.2.0**：`tjcal import calendar-bundle.json`（本地导入）
- **v0.3.0**：多镜像 fallback 完善、mirror 健康检查
- **v1.0.0**：API 稳定、数据格式稳定、导入/更新机制稳定、被生态其他子项目复用

---

## 16. 风险与应对

| 风险 | 应对 |
| --- | --- |
| 日历数据错误 | 不用规则推断；发布前自动校验；数据版本独立可修正 |
| 国内访问 GitHub 困难 | COS 作为 official 更新源；不把 GitHub 作为唯一源 |
| COS 密钥泄露 | 子账号最小权限（仅 calendar/ 前缀）；密钥走 GitHub Secrets |
| COS 写权限失败 | publish.py 上传后拉回比对 sha256，失败不更新 latest |
| 用户误以为是投资建议 | README 免责声明；定位为基础工具 |
| 未公布年份数据不准 | sources 标注 best-effort；每年节假日公布后自动更新 |
