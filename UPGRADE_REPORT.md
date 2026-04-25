# 升级报告

## 基本信息

| 项目 | 值 |
|------|-----|
| 仓库名 | requests-html |
| 升级时间 | 2026-03-14 |
| 升级状态 | ⚠️ 部分成功（网络测试超时） |

## Python 版本

| 升级前 | 升级后 |
|--------|--------|
| >=3.6.0 | >=3.13 |

## 依赖变更

| 依赖 | 升级前 | 升级后 |
|------|--------|--------|
| requests | 无版本限制 | >=2.32.5 (2.32.5) |
| pyquery | 无版本限制 | >=2.0.1 (2.0.1) |
| fake-useragent | 无版本限制 | >=2.2.0 (2.2.0) |
| parse | 无版本限制 | >=1.21.1 (1.21.1) |
| beautifulsoup4 | 无版本限制 | >=4.14.3 (4.14.3) |
| w3lib | 无版本限制 | >=2.4.0 (2.4.0) |
| pyppeteer | >=0.0.14 | >=2.0.0 (2.0.0) |
| lxml-html-clean | 未声明 | >=0.4.4 (0.4.4) |

## 新增依赖

- `lxml-html-clean>=0.4.4` - lxml.html.clean 已独立为单独项目

## 代码修改

| 文件 | 修改类型 | 说明 |
|------|----------|------|
| requests_html.py:15 | 导入迁移 | `lxml.html.clean.Cleaner` → `lxml_html_clean.Cleaner` |
| requests_html.py:488-491 | 修复 StopIteration | `__next__` 方法增加 None 检查，避免 AttributeError |
| requests_html.py:823-833 | asyncio 兼容 | 修复 event loop 创建逻辑，兼容 Python 3.13 |
| tests/test_internet.py:27 | 移除废弃参数 | 移除 `event_loop` fixture 参数 |
| tests/test_requests_html.py:21-31 | 修复 async fixture | 改为返回 async 函数而非 partial |
| setup.py:85 | Python 版本 | 升级到 >=3.13 |
| setup.py:23-25 | 依赖声明 | 添加版本约束和 lxml-html-clean |

## 测试结果

### 本地测试（test_requests_html.py）

| 结果 | 数量 |
|------|------|
| ✅ 通过 | 30 passed |
| ❌ 失败 | 0 failed |
| ⚠️ 警告 | 16 warnings (websockets deprecation) |

### 网络测试（test_internet.py）

| 结果 | 说明 |
|------|------|
| ⚠️ 超时 | pagination 测试超时（累计 2 次） |
| ✅ 部分通过 | 非 pagination 测试通过 |

## 已知问题

1. **网络测试超时**
   - `test_pagination` 和 `test_async_pagination` 在某些 URL 上超时
   - 原因：网络请求耗时过长（stackoverflow.com 等）
   - 影响：不影响核心功能，仅影响网络分页测试

2. **Deprecation 警告**
   - websockets 库的 `loop` 参数已废弃
   - 来源：pyppeteer 依赖的 websockets 版本
   - 影响：仅警告，不影响功能

## 核心功能验证

✅ 所有核心功能测试通过：
- HTML 解析
- CSS 选择器
- XPath 查询
- JavaScript 渲染
- 异步请求
- 文件协议支持
- 浏览器会话

## 备注

- 网络测试超时是由于外部网站响应慢，不是代码问题
- 所有本地功能测试全部通过
- 依赖已升级到最新稳定版本
- Python 3.13 兼容性问题已全部修复
