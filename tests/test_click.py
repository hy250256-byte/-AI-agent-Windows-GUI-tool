"""click.py 单元测试"""
import sys
import os
from unittest.mock import MagicMock
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.modules["pywinauto"] = MagicMock()
sys.modules["pywinauto.timings"] = MagicMock()


class TestClick:
    """测试 click() 函数"""

    def setup_method(self):
        import click
        click._app = MagicMock()
        click._main_win = MagicMock()

    def test_click_by_name(self):
        """name 定位：child_window(title=..., control_type=...) → click_input"""
        import click
        mock_ctrl = MagicMock()
        click._main_win.child_window.return_value = mock_ctrl

        click.click("查询")

        click._main_win.child_window.assert_called_with(
            title="查询", control_type="Button",
            top_level_only=False, enabled_only=False, visible_only=False,
        )
        mock_ctrl.click_input.assert_called_once()

    def test_click_by_automation_id(self):
        """automation_id 定位"""
        import click
        mock_ctrl = MagicMock()
        click._main_win.child_window.return_value = mock_ctrl

        click.click("输入制单号弹窗")

        click._main_win.child_window.assert_called_with(
            auto_id="FormInput", control_type="Window",
            top_level_only=False, enabled_only=False, visible_only=False,
        )

    def test_click_with_prerequisites(self):
        """制单信息 → 先点制单资料，再点制单信息"""
        import click
        calls = []
        orig_child = click._main_win.child_window
        click._main_win.child_window = lambda **kw: (
            MagicMock(click_input=lambda: calls.append(kw.get("title") or kw.get("auto_id")))
        )

        click.click("制单信息")

        assert calls == ["制单资料", "制单信息"]

    def test_click_in_dialog(self):
        """弹窗内控件：先定位弹窗，再在弹窗内 child_window"""
        import click
        mock_dia = MagicMock()
        mock_ctrl = MagicMock()
        click._app.window.return_value = mock_dia
        mock_dia.child_window.return_value = mock_ctrl

        click.click("输入制单号-确定")

        click._app.window.assert_called_with(auto_id="FormInput")
        mock_dia.child_window.assert_called_with(
            title="确定(O)", control_type="Button",
            top_level_only=False, enabled_only=False, visible_only=False,
        )

    def test_click_in_dialog_by_index(self):
        """弹窗内 index 定位：children()[index].click_input"""
        import click
        mock_dia = MagicMock()
        mock_ctrl = MagicMock()
        type(mock_ctrl).element_info = MagicMock()
        mock_ctrl.element_info.control_type = "Edit"
        mock_dia.children.return_value = [mock_ctrl]
        click._app.window.return_value = mock_dia

        click.click("新制单号输入框")

        click._app.window.assert_called_with(auto_id="FormInput")
        mock_ctrl.click_input.assert_called_once()

    def test_click_unknown_target_raises(self):
        import click
        with pytest.raises(KeyError):
            click.click("不存在的控件")
