# tj-calendar 数据格式

> 仅当模块涉及数据文件时使用。非数据模块可删除本文件。

## 版本约定

数据版本独立于代码版本。

```
package_version: 0.1.0
data_version:    YYYY.MM.DD
```

## 数据位置

- 包内置数据：`src/tj_calendar/data/`
- 用户本地数据：`~/.tianji/<module>/`

## 加载优先级

1. 用户本地数据
2. 包内置数据
3. 超范围报错
