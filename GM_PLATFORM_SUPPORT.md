# 掘金量化平台支持说明

**更新日期**: 2025-11-11
**文档版本**: v1.0

---

## 平台支持概览

| 操作系统 | SDK支持 | 终端支持 | 推荐使用 | 备注 |
|---------|--------|---------|---------|------|
| **Windows** | ✅ 完全支持 | ✅ 完全支持 | ✅ 推荐 | 32位和64位都支持 |
| **Linux** | ⚠️ 部分支持 | ❌ 不支持 | ⚠️ 复杂 | 需连接Windows终端 |
| **macOS** | ❌ 不支持 | ❌ 不支持 | ❌ 不可用 | 官方明确不支持 |

---

## 详细说明

### Windows 平台 ✅

**支持情况**: 完全支持

**系统要求**:
- Windows 7/8/10/11
- 32位或64位系统都支持
- 终端仅支持64位系统

**安装方式**:
```bash
pip install gm -U -i https://mirrors.aliyun.com/pypi/simple/
```

**使用方式**:
```python
from quantbox.adapters.gm_adapter import GMAdapter

adapter = GMAdapter()
data = adapter.get_future_daily(
    symbols="SHFE.rb2501",
    start_date="2024-11-01",
    end_date="2024-11-08"
)
```

**优势**:
- 完整功能支持
- 可以运行掘金终端
- 所有API都可用
- 性能最佳

---

### Linux 平台 ⚠️

**支持情况**: SDK可安装，但功能受限

**限制**:
- 掘金终端**不支持Linux**
- SDK需要连接到Windows上运行的掘金终端
- 需要配置`serv_addr`为Windows机器的IP和端口

**配置方法**:
```python
from gm.api import set_serv_addr, set_token

# 连接到Windows上的掘金终端
set_serv_addr("192.168.1.100:7001")  # Windows机器IP
set_token("your_token_here")
```

**推荐方案**:
对于Linux用户，**强烈推荐使用Tushare**数据源，更简单高效：
```bash
uv run quantbox-async
# 默认使用Tushare，无需额外配置
```

---

### macOS 平台 ❌

**支持情况**: **完全不支持**

**原因**:
- 掘金官方SDK不提供macOS版本
- 掘金终端不支持macOS
- 官方文档明确说明不支持macOS

**代码中的检查**:
```python
# quantbox/adapters/gm_adapter.py
if platform.system() == 'Darwin':
    raise NotImplementedError(
        "掘金量化 API 不支持 macOS 系统。"
        "请使用其他数据源或在 Linux/Windows 上运行。"
    )
```

**替代方案**:
macOS用户**只能使用Tushare**数据源：
```bash
uv run quantbox-async
# 默认使用Tushare，功能完整
```

---

## Python版本支持

所有平台的Python版本要求（基于Windows平台）:

- ✅ Python 3.6.5+
- ✅ Python 3.7.*
- ✅ Python 3.8.*
- ✅ Python 3.9.*
- ✅ Python 3.10.*
- ✅ Python 3.11.*
- ✅ Python 3.12.*

**注意**: 掘金3.0版本不再支持Python 2.7

---

## 测试结果

### Windows 测试 ✅

**测试环境**:
- 操作系统: Windows 10.0.26100
- Python: Python 3.x
- GM SDK: 3.0.179

**测试结果**:
```
[PASS] GMAdapter 初始化成功
[PASS] 掘金 API 连接正常
[PASS] 下载期货日线数据成功 - 6条数据
```

### Linux 测试 ⚠️

未进行测试，理论上可以安装SDK但需要连接Windows终端。

### macOS 测试 ❌

**预期行为**:
```python
from quantbox.adapters.gm_adapter import GMAdapter

adapter = GMAdapter()
# 抛出异常: NotImplementedError: 掘金量化 API 不支持 macOS 系统
```

---

## 推荐使用方案

### 按平台推荐

| 平台 | 首选数据源 | 备选方案 | 说明 |
|------|-----------|---------|------|
| **Windows** | 掘金 或 Tushare | - | 两者都完全支持，可按需选择 |
| **Linux** | Tushare | 掘金（需配置） | Tushare更简单 |
| **macOS** | Tushare | - | 只能用Tushare |

### 按功能推荐

| 需求 | 推荐方案 | 平台要求 |
|------|---------|---------|
| 实时行情 | 掘金 | Windows |
| Tick数据 | 掘金 | Windows |
| 历史日线 | Tushare | 所有平台 |
| 分钟数据 | Tushare | 所有平台 |
| 跨平台 | Tushare | 所有平台 |

---

## 常见问题

### Q1: 为什么macOS不支持掘金？
**A**: 这是掘金官方的限制，官方SDK和终端都不提供macOS版本。

### Q2: Linux上可以用掘金吗？
**A**: 可以安装SDK，但需要连接到Windows上运行的掘金终端，配置复杂，不推荐。建议使用Tushare。

### Q3: quantbox支持哪些数据源？
**A**: quantbox支持多种数据源：
- **Tushare** - 所有平台都支持 ✅
- **掘金** - 仅Windows完全支持 ⚠️
- **本地数据库** - 所有平台都支持 ✅

### Q4: 如何在Shell中切换数据源？
**A**: 使用`set_adapter`命令：
```bash
quantbox-async> set_adapter gm        # 切换到掘金（仅Windows）
quantbox-async> set_adapter tushare   # 切换到Tushare
quantbox-async> show_adapter          # 查看当前数据源
```

### Q5: Tushare和掘金有什么区别？
**A**: 主要区别：

| 特性 | Tushare | 掘金 |
|------|---------|------|
| 平台支持 | 所有平台 | 仅Windows |
| 历史数据 | 丰富 | 丰富 |
| 实时行情 | 需权限 | 支持 |
| Tick数据 | 不支持 | 支持 |
| 分钟数据 | 支持 | 支持 |
| 免费额度 | 较多 | 较少 |

---

## 参考资料

- [掘金量化官网](https://www.myquant.cn/)
- [掘金SDK下载](https://www.myquant.cn/docs2/operatingInstruction/study/SDK下载及说明文档.html)
- [Tushare官网](https://tushare.pro/)
- [quantbox文档](https://github.com/your-repo/quantbox)

---

**文档维护**: Claude Code
**项目**: quantbox v0.2.0
**最后更新**: 2025-11-11
