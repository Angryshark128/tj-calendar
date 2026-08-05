# tj-calendar 数据格式

本文档描述 `calendar-bundle.json` 的完整结构与约定，是设计文档的配套参考。

## 版本约定

数据版本与代码版本分离：

```
package_version: 0.1.0
calendar_version: 2026.08.04   # YYYY.MM.DD，随数据内容更新
```

## 顶层结构

```json
{
  "schema_version": 1,
  "calendar_version": "2026.08.04",
  "bundle_id": "tj-calendar-2026.08.04",
  "timezone": "Asia/Shanghai",
  "generated_at": "2026-08-04T00:00:00+08:00",
  "markets": { ... },
  "special_closures": [ ... ],
  "sources": [ ... ]
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| schema_version | int | bundle schema 版本，当前 1 |
| calendar_version | str | 数据版本 `YYYY.MM.DD` |
| bundle_id | str | `tj-calendar-<calendar_version>` |
| timezone | str | 市场时区，Asia/Shanghai |
| generated_at | str | 生成时间（ISO 8601） |
| markets | object | 各市场交易日数据，见下 |
| special_closures | array | 特殊休市记录 |
| sources | array | 数据来源（可追溯） |

## markets 结构

每个市场的键值：

```json
"CN_A_SHARE": {
  "name": "China A-share market",
  "coverage_start": "2000-01-01",
  "coverage_end": "2035-12-31",
  "years": {
    "2026": [20260803, 20260804, 20260805]
  }
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| name | str | 市场展示名 |
| coverage_start | str | 覆盖起始日期（ISO） |
| coverage_end | str | 覆盖结束日期（ISO） |
| years | object | 键为年份字符串，值为该年交易日整数数组 |

**years 约定**：
- 日期使用整数 `YYYYMMDD`（如 `20260804`）
- 每年内**有序**、**不重复**
- 不落在周末
- 全部在 `[coverage_start, coverage_end]` 内

## 市场清单

| market | 名称 | coverage_start |
| --- | --- | --- |
| CN_A_SHARE | China A-share market | 2000-01-01 |
| SSE | Shanghai Stock Exchange | 2000-01-01 |
| SZSE | Shenzhen Stock Exchange | 2000-01-01 |
| BSE | Beijing Stock Exchange | 2021-11-15 |

## special_closures

特殊休市（非节假日规则内的临时休市）：

```json
[
  {
    "date": 20200131,
    "market": "CN_A_SHARE",
    "reason": "COVID-19 extended Spring Festival holiday"
  }
]
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| date | int | 闭市日期 `YYYYMMDD` |
| market | str | 受影响市场 |
| reason | str | 休市原因 |

## sources

数据来源记录，保证可追溯：

```json
[
  {
    "name": "manual",
    "description": "Encoded public exchange holiday schedules for 2019-2027; ..."
  },
  {
    "name": "akshare_sina",
    "description": "Trade days for published years fetched from AkShare ...; years: 2019, 2020, ..."
  }
]
```

- `manual`：内置权威节假日清单
- `akshare_sina`：AkShare 新浪接口拉取的已公布年份

## 校验

发布前运行 `scripts/validate_calendar.py`，检查：版本一致、日期有序不重复、无周末、覆盖范围内、BSE 不早于成立日、sources 非空。
