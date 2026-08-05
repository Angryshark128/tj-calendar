# tj-calendar 数据维护

面向维护者的日历数据格式、构建、校验与发布指南。普通用户无需阅读本文。

## 数据格式

`calendar-bundle.json` 顶层结构：

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

### markets

每个市场的键值：

```json
"CN_A_SHARE": {
  "name": "China A-share market",
  "coverage_start": "1990-12-19",
  "coverage_end": "2035-12-31",
  "years": { "2026": [20260803, 20260804, 20260805] }
}
```

- 日期整数 `YYYYMMDD`（如 `20260804`）
- 每年内**有序**、**不重复**、**不落在周末**
- 全部在 `[coverage_start, coverage_end]` 内

| market | 名称 | coverage_start |
| --- | --- | --- |
| CN_A_SHARE | China A-share market | 1990-12-19 |
| SSE | Shanghai Stock Exchange | 1990-12-19 |
| SZSE | Shenzhen Stock Exchange | 1990-12-19 |
| BSE | Beijing Stock Exchange | 2021-11-15 |

### special_closures

非节假日规则内的临时休市：

```json
[
  {
    "date": 20200131,
    "market": "CN_A_SHARE",
    "reason": "COVID-19 extended Spring Festival holiday"
  }
]
```

### sources

数据来源记录，保证可追溯。**以国家公布的节假日安排为权威**，AkShare 负责融合与交叉验证：

- `manual`：国家/交易所公布的节假日清单（2019-2027），人工编码核对
- `akshare_sina`：AkShare 新浪接口拉取的交易日，与官方清单交叉验证

AkShare 不是唯一来源，只作为融合验证手段。

## 构建（scripts/build_calendar.py）

两种模式：

```
uv run python scripts/build_calendar.py          # offline：内置清单 + 工作日近似
uv run python scripts/build_calendar.py --fetch  # 合并 AkShare 已公布年份
```

- 内置节假日清单编码在脚本 `HOLIDAYS` 中（2019-2027），以国家公布为准人工核对
- `--fetch` 从 AkShare 拉已公布年份交易日，**与官方清单交叉验证**后合并，**裁剪到 `[1990-12-19, 2035-12-31]`**，仅保留窗口内日期
- 已公布年份用真实数据覆盖近似值；未公布年份回退内置/best-effort
- 结果写入 `src/tj_calendar/data/calendar-bundle.json`

依赖：`pip install tj-calendar[akshare]`。

## 校验（scripts/validate_calendar.py）

发布前检查：

- schema_version / calendar_version / bundle_id 一致
- 每个市场日期在覆盖范围内
- 每年交易日有序、不重复
- 日期不落在周末
- BSE 不早于 2021-11-15
- sources 非空

```
uv run python scripts/validate_calendar.py [bundle-path]
```

## 发布（scripts/publish.py）

自动化发布流程：

1. 构建 bundle（`--fetch` 可选合并 AkShare）
2. 本地校验
3. 生成版本化 artifacts 与 metadata
4. 检查远端：版本+sha256 一致则跳过（**幂等**）
5. 上传版本目录 `calendar/v<version>/`
6. 拉回远端 bundle 对比 sha256 验证上传
7. **最后更新** `calendar/latest/metadata.json`（避免用户下到半发布状态）

```
uv run python scripts/publish.py --fetch     # 真实发布
uv run python scripts/publish.py --dry-run   # 仅构建+校验，不上传
```

依赖：`pip install tj-calendar[cos]`。

### COS 配置（环境变量）

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `TIANJI_COS_BUCKET` | tj-1310342032 | bucket 名 |
| `TIANJI_COS_REGION` | ap-beijing | 区域 |
| `TIANJI_COS_PREFIX` | calendar | bucket 内键前缀 |
| `TIANJI_COS_SECRET_ID` | — | 腾讯云 SecretId（必填） |
| `TIANJI_COS_SECRET_KEY` | — | 腾讯云 SecretKey（必填） |

密钥必填，缺失时报错退出。建议子账号最小权限（仅 `calendar/` 前缀写入）。

## 自动发布（GitHub Actions）

`.github/workflows/publish-calendar.yml`：

- 每天 02:00 UTC（北京时间 10:00）定时触发，也可手动 `workflow_dispatch`
- 安装 extras（`uv sync --extra akshare --extra cos`）到同一环境
- 运行 `uv run python scripts/publish.py --fetch`
- 数据无变化时幂等跳过
- 密钥从 GitHub Secrets 注入：`COS_SECRET_ID` / `COS_SECRET_KEY`

仓库变量：`COS_BUCKET` / `COS_REGION` / `COS_PREFIX` / `ENABLE_CALENDAR_PUBLISH`。

## 数据更新节奏

A 股节假日由国务院**每年年底公布下一年**。因此：

- 数据**一年发布 1-2 次**（新年份公布后）
- 用户侧每天可 `ensure_fresh()` 检查，但只拉几百字节 metadata，版本不变则跳过
- 未公布年份（2028+）保持 best-effort，公布后自动更新
