# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

圣瑞思智能服装吊挂系统（autotrans.exe，32 位 .NET WinForms）的自动化操作工具。单一 Python 文件 `autotrans_ops.py`，供 TS agent 通过 `execSync` 调用。

## 架构

单文件自包含。无外部依赖（除 pywinauto 和 Python 标准库）。

```
autotrans_ops.py
├── MAPPING  dict            # 控件映射表（40+ 条，文件内定义）
├── _locate(target)           # 公共查找：prerequisites → 连接 → dialog/parent 范围 → find_elements → 返回 wrapper
├── click(target)             # 调 _locate.click_input()
├── input_text(target, value) # 调 _locate → click_input + type_keys
└── __name__ == "__main__"   # CLI 路由：python autotrans_ops.py click|input <target> [value]
```

## 运行环境

- **Python：** 必须是 32 位 Python 3.11（`C:\Python311-32\python.exe`），autotrans.exe 是 32 位进程
- **pywinauto backend：** 固定 uia（`find_elements` 必须传 `backend="uia"`，否则走 win32 后端炸 `rich_text`）
- **前提：** autotrans.exe 必须已启动并登录

## 常用命令

```bash
# CLI（需 autotrans.exe 运行中）
cd C:\Users\25025\autotrans_plugin
C:\Python311-32\python.exe autotrans_ops.py click 制单信息
C:\Python311-32\python.exe autotrans_ops.py input 制单号 "XHSJ3060912"

# 测试
C:/Python311-32/python.exe -m pytest tests/test_click.py -v

# 单个测试
C:/Python311-32/python.exe -m pytest tests/test_click.py::TestClick::test_click_with_prerequisites -v
```

## MAPPING 控件定位字段

`_locate()` 按以下流程处理每条映射记录：

| 字段 | 作用 | 示例 |
|------|------|------|
| `name` | 传入 `find_elements(title=...)` | `"name": "查询"` |
| `automation_id` | 传入 `find_elements(auto_id=...)` | `"automation_id": "FormInput"` |
| `control_type` | 传入 `find_elements(control_type=...)` | `"control_type": "Button"` |
| `prerequisites` | 递归 `click()` 的前置导航链 | `"prerequisites": ["制单资料"]` |
| `dialog` | 缩小搜索范围到弹窗（先 `_app.window(auto_id=...)`） | `"dialog": "FormInput"` |
| `parent` | 缩小搜索范围到父容器（先 `_locate(parent)`） | `"parent": "bar1"` |
| `index` | 不走 `find_elements`，直接用 `children()[index]` | `"index": 0` |

**注意：** `find_elements` 返回原始 `UIAElementInfo`，无 `click_input`。需要用 `registry.backends["uia"].generic_wrapper_class` 包装后才可操作。

## 添加新控件

1. 用 Inspect.exe (UIA 模式) 采集 Name / AutomationId / ControlType
2. 在 `autotrans_ops.py` 的 `MAPPING` dict 中添加条目
3. 带 `prerequisites` 的控件确保前置依赖已注册
4. 带 `dialog` 的控件确保弹窗 AutomationId 已注册
5. 运行 `tests/test_click.py` 验证
6. 同步更新 `C:\Users\25025\.agents\skills\autotrans\SKILL.md`

## 控件采集参考

`C:\Users\25025\.agents\skills\autotrans\references\control-map.md` 含完整的 Inspect.exe 采集记录（各页面控件层级、AutomationId、工具栏布局对比）。

## 设计约束

- **agent 不接触 pywinauto** — 只传业务名，所有定位在 `_locate` 内部
- **stdout 是唯一输出** — `{"ok": true}` 或 `{"ok": false, "error": "..."}`
- **失败即抛异常** — CLI 入口 catch 后输出 JSON 错误，不内部重试
- **不使用 `child_window`** — DevExpress NavBarControl 虚影子项导致多匹配报错，统一用 `find_elements` + 取第一个
- **`find_elements` 必须指定 `parent`** — 不带 `parent` 的 `find_elements` 会从桌面根节点遍历整个 UIA 树，控件树太复杂，返回数据量太大，性能极差。始终传入 `parent=_main_win` 限定搜索范围
