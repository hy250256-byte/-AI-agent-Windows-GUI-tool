# autotrans-ops

供 AI agent 使用的 Windows GUI 操作工具。用于没有 API 接口的软件，通过业务名驱动控件操作，agent 不接触底层自动化细节。

## 解决的问题

传统软件没有 API，agent 只能自己写 pywinauto 代码探索控件树——反复猜控件名、定位失败、重试，耗时长且易出错。

autotrans-ops 将控件属性提前采集为映射表，agent 只传"业务名"（如 `查询`、`另存为`），工具内部一步定位执行，返回 `{"ok": true/false}`。

## 环境

- Windows
- Python 3.11 **32-bit**（目标软件为 32 位进程时必须同位）
- pywinauto

```bash
pip install pywinauto
```

## 使用

```bash
python autotrans_ops.py click <业务名>
python autotrans_ops.py input <业务名> <值>
```

每次调用返回 JSON：

```json
{"ok": true}
{"ok": false, "error": "找不到控件: xxx"}
```

## 核心设计

**MAPPING** — 控件映射表。预先用 Inspect.exe (UIA 模式) 采集每个控件的定位属性，存为 dict。

```python
MAPPING = {
    "查询":   {"name": "查询",   "control_type": "Button"},
    "制单号": {"parent": "bar1", "control_type": "Edit", "index": 0},
}
```

支持字段：

| 字段 | 说明 |
|------|------|
| `name` | 控件 Name 属性 |
| `automation_id` | 控件 AutomationId |
| `control_type` | Button / Edit / ComboBox / Pane / Window |
| `prerequisites` | 点击前必须已展开的父级（如 `["制单资料"]`） |
| `dialog` | 控件所在弹窗的 AutomationId |
| `parent` | 控件所在容器的业务名 |

**prerequisites** — 导航层级自动处理。`click("制单信息")` 自动先 `click("制单资料")`，agent 无需知道层级关系。

**定位方式** — `find_elements` + uia backend。不用 `child_window`（多匹配时报错），不用 `descendants` 全遍历（慢）。

## 测试

```bash
python -m pytest tests/ -v
```

## 适配其他软件

1. 用 Inspect.exe (UIA 模式) 采集目标软件的控件属性
2. 替换 `MAPPING` dict 中的条目
3. 修改 `_ensure_connected()` 中的连接逻辑（窗口标题匹配）
