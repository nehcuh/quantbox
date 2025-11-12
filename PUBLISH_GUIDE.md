# PyPI 发布指南

## 准备工作

### 1. 注册账号

如果还没有 PyPI 账号：

**TestPyPI（测试环境）**：
- 注册：https://test.pypi.org/account/register/
- 用于测试上传，不会影响正式环境

**PyPI（正式环境）**：
- 注册：https://pypi.org/account/register/
- 用于正式发布

### 2. 生成 API Token

**TestPyPI**：
1. 登录 https://test.pypi.org
2. 进入 Account settings → API tokens
3. 点击 "Add API token"
4. Token name: `quantbox-cn-test`
5. Scope: 选择 "Entire account" 或特定项目
6. 复制生成的 token（格式：`pypi-...`）

**PyPI**：
1. 登录 https://pypi.org
2. 进入 Account settings → API tokens
3. 点击 "Add API token"
4. Token name: `quantbox-cn`
5. Scope: 选择 "Entire account"（首次上传）或 "Project: quantbox-cn"（后续更新）
6. 复制生成的 token

### 3. 配置 Token

创建 `~/.pypirc` 文件：

```bash
cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-YOUR-ACTUAL-TOKEN-HERE

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-YOUR-TEST-TOKEN-HERE
EOF

chmod 600 ~/.pypirc
```

## 发布流程

### 步骤 1：验证包（已完成 ✅）

```bash
uv run twine check dist/*
```

输出应该是 `PASSED`

### 步骤 2：上传到 TestPyPI

```bash
uv run twine upload --repository testpypi dist/*
```

### 步骤 3：测试安装

```bash
# 创建测试环境
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# 从 TestPyPI 安装
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ quantbox-cn

# 测试导入
python -c "from quantbox.services import MarketDataService; print('✅ 安装成功！')"

# 清理
deactivate
rm -rf test_env
```

### 步骤 4：上传到正式 PyPI

如果测试通过，上传到正式 PyPI：

```bash
uv run twine upload dist/*
```

### 步骤 5：验证正式发布

```bash
# 等待几分钟让 PyPI 同步

# 从正式 PyPI 安装
pip install quantbox-cn

# 测试
python -c "from quantbox.services import MarketDataService; print('✅ 发布成功！')"
```

## 发布后工作

### 1. 创建 Git 标签

```bash
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0
```

### 2. 创建 GitHub Release

1. 访问 https://github.com/curiousbull/quantbox/releases
2. 点击 "Draft a new release"
3. 选择标签 `v0.2.0`
4. Release title: `v0.2.0 - PyPI 首次发布`
5. 描述：复制 README.md 中的更新日志
6. 附加文件（可选）：
   - quantbox-cn-0.2.0-py3-none-any.whl
   - quantbox-cn-0.2.0.tar.gz
7. 点击 "Publish release"

### 3. 验证 PyPI 页面

访问：https://pypi.org/project/quantbox-cn/

检查：
- ✅ README 显示正确
- ✅ 版本号正确 (0.2.0)
- ✅ 依赖列表完整
- ✅ 分类标签正确
- ✅ 项目链接正确

### 4. 更新文档链接

确保 README.md 中的 PyPI badge 显示正确：

```markdown
[![PyPI Version](https://img.shields.io/pypi/v/quantbox-cn.svg)](https://pypi.org/project/quantbox-cn/)
```

## 常见问题

### Q: 上传失败，提示 "403 Forbidden"？

A: 检查：
- Token 是否正确配置在 `~/.pypirc`
- Token 权限是否足够（首次上传需要 "Entire account" 权限）
- Token 是否已过期

### Q: 包名已被占用？

A:
- 在 PyPI 搜索 "quantbox" 确认是否已存在
- 如果已存在，需要选择其他名称或联系原作者
- 如果是你自己的项目，使用对应项目的 Token

### Q: 上传后 README 显示不正确？

A:
- 确保 README.md 使用标准 Markdown 格式
- PyPI 支持的 Markdown 有限制，避免使用高级语法
- 可以用 `twine check` 验证 README 渲染

### Q: 如何更新已发布的包？

A:
1. 更新 `pyproject.toml` 中的版本号（如 `0.2.1`）
2. 重新构建：`uv build`
3. 验证：`uv run twine check dist/*`
4. 上传：`uv run twine upload dist/*`

**注意**：相同版本号不能重复上传，必须更新版本号

### Q: 如何删除已发布的版本？

A:
- PyPI 不支持删除已发布的版本
- 只能"yank"（标记为不推荐）：在 PyPI 项目页面操作
- 如果确实需要删除，联系 PyPI 支持团队

## 下次发布清单

- [ ] 更新版本号（pyproject.toml）
- [ ] 更新 CHANGELOG（README.md）
- [ ] 运行测试：`uv run pytest tests/`
- [ ] 清理构建产物：`rm -rf dist/ build/`
- [ ] 重新构建：`uv build`
- [ ] 验证包：`uv run twine check dist/*`
- [ ] 上传到 TestPyPI 测试
- [ ] 上传到正式 PyPI
- [ ] 创建 Git 标签
- [ ] 创建 GitHub Release
- [ ] 验证安装和功能

---

**祝发布顺利！** 🎉
