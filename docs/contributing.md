# tj-calendar 项目开发约定

本文件是 tj-calendar 的硬性工程约定，所有贡献者必须遵守。

## 工具链

| 工具 | 约定 |
| --- | --- |
| Python | >=3.10 |
| 依赖管理 | uv（锁定文件 `uv.lock` 提交到仓库） |
| 代码格式化 | ruff format（单行最大 120 字符） |
| 静态检查 | ruff check（CI 失败阻断） |
| 类型检查 | pyright（via pre-commit，版本与 .pre-commit-config.yaml 对齐） |
| 测试 | pytest + pytest-cov + pytest-xdist |
| 预提交 | pre-commit，钩子顺序：ruff check → ruff format → pyright |

## 本地开发

```bash
uv sync --group dev
uv run pre-commit install
uv run pre-commit run --all-files
uv run ruff check .
uv run ruff format .
uv run pyright
uv run pytest -n auto --cov
```

## 轻量核心

本包核心保持轻量，不默认安装 pandas/numpy/pyarrow/akshare/LLM SDK。
可选能力通过 extras 提供，缺失时抛 `MissingDependencyError`。

## 合规

本项目仅用于研究和教育目的，不构成投资建议、交易信号或金融建议。

## 发布

打 `v*` tag 触发 GitHub Actions 发布到 PyPI（trusted publishing，无需 token）。
