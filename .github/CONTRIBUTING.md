# 贡献指南

感谢您对 Quantbox 的关注！我们欢迎所有形式的贡献。

## 🤝 如何贡献

### 报告问题

如果您发现了 bug 或有功能建议，请：

1. 在 [Issues](https://github.com/nehcuh/quantbox/issues) 中搜索是否已有相关问题
2. 如果没有，创建新的 Issue，并提供：
   - 清晰的标题和描述
   - 复现步骤（如果是 bug）
   - 期望的行为
   - 实际的行为
   - 环境信息（Python 版本、操作系统等）
   - 相关的错误日志或截图

### 提交代码

#### 开发流程

1. **Fork 仓库**
   ```bash
   # 点击 GitHub 页面的 Fork 按钮
   git clone https://github.com/YOUR_USERNAME/quantbox.git
   cd quantbox
   ```

2. **创建开发环境**
   ```bash
   # 安装 uv（推荐）
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # 安装依赖
   uv sync --all-extras

   # 激活虚拟环境
   source .venv/bin/activate  # Linux/macOS
   # 或
   .venv\Scripts\activate     # Windows
   ```

3. **创建功能分支**
   ```bash
   git checkout -b feature/amazing-feature
   # 或
   git checkout -b fix/bug-description
   ```

4. **编写代码**
   - 遵循项目的编码规范（见 [docs/coding_standards.md](../docs/coding_standards.md)）
   - 添加必要的类型注解
   - 编写清晰的文档字符串
   - 确保代码通过 lint 检查

5. **编写测试**
   ```bash
   # 为新功能添加测试
   # 测试文件位于 tests/ 目录

   # 运行测试
   uv run pytest tests/ -v

   # 检查覆盖率
   uv run pytest tests/ --cov=quantbox --cov-report=html
   ```

6. **提交更改**
   ```bash
   git add .
   git commit -m "feat: 添加新功能描述"

   # 提交信息格式：
   # feat: 新功能
   # fix: 修复 bug
   # docs: 文档更新
   # test: 测试相关
   # refactor: 重构
   # perf: 性能优化
   # chore: 构建/工具链相关
   ```

7. **推送到您的 Fork**
   ```bash
   git push origin feature/amazing-feature
   ```

8. **创建 Pull Request**
   - 访问 GitHub 上的原仓库
   - 点击 "New Pull Request"
   - 选择您的分支
   - 填写 PR 描述，说明：
     - 改动的目的和动机
     - 测试情况
     - 相关的 Issue 编号（如有）

## 📋 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用 4 个空格缩进
- 最大行长度 100 字符
- 使用类型注解

```python
# ✅ 好的示例
def get_trade_calendar(
    exchanges: Optional[Union[str, List[str]]] = None,
    start_date: Optional[DateLike] = None,
    end_date: Optional[DateLike] = None,
) -> pd.DataFrame:
    """
    获取交易日历

    Args:
        exchanges: 交易所代码或列表
        start_date: 开始日期
        end_date: 结束日期

    Returns:
        交易日历数据
    """
    pass
```

### 文档字符串

- 使用 Google 风格的文档字符串
- 包含参数说明、返回值和示例（如适用）

### 测试要求

- 所有新功能必须有相应的测试
- 测试覆盖率应保持在 85% 以上
- 使用描述性的测试名称

```python
# ✅ 好的测试命名
def test_get_trade_calendar_returns_correct_columns():
    pass

def test_get_trade_calendar_filters_by_exchange():
    pass
```

## 🏗️ 架构原则

在贡献代码时，请遵循项目的三层架构：

1. **工具层（Utils）**
   - 纯函数，无状态
   - 可独立测试
   - 高度可复用

2. **适配器层（Adapters）**
   - 继承 `BaseDataAdapter`
   - 实现标准接口
   - 处理数据源特定逻辑

3. **服务层（Services）**
   - 编排适配器
   - 提供统一接口
   - 处理业务逻辑

详见 [架构文档](../docs/ARCHITECTURE.md)

## ✅ Pull Request 检查清单

提交 PR 前，请确保：

- [ ] 代码通过所有测试
- [ ] 添加了必要的测试用例
- [ ] 更新了相关文档
- [ ] 提交信息清晰且符合规范
- [ ] 代码通过 lint 检查
- [ ] 没有引入新的依赖（或已讨论）
- [ ] 向后兼容（或在 PR 中说明破坏性变更）

## 📝 文档贡献

文档改进同样重要！您可以：

- 修正文档中的错误
- 改进现有文档的清晰度
- 添加使用示例
- 翻译文档（如果需要）

## 💬 交流渠道

- **Issue 讨论**：技术问题和 bug 报告
- **Pull Request**：代码审查和讨论
- **Discussions**：功能建议和一般讨论

## 🙏 行为准则

- 尊重所有贡献者
- 接受建设性的批评
- 专注于对项目最有利的事情
- 对新手保持友好和耐心

## 📄 许可证

贡献的代码将采用与项目相同的 MIT 许可证。

---

再次感谢您的贡献！🎉
