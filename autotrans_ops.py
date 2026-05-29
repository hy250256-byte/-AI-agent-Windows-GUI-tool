"""
圣瑞思吊挂系统 GUI 操作工具

用法:
    python autotrans_ops.py click <target>
    python autotrans_ops.py input <target> <value>

返回 (stdout):
    {"ok": true}                        # 成功
    {"ok": false, "error": "..."}       # 失败
"""

import sys
import json

from pywinauto import Application
from pywinauto.backend import registry
from pywinauto.findwindows import find_elements
from pywinauto.timings import Timings

Timings.window_find_timeout = 10

# find_elements 返回原始 element_info，需包一层 wrapper 才能调 click_input 等方法
_uia_wrapper = registry.backends["uia"].generic_wrapper_class

# 控件映射表：业务名 → {name, automation_id, control_type, prerequisites, dialog, parent, index}
MAPPING = {
    "制单资料":       {"name": "制单资料",       "control_type": "Button"},
    "制单信息":       {"name": "制单信息",       "control_type": "Button", "prerequisites": ["制单资料"]},
    "制单工序":       {"name": "制单工序",       "control_type": "Button", "prerequisites": ["制单资料"]},
    "吊挂加工方案":   {"name": "吊挂加工方案",   "control_type": "Button", "prerequisites": ["制单资料"]},
    "在线信息":       {"name": "在线信息",       "control_type": "Button"},
    "基本资料":       {"name": "基本资料",       "control_type": "Button"},
    "配置":           {"name": "配置",           "control_type": "Button"},
    "运行控制":       {"name": "运行控制",       "control_type": "Button"},
    "报表":           {"name": "报表",           "control_type": "Button"},
    "bar1":           {"automation_id": "bar1", "control_type": "Pane"},

    "工位实时信息":   {"name": "工位实时信息",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "工序平衡信息":   {"name": "工序平衡信息",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "多组工序平衡":   {"name": "多组工序平衡",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "在加工产品":     {"name": "在加工产品",     "control_type": "Button", "prerequisites": ["在线信息"]},
    "衣架信息查询":   {"name": "衣架信息查询",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "在线衣架查询":   {"name": "在线衣架查询",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "站点衣架查询":   {"name": "站点衣架查询",   "control_type": "Button", "prerequisites": ["在线信息"]},
    "回工":           {"name": "回工",           "control_type": "Button", "prerequisites": ["在线信息"]},
    "工序产量平衡":   {"name": "工序产量平衡",   "control_type": "Button", "prerequisites": ["在线信息"]},

    "保存":           {"name": "保存",           "control_type": "Button"},
    "取消":           {"name": "取消",           "control_type": "Button"},
    "刷新":           {"name": "刷新",           "control_type": "Button"},
    "编辑":           {"name": "编辑",           "control_type": "Button"},
    "新增":           {"name": "新增",           "control_type": "Button"},
    "删除":           {"name": "删除",           "control_type": "Button"},
    "删除明细":       {"name": "删除明细",       "control_type": "Button"},
    "查询":           {"name": "查询",           "control_type": "Button"},
    "复制":           {"name": "复制",           "control_type": "Button"},
    "另存为":         {"name": "另存为",         "control_type": "Button"},
    "相关表":         {"name": "相关表",         "control_type": "Button"},
    "版本":           {"name": "版本",           "control_type": "Button"},
    "从XLS导入":      {"name": "从XLS导入",      "control_type": "Button"},
    "导出方案":       {"name": "导出方案",       "control_type": "Button"},
    "查看日志":       {"name": "查看日志",       "control_type": "Button"},
    "制单":           {"name": "制单",           "control_type": "Button"},
    "显示当前":       {"name": "显示当前",       "control_type": "Button"},

    "制单号输入":     {"parent": "bar1", "control_type": "Edit", "index": 0},
    "客户名称字段":   {"name": "客户名称",       "control_type": "Pane"},

    "输入制单号弹窗": {"automation_id": "FormInput", "control_type": "Window"},
    "新制单号输入框": {"dialog": "FormInput", "control_type": "Edit", "index": 0},
    "另存为-确定":     {"dialog": "FormInput", "name": "确定(O)",     "control_type": "Button"},
    "另存为-取消":     {"dialog": "FormInput", "name": "取消(C)",     "control_type": "Button"},

    "制单选择弹窗":   {"automation_id": "FormZdList", "control_type": "Window"},
    "制单号搜索框":   {"dialog": "FormZdList", "automation_id": "textGridview1", "control_type": "Edit"},
    "选择加工方案":   {"dialog": "FormZdList", "automation_id": "comboBoxEx1",   "control_type": "ComboBox"},
    "选择流水线":     {"dialog": "FormZdList", "automation_id": "comboBoxEx3",   "control_type": "ComboBox"},
    "制单选择-查询":  {"dialog": "FormZdList", "name": "查询",    "control_type": "Button"},
    "制单选择-确定":  {"dialog": "FormZdList", "name": "确定(O)", "control_type": "Button"},
    "制单选择-取消":  {"dialog": "FormZdList", "name": "取消(C)", "control_type": "Button"},
}

_app = None
_main_win = None


def _ensure_connected():
    """确保连着 autotrans.exe。首次调用时连接，失效时自动重连。"""
    global _app, _main_win
    try:
        if _app is not None:
            _main_win.exists()
            return
    except Exception:
        _app = None
        _main_win = None
    _app = Application(backend="uia").connect(title_re=".*圣瑞思.*")
    _main_win = _app.top_window()


def _locate(target: str):
    """
    查映射表 → 处理 prerequisites → 定位控件 → 返回控件对象。

    内部职责：
    1. 递归点击所有前置依赖
    2. 弹窗内控件先定位弹窗
    3. child_window() 精确匹配，不遍历控件树
    """
    entry = MAPPING[target]

    for pre in entry.get("prerequisites", []):
        click(pre)

    _ensure_connected()
    search = _main_win

    if "dialog" in entry:
        search = _app.window(auto_id=entry["dialog"])
        search.wait("visible", timeout=10)

    if "parent" in entry:
        search = _locate(entry["parent"])

    kwargs = {"top_level_only": False, "enabled_only": False, "visible_only": False}

    if "automation_id" in entry:
        kwargs["auto_id"] = entry["automation_id"]
    elif "name" in entry:
        kwargs["title"] = entry["name"]
    elif "index" in entry:
        children = search.children()
        if entry.get("control_type"):
            children = [c for c in children
                        if c.element_info.control_type == entry["control_type"]]
        return children[entry["index"]]
    else:
        raise KeyError(f"控件 '{target}' 缺少定位属性 (name/automation_id/index)")

    if entry.get("control_type"):
        kwargs["control_type"] = entry["control_type"]

    kwargs["backend"] = "uia"
    elements = find_elements(**kwargs)
    if not elements:
        raise RuntimeError(f"找不到控件: {target}")
    return _uia_wrapper(elements[0])


def click(target: str):
    """点击指定控件"""
    _locate(target).click_input()


def input_text(target: str, value: str):
    """在指定控件中填入文本。点击聚焦 → Ctrl+A 全选 → 退格清空 → 输入"""
    ctrl = _locate(target)
    ctrl.click_input()
    ctrl.type_keys("^a{BACKSPACE}" + str(value))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"ok": False, "error": "用法: autotrans_ops.py click|input <target> [value]"}))
        sys.exit(1)

    cmd = sys.argv[1]

    try:
        if cmd == "click":
            if len(sys.argv) < 3:
                print(json.dumps({"ok": False, "error": "缺少 target 参数"}))
                sys.exit(1)
            click(sys.argv[2])
            print(json.dumps({"ok": True}))

        elif cmd == "input":
            if len(sys.argv) < 4:
                print(json.dumps({"ok": False, "error": "缺少 target 或 value 参数"}))
                sys.exit(1)
            target = sys.argv[2]
            value = " ".join(sys.argv[3:])
            input_text(target, value)
            print(json.dumps({"ok": True}))

        else:
            print(json.dumps({"ok": False, "error": f"未知命令: {cmd}"}))
            sys.exit(1)

    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        sys.exit(1)
