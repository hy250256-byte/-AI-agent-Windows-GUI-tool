# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

圣瑞思智能服装吊挂系统（autotrans.exe，32 位 .NET WinForms）的自动化操作工具。单一 Python 文件 `autotrans_ops.py`，供 TS agent 通过 `execSync` 调用。

## 架构

单文件自包含。无外部依赖（除 pywinauto 和 Python 标准库）。

```
autotrans_ops.py
├── MAPPING  dict              # 控件映射表（50+ 条，文件内定义）
├── _locate(target)             # 公共查找：MAPPING → prerequisites → parent → find_elements → 返回 wrapper
│   ├── 映射命中               # name/automation_id/index 三选一定位，走 find_elements
│   └── 映射未命中             # 按 name 模糊搜索（用于 DataGridView 单元格如 "尺码 行 0"）
├── _check_error_dialog()      # click() 后检测 Win32 "提示"弹窗，有则读文本、关闭、抛异常
├── click(target)               # _locate.click_input() + 错误弹窗检测
├── input_text(target, value)   # _locate → click_input → Ctrl+A Backspace → type_keys
└── __name__ == "__main__"     # CLI 路由：python autotrans_ops.py click|input <target> [value]
```

## 运行环境

- **Python：** 必须是 32 位 Python 3.11（`C:\Python311-32\python.exe`），autotrans.exe 是 32 位进程
- **pywinauto backend：** 固定 uia（`find_elements` 必须传 `backend="uia"`，否则走 win32 后端炸 `rich_text`）
- **前提：** autotrans.exe 必须已启动并登录

## 常用命令

```bash
# CLI（需 autotrans.exe 运行中）
cd C:\Users\25025\autotrans_tool
C:\Python311-32\python.exe autotrans_ops.py click 制单信息
C:\Python311-32\python.exe autotrans_ops.py input 新制单号输入框 "121901"

# Grid 单元格（target 不在 MAPPING 中时按 name 搜索）
C:\Python311-32\python.exe autotrans_ops.py input "尺码 行 0" "M"

# 测试
C:/Python311-32/python.exe -m pytest tests/test_click.py -v
C:/Python311-32/python.exe -m pytest tests/test_click.py::TestClick::test_click_with_prerequisites -v
```

## MAPPING 控件定位字段

`_locate()` 按以下流程处理每条映射记录：

| 字段 | 作用 | 示例 |
|------|------|------|
| `name` | 传入 `find_elements(title=...)` | `"name": "查询"` |
| `automation_id` | 传入 `find_elements(auto_id=...)` | `"automation_id": "textBoxX1"` |
| `control_type` | 传入 `find_elements(control_type=...)` | `"control_type": "Button"` |
| `prerequisites` | 递归 `click()` 的前置导航链 | `"prerequisites": ["制单资料"]` |
| `parent` | 递归 `_locate(parent)`，将搜索范围缩小到父容器 | `"parent": "bar1"` |
| `index` | 不走 `find_elements`，直接用 `search.children()[index]` | `"index": 0` |

**注意：**

- `find_elements` 返回原始 `UIAElementInfo`，无 `click_input`，需要用 `registry.backends["uia"].generic_wrapper_class` 包装后才可操作
- **不使用 `_app.window()`** — 所有弹窗/子窗口都是 `Main:Nested`（嵌套在主窗口内），`_app.window()` 只能搜顶层窗口，永远找不到。统一用 `find_elements(top_level_only=False)`
- **不使用 `dialog` 字段** — 已废弃，弹窗控件改用 `parent` 链递归定位
- **不使用 `child_window`** — DevExpress NavBarControl 虚影子项导致多匹配报错
- **`find_elements` 不传 `parent`** — 传了会改变返回元素的上下文，导致 `type_keys` 击键路由失败（DataGridView 单元格接不到键盘输入）

## 添加新控件

1. 用 Inspect.exe (UIA 模式) 采集 Name / AutomationId / ControlType
2. 在 `autotrans_ops.py` 的 `MAPPING` dict 中添加条目
3. 带 `prerequisites` 的控件确保前置依赖已注册
4. 弹窗内控件用 `parent` 指向弹窗条目，不要用 `dialog`
5. 运行 `tests/test_click.py` 验证（注：测试 mock 了 pywinauto，与当前代码实现有差异，主要靠手工测试）
6. 同步更新 `C:\Users\25025\.agents\skills\autotrans\SKILL.md`

## 控件采集参考

`C:\Users\25025\.agents\skills\autotrans\references\control-map.md` 含完整的 Inspect.exe 采集记录（各页面控件层级、AutomationId、工具栏布局对比）。

## 设计约束

- **agent 不接触 pywinauto** — 只传业务名，所有定位在 `_locate` 内部
- **stdout 是唯一输出** — `{"ok": true}` 或 `{"ok": false, "error": "..."}`
- **失败即抛异常** — CLI 入口 catch 后输出 JSON 错误，不内部重试
- **无状态跨进程** — 每次 CLI 调用是独立进程，不保持状态（如 grid 上下文标记不可行）
- **回退 name 搜索** — target 不在 MAPPING 时自动当控件 Name 搜索，无需为每个 DataGridView 单元格建映射
