# Tianji Calendar 设计

> 当前实现状态，与代码一致。

## 定位

离线优先的中国市场交易日历工具。Tianji 生态基础模块，被 tj-data / tj-backtest / tj-factors / tj-terminal 复用。

**核心原则**
1. **离线优先**：查询 API 不联网
2. **显式更新**：`check-update` / `update` / `ensure_fresh` 才触网
3. **不猜超范围**：日期超出市场覆盖范围抛 `CalendarRangeError`，不按工作日猜测
4. **数据/代码版本分离**：`calendar_version`（YYYY.MM.DD）独立于包版本
5. **单一权威 bundle**：普通用户只消费官方 `calendar-bundle.json`
6. **国家公布为准，AkShare 验证**：以国务院/交易所公布的节假日安排为权威数据源，AkShare 负责融合与交叉验证，不作为唯一来源
7. **更新源必配不内置**：`TIANJI_CALENDAR_METADATA_URL` / `TIANJI_CALENDAR_MIRROR_URLS`，未配报清晰错误

## 市场

| market | coverage_start | coverage_end |
| --- | --- | --- |
| CN_A_SHARE（默认） | 1990-12-19 | 2035-12-31 |
| SSE | 1990-12-19 | 2035-12-31 |
| SZSE | 1990-12-19 | 2035-12-31 |
| BSE | 2021-11-15 | 2035-12-31 |

## Python API

```python
is_trade_day(value, market="CN_A_SHARE") -> bool
next_trade_day(value, market) -> date
prev_trade_day(value, market) -> date
trade_days_between(start, end, market) -> list[date]
get_calendar_info(market) -> dict
check_for_update(metadata_urls=None) -> dict      # 拉 metadata，返回 update_needed
update_calendar(metadata_urls=None) -> dict       # 按需下载+sha256+原子替换
ensure_fresh(metadata_urls=None) -> dict          # 查询前保证最新，已最新静默
```

对象接口：`TradingCalendar.load(market)`，方法同顶层函数。按 market `lru_cache`。

日期输入：ISO 字符串 / `date` / `YYYYMMDD` 整数；返回 `date`。

## CLI

```
tjcal today|check|next|prev|range|info|check-update|update [--market M] [--json]
```

`--market` / `--json` 可放子命令前后。

## 更新机制

```
update → 读本地版本（local metadata→local bundle→bundled）
       → 拉远端 metadata.json（version+sha256+bundle_url）
       → 版本一致：跳过，不下载 bundle
       → 不一致：下载 → sha256 校验 → 结构校验 → os.replace 原子替换
```

失败（sha256 不匹配 / 下载失败）时保留旧数据，绝不破坏当前可用日历。

## 数据格式

`calendar-bundle.json`：顶层含 `schema_version / calendar_version / bundle_id / timezone / generated_at / markets / special_closures / sources`。`markets.<m>.years` 存整数日期 `YYYYMMDD`。`sources` 记录来源（manual / akshare_sina）可追溯。

完整规范见 **`docs/data-maintenance.md`**。

## 加载与存储

- 内置：`src/tj_calendar/data/calendar-bundle.json`
- 本地：`~/.tianji/calendar/{calendar-bundle.json, metadata.json}`，可用 `TIANJI_HOME` 覆盖
- 优先级：本地数据 > 内置数据；本地损坏回退内置并 `warnings.warn`

## 异常

```
TianjiCalendarError
├── CalendarRangeError    超范围
├── CalendarDataError     数据损坏
└── CalendarUpdateError   更新失败
```

## 数据维护

以国家公布的节假日安排为权威，AkShare 融合验证，构建 → 校验 → COS 发布 → GitHub Actions 自动发布：见 **`docs/data-maintenance.md`**。

## 项目结构

```
src/tj_calendar/  __init__ calendar loader update cli types errors data/
scripts/          build_calendar validate_calendar publish
docs/             design data-format data-maintenance
.github/workflows/ ci release publish-calendar
releases/         v<version>/ + latest/metadata.json
tests/            test_calendar test_update
```

## 与早期设计稿差异

1. 在线更新提前落地（原计划 v0.3 → v0.1.0）
2. `tjcal import` 未实现，留待后续
3. 不内置默认更新源 URL（环境变量必填）
4. AkShare 自动合并进发布流水线，并裁剪到覆盖窗口
5. `sources` 记录来源可追溯
6. 发布流水线脚本化 + GitHub Actions 定时 + 幂等
7. COS 前缀可配置（`TIANJI_COS_PREFIX`）

## 版本规划

- v0.1.0：内置日历、market 查询、CLI、metadata 预校验更新、发布流水线
- v0.2.0：`tjcal import`（本地导入）
- v0.3.0：多镜像 fallback 完善
- v1.0.0：API / 数据格式 / 更新机制稳定

## 风险与应对

| 风险 | 应对 |
| --- | --- |
| 数据错误 | 发布前自动校验；数据版本独立可修正 |
| 国内 GitHub 访问难 | COS 官方源，不依赖 GitHub 更新 |
| COS 密钥泄露 | 子账号最小权限，密钥走 Secrets |
| 写失败 | 上传后拉回比对 sha256，失败不更新 latest |
| 未公布年份不准 | sources 标 best-effort，公布后自动更新 |
