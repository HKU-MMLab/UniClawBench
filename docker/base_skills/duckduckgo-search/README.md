# 🦆 DuckDuckGo Search Skill for OpenClaw

使用 DuckDuckGo 进行隐私保护的网页搜索，**无需 API Key**。支持关键信息提取和 AI 总结。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![OpenClaw](https://img.shields.io/badge/OpenClaw-Skill-blue)](https://openclaw.ai)
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg)](https://github.com/cscsxx606/duckduckgo-search-openclaw)

---

## ✨ 特性

- 🔍 **无需 API Key** - 开箱即用
- 🛡️ **隐私保护** - DuckDuckGo 不追踪用户
- 🇨🇳 **中文支持** - HTML 模式支持中文搜索
- 📊 **关键信息总结** - 自动提取和总结
- 📰 **来源分析** - 识别信息来源
- 🏷️ **实体提取** - 人名、地名、组织名
- 💾 **备份搜索** - 当 Tavily 不可用时使用

---

## 🚀 快速开始

### 安装

```bash
# 克隆到 OpenClaw skills 目录
cd ~/.openclaw/workspace/skills
git clone https://github.com/cscsxx606/duckduckgo-search-openclaw.git
```

### 使用

```bash
# 基本搜索
python3 duckduckgo-search-openclaw/scripts/duckduckgo_search.py "搜索关键词"

# 带关键信息总结
python3 duckduckgo-search-openclaw/scripts/duckduckgo_search.py "伊朗局势" --summarize

# 指定结果数量
python3 duckduckgo-search-openclaw/scripts/duckduckgo_search.py "AI 新闻" -n 10

# JSON 输出
python3 duckduckgo-search-openclaw/scripts/duckduckgo_search.py "API" --json
```

---

## 📖 功能说明

### 1. 关键信息总结

使用 `--summarize` 参数自动生成结构化摘要：

```bash
python3 scripts/duckduckgo_search.py "伊朗战争最新消息" --summarize
```

**输出示例**:
```
📋 关键信息摘要
============================================================

🔍 搜索主题：伊朗战争最新消息

📰 信息来源 (5 个):
   • www.bbc.com
   • news.qq.com
   • m.guancha.cn
   • www.cna.com.tw
   • cn.nytimes.com

📊 结果概览:
   共找到 5 条相关信息
   主要关注点:
   - 美伊開戰
   - 伊朗局势最新动态
   - 美国以色列联手攻击伊朗
```

### 2. 信息来源分析

自动识别并统计媒体来源，帮助判断信息权威性。

### 3. 关键实体提取

提取人名、地名、组织名等关键实体。

### 4. 时间信息识别

识别多种日期格式，快速了解事件时间线。

---

## 📊 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `query` | 搜索关键词（必需） | - |
| `-n, --top-k` | 返回结果数量 | 5 |
| `--mode` | 搜索模式：`instant` / `html` | `html` |
| `--summarize` | 生成关键信息总结 | false |
| `--json` | 输出原始 JSON | false |

---

## 🎯 使用场景

### ✅ 推荐使用

- 临时搜索（无需配置 API）
- 隐私敏感搜索
- 中文搜索
- 备份搜索方案

### ❌ 不推荐

- 生产环境（稳定性要求高）
- 批量搜索（可能触发反爬）
- 高质量需求（建议用 Tavily）

---

## 🧪 测试结果

| 测试项 | 结果 | 说明 |
|--------|------|------|
| 中文搜索 | ✅ 通过 | HTML 模式 |
| 关键信息提取 | ✅ 通过 | --summarize |
| 来源分析 | ✅ 通过 | 自动识别 |
| 实体提取 | ✅ 通过 | 正则匹配 |
| 日期识别 | ✅ 通过 | 多种格式 |
| 响应时间 | ✅ <2 秒 | 包含总结 |

---

## 📁 项目结构

```
duckduckgo-search-openclaw/
├── scripts/
│   └── duckduckgo_search.py    # 主脚本
├── SKILL.md                     # 技能文档
├── FEATURES.md                  # 功能说明
├── CODE_REVIEW.md               # 代码审查
├── TEST_REPORT.md               # 测试报告
├── PUBLISH_GUIDE.md             # 发布指南
├── package.json                 # NPM 包信息
├── skill.json                   # ClawHub 元数据
├── LICENSE                      # MIT 许可证
└── .gitignore
```

---

## 🔧 技术实现

### 核心函数

- `search_instant()` - DuckDuckGo Instant API
- `search_html()` - HTML 端点搜索
- `extract_key_info()` - 关键信息提取
- `generate_summary()` - 生成总结
- `parse_html_results()` - 解析 HTML 结果
- `extract_real_url()` - URL 提取

### 依赖

- Python 3.x（标准库）
- 无需外部依赖

---

## 🆚 与 Tavily 搜索对比

| 特性 | DuckDuckGo | Tavily |
|------|------------|--------|
| **API Key** | ✅ 不需要 | ❌ 需要 |
| **成本** | ✅ 免费 | ✅ 免费额度 |
| **结果质量** | ⚠️ 一般 | ✅ 优秀（AI 总结） |
| **稳定性** | ⚠️ 中 | ✅ 高 |
| **适用场景** | 备份/临时 | 生产环境 |

---

## 📝 更新日志

### v1.1.0 (2026-03-12)

**新增**:
- ✅ 关键信息提取与总结
- ✅ 信息来源分析
- ✅ 关键实体提取
- ✅ 时间信息识别

**改进**:
- ✅ 默认模式改为 `html`
- ✅ 优化输出格式
- ✅ 修复语法警告

### v1.0.0 (2026-03-12)

- ✅ 初始版本
- ✅ 基本搜索功能
- ✅ 双模式支持

---

## ⚠️ 注意事项

1. **速率限制**: DuckDuckGo 可能限制大量请求，建议添加 2-5 秒间隔
2. **反爬虫**: HTML 模式可能被识别为爬虫，触发 403 错误
3. **API 限制**: Instant API 只返回"即时答案"，不是完整搜索
4. **中文支持**: Instant API 对中文支持差，建议使用 HTML 模式

---

## 📚 相关资源

- [OpenClaw 官方文档](https://docs.openclaw.ai)
- [ClawHub 技能市场](https://clawhub.ai)
- [DuckDuckGo](https://duckduckgo.com)
- [OpenClaw Discord 社区](https://discord.gg/clawd)

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

---

## 👤 作者

- **OpenClaw Community**
- GitHub: [@cscsxx606](https://github.com/cscsxx606)

---

## 🙏 致谢

- 感谢 [OpenClaw](https://openclaw.ai) 团队提供的平台
- 感谢 [DuckDuckGo](https://duckduckgo.com) 提供的搜索服务
- 感谢社区贡献者

---

**🔗 项目地址**: https://github.com/cscsxx606/duckduckgo-search-openclaw
