

1. 项目概述

1.1 项目名称





母品牌：Tianji



子项目：tj-calendar



展示名：Tianji Calendar



Python 包名：tj-calendar



Python 模块名：tj_calendar



CLI 命令：tjcal

1.2 品牌定位

Tianji 取“一窥天机”之意，定位为面向个人投资研究、量化研究和市场数据分析的开源工具生态。

子项目统一采用 tj-* 前缀，例如：

tj-calendar   交易日历
tj-symbols    证券代码标准化
tj-data       数据适配与缓存
tj-factors    因子与技术指标
tj-metrics    绩效指标
tj-backtest   轻量回测
tj-research   AI 辅助研究
tj-terminal   综合研究工作台

1.3 一句话定位

Tianji Calendar 是一个离线优先的中国市场交易日历工具。

英文定位：

Tianji Calendar is an offline-first China market trading calendar for Python.

1.4 项目角色

tj-calendar 是 Tianji 生态的第一个基础模块，后续可被以下项目复用：





tj-data：判断行情数据日期是否为交易日。



tj-backtest：推进回测交易日期。



tj-factors：对齐时间序列与因子计算窗口。



tj-terminal：展示市场状态与交易日信息。



2. 核心目标与非目标

2.1 核心目标





离线可用：安装后无需联网即可查询交易日历。



结果可靠：使用预生成、校验过的交易日列表，不临时推断。



市场绑定：交易日历必须与市场绑定，例如 CN_A_SHARE、SSE、SZSE、BSE。



API 简洁：提供稳定、直观的 Python API。



CLI 友好：提供适合脚本和终端使用的命令行工具。



可更新：后续支持用户显式导入或在线更新日历包。



可生态化：作为 Tianji 后续子项目的基础依赖。

2.2 非目标

MVP 阶段不做：





不做股票行情数据。



不做策略回测。



不做自动交易。



不做荐股或预测。



不在普通查询时联网。



不要求用户提供 Tushare token。



不让普通用户直接从 AkShare、Tushare、交易所网页生成日历。



3. 核心原则

3.1 离线优先

所有查询 API 默认只读取本地数据，不发起网络请求。

例如：

from tj_calendar import is_trade_day, next_trade_day
​
is_trade_day("2026-08-04")
next_trade_day("2026-08-04")

这些调用必须在完全无网络环境下可用。

3.2 显式更新

只有用户主动执行更新或导入命令时，才改变本地日历数据。

例如：

tjcal import calendar-bundle.json
tjcal update

普通查询绝不自动联网。

3.3 不猜测超范围日期

如果日期超出某个市场的覆盖范围，应抛出明确异常，而不是基于工作日规则猜测。

示例：

CalendarRangeError: 2036-01-05 is outside CN_A_SHARE calendar range 2000-01-01 to 2035-12-31.

对于市场成立前日期，也应该抛出异常，而不是返回 False。

例如查询北交所成立前日期：

is_trade_day("2018-01-02", market="BSE")

应该抛出：

CalendarRangeError: 2018-01-02 is outside BSE calendar range 2021-11-15 to 2035-12-31.

这样可以避免混淆两种情况：





这一天不是交易日。



这个市场当时不存在或数据不覆盖。

3.4 数据版本独立于代码版本

代码包版本和日历数据版本分开管理。

例如：

package_version: 0.1.0
calendar_version: 2026.08.04
coverage_start: 2000-01-01
coverage_end: 2035-12-31

3.5 单一权威数据包

tj-calendar 不应让普通用户从多个原始数据源各自生成日历。

应采用：

单一权威 calendar-bundle.json + 多个分发镜像

而不是：

多个数据源分别生成用户本地日历

AkShare、Tushare、交易所公告等只用于维护者侧生成和交叉校验，不作为普通用户运行时数据源。



4. 市场维度设计

4.1 为什么交易日要与市场绑定

交易日历必须绑定市场，原因包括：





北交所成立较晚，不能套用 2000 年以来的 A 股整体日历。



沪深北交易所未来可能存在局部差异。



不同市场交易时段可能不同。



未来扩展港股、美股、期货、基金等市场时需要统一模型。

4.2 MVP 市场规划

MVP 默认实现：

CN_A_SHARE   中国 A 股整体日历

数据结构从第一版开始预留：

SSE          上海证券交易所
SZSE         深圳证券交易所
BSE          北京证券交易所

4.3 API 市场参数

从第一版开始，API 应支持 market 参数，默认值为 CN_A_SHARE。

is_trade_day("2026-08-04")
is_trade_day("2026-08-04", market="CN_A_SHARE")
is_trade_day("2026-08-04", market="BSE")

CLI 也预留市场参数：

tjcal check 2026-08-04
tjcal check 2026-08-04 --market CN_A_SHARE
tjcal check 2026-08-04 --market BSE

4.4 市场覆盖范围

每个市场都应有自己的覆盖范围。

例如：

CN_A_SHARE: 2000-01-01 ~ 2035-12-31
SSE:        2000-01-01 ~ 2035-12-31
SZSE:       2000-01-01 ~ 2035-12-31
BSE:        2021-11-15 ~ 2035-12-31



5. 数据设计

5.1 为什么存交易日列表

A 股交易日历不适合只靠规则推断，原因包括：





春节、国庆等长假每年不同。



存在调休。



存在临时休市。



交易所安排可能变化。



历史数据需要可复现。

因此应直接存储最终交易日列表。

5.2 数据覆盖范围

MVP 建议内置：

2000-01-01 ~ 2035-12-31

对于成立较晚的市场，例如 BSE，应使用该市场实际可覆盖起始日期。

5.3 数据包格式

权威数据包文件名：

calendar-bundle.json

示例结构：

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
        "2026": [20260102, 20260105, 20260106]
      }
    },
    "SSE": {
      "name": "Shanghai Stock Exchange",
      "coverage_start": "2000-01-01",
      "coverage_end": "2035-12-31",
      "years": {
        "2026": [20260102, 20260105, 20260106]
      }
    },
    "SZSE": {
      "name": "Shenzhen Stock Exchange",
      "coverage_start": "2000-01-01",
      "coverage_end": "2035-12-31",
      "years": {
        "2026": [20260102, 20260105, 20260106]
      }
    },
    "BSE": {
      "name": "Beijing Stock Exchange",
      "coverage_start": "2021-11-15",
      "coverage_end": "2035-12-31",
      "years": {
        "2021": [20211115, 20211116]
      }
    }
  },
  "special_closures": [
    {
      "date": 20200203,
      "market": "CN_A_SHARE",
      "reason": "COVID-19 extended Spring Festival holiday"
    }
  ],
  "sources": [
    {
      "name": "manual",
      "description": "Maintained calendar data verified against public exchange schedules"
    }
  ]
}

5.4 日期格式

内部数据建议使用整数：

20260804

优点：





比字符串更紧凑。



易排序。



易做集合查找。



便于未来压缩。

对外 API 建议接受：

YYYY-MM-DD 字符串
datetime.date
datetime.datetime
YYYYMMDD 整数，可选

对外返回建议使用 datetime.date，CLI 输出 ISO 字符串。



6. 数据加载策略

6.1 数据位置

包内置数据：

src/tj_calendar/data/calendar-bundle.json

用户本地数据：

~/.tianji/calendar/calendar-bundle.json

推荐使用品牌目录：

~/.tianji/
  calendar/
  data/
  config.toml

6.2 加载优先级

查询时的数据优先级：

1. 用户本地导入或更新的数据
2. tj-calendar 内置基础数据
3. 超范围报错

未来如果有独立数据包，可扩展为：

1. 用户本地导入或更新的数据
2. tj-calendar-data 数据包
3. tj-calendar 内置基础数据
4. 超范围报错

6.3 数据损坏处理

如果用户本地数据损坏：





不应导致工具完全不可用。



应回退到包内置数据。



CLI 可输出 warning。



API 可通过诊断接口暴露当前使用的数据来源。



7. Python API 设计

7.1 顶层函数

MVP 核心 API：

from tj_calendar import (
    is_trade_day,
    next_trade_day,
    prev_trade_day,
    trade_days_between,
    get_calendar_info,
)

is_trade_day("2026-08-04", market="CN_A_SHARE")
next_trade_day("2026-08-04", market="CN_A_SHARE")
prev_trade_day("2026-08-04", market="CN_A_SHARE")
trade_days_between("2026-08-01", "2026-08-31", market="CN_A_SHARE")
get_calendar_info()

7.2 对象接口

高级用户可使用对象接口：

from tj_calendar import TradingCalendar

cal = TradingCalendar.load(market="CN_A_SHARE")

cal.is_trade_day("2026-08-04")
cal.next_trade_day("2026-08-04")
cal.prev_trade_day("2026-08-04")
cal.trade_days_between("2026-08-01", "2026-08-31")
cal.info()

未来可扩展为：

from tj_calendar import get_calendar

cn = get_calendar("CN_A_SHARE")
bse = get_calendar("BSE")

7.3 交易时间 API

交易时间判断放到后续版本。

可能 API：

is_market_open(market="CN_A_SHARE")
is_trading_time(market="CN_A_SHARE")
current_session(market="CN_A_SHARE")

A 股基础交易时段：

09:30 - 11:30
13:00 - 15:00

集合竞价、收盘集合竞价等细节后续再做，避免 MVP 复杂化。



8. CLI 设计

8.1 命令清单

命令行工具名：

tjcal

MVP 命令：

tjcal today
tjcal check <date>
tjcal next <date>
tjcal prev <date>
tjcal range <start> <end>
tjcal info

后续命令：

tjcal import <file>
tjcal update

8.2 示例

tjcal check 2026-08-04

输出：

2026-08-04 is a trading day.

tjcal next 2026-10-01

输出：

2026-10-09

tjcal info

输出：

Tianji Calendar
Package version: 0.1.0
Calendar version: 2026.08.04
Market: CN_A_SHARE
Timezone: Asia/Shanghai
Coverage: 2000-01-01 ~ 2035-12-31
Data mode: bundled

8.3 JSON 输出

后续可支持：

tjcal check 2026-08-04 --json

输出：

{
  "date": "2026-08-04",
  "is_trade_day": true,
  "market": "CN_A_SHARE"
}



9. 异常设计

建议定义清晰异常：

class TianjiCalendarError(Exception):
    pass

class CalendarRangeError(TianjiCalendarError):
    pass

class CalendarDataError(TianjiCalendarError):
    pass

class CalendarUpdateError(TianjiCalendarError):
    pass

常见错误：





CalendarRangeError：日期超出指定市场覆盖范围。



CalendarDataError：数据文件格式错误、损坏或校验失败。



CalendarUpdateError：导入或在线更新失败。



10. 在线更新与分发设计

10.1 设计原则

用户侧只消费 Tianji 官方发布的权威日历包。

不要让普通用户直接使用：

tjcal update --source akshare
tjcal update --source tushare
tjcal update --source sse

这些数据源只用于维护者生成和交叉校验。

用户侧采用：

单一权威数据包 + 多个分发镜像

10.2 为什么不能只放 GitHub

国内用户访问 GitHub Release 或 raw GitHub 经常不稳定，因此 GitHub 不能作为唯一更新源。

同时，也不应要求用户指定 pip 安装源作为主要更新方式，因为这会增加用户使用门槛。

10.3 国内对象存储方案

推荐使用国内对象存储作为 official 更新源，例如：





阿里云 OSS



腾讯云 COS



华为云 OBS



七牛云 Kodo



又拍云 USS

对象存储托管文件：

metadata.json
calendar-bundle.json
calendar-bundle.json.sha256

用户执行：

tjcal update

工具默认访问 official 对象存储 URL。

10.4 多对象存储备份

可以配置多个对象存储作为备份镜像。

这些镜像不是多个数据源，而是同一份权威 bundle 的多个下载通道。

示例：

腾讯云 COS:
https://tj-calendar-xxx.cos.ap-shanghai.myqcloud.com/tj-calendar/latest/metadata.json

阿里云 OSS:
https://tj-calendar-xxx.oss-cn-shanghai.aliyuncs.com/tj-calendar/latest/metadata.json

华为云 OBS:
https://tj-calendar-xxx.obs.cn-east-3.myhuaweicloud.com/tj-calendar/latest/metadata.json

tjcal update 内部逻辑：

尝试第一个 official mirror
  失败 -> 尝试第二个 mirror
  失败 -> 尝试第三个 mirror
  失败 -> 提示用户使用 tjcal import

10.5 不急于使用自定义域名

MVP 不需要自定义域名。

可以先使用对象存储默认域名，降低成本和备案复杂度。

如果未来使用大陆区域对象存储加自定义域名或 CDN，大概率需要 ICP 备案。

10.6 本地导入

必须支持本地导入：

tjcal import ./calendar-bundle.json

适用场景：





企业内网。



用户无法访问官方源。



私有部署。



离线环境。

10.7 在线更新失败处理

更新失败时：





不替换旧数据。



保留当前可用日历。



输出明确错误。



建议用户使用 tjcal import。



11. 对象存储安全设计

11.1 public-read 是否允许别人上传

对象存储设置为 public-read 时，匿名用户通常只能下载文件，不能上传文件。

含义：

允许 GetObject
不允许 PutObject
不允许 DeleteObject
不允许 ListBucket

因此，正常配置下，别人不能往 bucket 上传文件，也不能通过上传文件制造费用。

真正危险的是：





误设为 public-write。



AccessKey 泄露。



发布子账号权限过大。

11.2 权限建议





Bucket 绝不能设置为 public-write。



匿名用户只允许读取指定对象或指定前缀。



不开放目录列表能力。



上传权限只给 CI/CD 或发布专用子账号。



发布子账号只允许写入 tj-calendar/* 前缀。



AccessKey 不进入代码仓库。



AccessKey 只放在 CI/CD secret 或本地安全环境。

11.3 费用风险

主要费用风险不是别人上传，而是公开文件被大量下载，产生公网流量费用。

建议设置：





云账户余额告警。



单日流量告警。



单月预算告警。



Bucket 请求量告警。



可选访问限速。



可选生命周期规则清理旧版本。

tj-calendar 文件很小，正常使用成本应很低，但仍需防止异常流量。



12. 镜像发布方式

12.1 版本化路径

不要只维护：

/latest/calendar-bundle.json

推荐使用版本化路径：

/tj-calendar/v2026.12.20/calendar-bundle.json
/tj-calendar/v2026.12.20/calendar-bundle.json.sha256
/tj-calendar/latest/metadata.json

12.2 metadata.json

metadata.json 指向具体版本文件。

示例：

{
  "schema_version": 1,
  "calendar_version": "2026.12.20",
  "bundle_id": "tj-calendar-2026.12.20",
  "sha256": "abc123...",
  "bundle_url": "https://example-bucket/tj-calendar/v2026.12.20/calendar-bundle.json",
  "generated_at": "2026-12-20T10:00:00+08:00"
}

多个对象存储中的 metadata.json 可以使用不同域名，但必须指向同一个版本、同一个 sha256。

12.3 发布流程

推荐发布流程：

1. 生成 calendar-bundle.json
2. 生成 calendar-bundle.json.sha256
3. 上传到各对象存储的版本目录
4. 分别下载回来校验 sha256
5. 确认所有镜像可用
6. 最后更新各平台 /latest/metadata.json

这样可以避免用户下载到半发布状态的数据。



13. 维护者数据生成策略

13.1 维护者侧数据源

维护者可以使用多个来源生成和校验日历：





交易所公开休市安排公告。



中国政府节假日安排。



AkShare 数据。



Tushare 数据。



人工修订文件。

但这些不直接暴露给普通用户作为更新源。

13.2 校验策略

发布前应校验：





schema 版本正确。



每个市场日期在覆盖范围内。



每年交易日有序。



每年交易日不重复。



普通交易日不落在周六周日。



特殊休市记录格式正确。



calendar_version 合法。



bundle hash 正确。

13.3 修正版数据

如果发现数据错误，应发布新的 calendar_version，而不是静默覆盖旧版本。

例如：

2026.12.20
2026.12.21



14. 项目结构建议

tj-calendar/
  README.md
  pyproject.toml
  LICENSE
  src/
    tj_calendar/
      __init__.py
      calendar.py
      loader.py
      update.py
      cli.py
      errors.py
      types.py
      data/
        calendar-bundle.json
  tests/
    test_calendar.py
    test_loader.py
    test_cli.py
    test_update.py
  scripts/
    build_calendar.py
    validate_calendar.py
    publish_bundle.py
  docs/
    data-format.md
    update-policy.md

模块职责：

calendar.py        核心日历查询逻辑
loader.py          加载内置数据和用户数据
update.py          导入、在线更新、校验、原子替换
cli.py             命令行入口
errors.py          异常类型
types.py           类型定义
build_calendar.py  维护者侧生成日历包
validate_calendar.py 维护者侧校验日历包
publish_bundle.py  发布 bundle 到对象存储镜像



15. 测试策略

15.1 核心查询测试





判断交易日。



判断非交易日。



查询前一个交易日。



查询后一个交易日。



查询区间交易日。



查询范围边界。



超范围日期抛错。



市场成立前日期抛错。

15.2 数据测试





calendar-bundle.json schema 正确。



markets 字段存在。



每个市场有独立覆盖范围。



每年交易日有序。



每年交易日不重复。



所有日期在覆盖范围内。



特殊休市记录格式正确。

15.3 CLI 测试





tjcal check



tjcal next



tjcal prev



tjcal range



tjcal info



tjcal --json



tjcal --market

15.4 更新与导入测试





本地导入成功。



schema 不兼容时导入失败。



sha256 校验失败时导入失败。



在线更新失败时保留旧数据。



远端版本低于本地时不更新。



多 mirror fallback 行为正确。



16. README 建议

README 首屏：

# Tianji Calendar

Offline-first China market trading calendar for Python.

Tianji Calendar is part of the Tianji open-source market research toolkit.
It works without network access at runtime and provides simple APIs for trading day queries.

核心卖点：

## Features

- Offline-first, no network required at runtime
- Market-aware trading calendar model
- Built-in China A-share trading calendar
- Trading day, previous day, next day, and range queries
- Simple Python API and CLI
- Explicit import and update workflow
- No Tushare token required

免责声明：

## Disclaimer

This project is for research and educational purposes only.
It does not provide investment advice, trading signals, or financial recommendations.



17. 版本规划

v0.1.0





内置基础日历数据。



支持 market 参数，默认 CN_A_SHARE。



支持 is_trade_day。



支持 next_trade_day。



支持 prev_trade_day。



支持 trade_days_between。



支持 get_calendar_info。



支持 tjcal check / next / prev / range / info。



不做在线更新。

v0.2.0





支持 tjcal import calendar-bundle.json。



支持本地导入数据优先。



支持 bundle schema 校验。



支持 sha256 校验。



导入失败时保留旧数据。

v0.3.0





支持 tjcal update。



默认访问一个 official 对象存储源。



支持 metadata + 版本化 bundle。



支持在线更新失败回滚。

v0.4.0





支持多个对象存储 mirror fallback。



仍然只分发同一份权威 bundle。



支持 mirror 级别健康检查。

v1.0.0





API 稳定。



数据格式稳定。



导入和更新机制稳定。



文档完善。



被 Tianji 其他子项目复用。



18. 风险与应对

18.1 日历数据错误

应对：





不用规则推断。



发布前运行数据校验。



维护特殊休市记录。



发现错误后发布新的数据版本。

18.2 国内用户访问 GitHub 困难

应对：





不把 GitHub 作为唯一更新源。



支持对象存储 official 源。



支持多个对象存储备份。



支持本地导入。

18.3 多镜像一致性问题

应对：





多镜像只分发同一份权威 bundle。



使用 sha256 校验内容一致性。



使用版本化路径，不静默覆盖历史版本。



发布流程先上传版本文件，再更新 latest metadata。

18.4 对象存储费用风险

应对：





只开启 public-read，不开启 public-write。



设置预算、流量、请求量告警。



只放公开小文件。



发布账号最小权限。

18.5 用户误以为是投资建议

应对：





项目定位为基础工具。



README 加免责声明。



不提供荐股、预测、收益承诺。



文案避免 profit、guaranteed alpha 等词。



19. 最终决策摘要





母品牌为 Tianji，子项目使用 tj-* 前缀。



第一个项目为 tj-calendar，展示名为 Tianji Calendar。



项目定位为离线优先的中国市场交易日历工具。



查询 API 不联网，更新必须显式触发。



交易日历必须与 market 绑定。



MVP 默认市场为 CN_A_SHARE，数据结构预留 SSE、SZSE、BSE。



北交所等成立较晚市场必须有独立覆盖起始日期。



超出市场覆盖范围时抛出异常，不做猜测。



使用预生成交易日列表，不用节假日规则临时推断。



普通用户只消费 Tianji 官方权威 bundle。



AkShare、Tushare、交易所公告只作为维护者侧数据生成和校验来源。



数据分发采用单一权威 bundle + 多个镜像。



不把 GitHub 作为唯一更新源。



可使用国内对象存储作为 official 源，后续配置多个对象存储备份。



Bucket 可以 public-read，但绝不能 public-write。



必须支持本地导入，解决内网和离线环境。



MVP 保持小而硬，优先做到稳定、离线、可信、可复用。


