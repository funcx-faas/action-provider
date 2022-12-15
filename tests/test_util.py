from funcx_action_provider.util import FXUtil
import pytest
from time import strftime


class TestUtil:
    @pytest.mark.parametrize(
        "input_output",
        [
            ["", "", None],
            ["1", "1", None],
            ["1234567890123", "***7890123", None],
            ["1234567890123", "***7890123", 7],
            ["1234567890123", "***123", 3],
            ["1234567890123", "***", 0],
            ["1234", "***4", 1],
            ["123", "123", None],
            ["12", "*2", 1],
            ["1234", "**34", 2],
            ["1234567890123", "***7890123", -1],
        ]
    )
    def test_sanitize(self, input_output):
        input, output, show_max = input_output
        if show_max is None:
            assert output == FXUtil.sanitize(input)
        else:
            if show_max < 0:
                with pytest.raises(ValueError):
                    FXUtil.sanitize(input, show_max)
            else:
                assert output == FXUtil.sanitize(input, show_max)

    @pytest.mark.parametrize(
        "input_output",
        [
            ["1234567890123", "123...", 3, None],
            ["1234567890123", "1...", 1, None],
            ["1234567890123", "12345678...", 8, None],
            ["12\n345678901", "12 <br> 34567...", 8, True],
        ]
    )
    def test_get_start(self, input_output):
        in_str, output, maxl, replace_lb = input_output
        if replace_lb is None:
            assert output == FXUtil.get_start(in_str, max_length=maxl)
        else:
            assert output == FXUtil.get_start(
                in_str,
                max_length=maxl,
                replace_line_breaks=replace_lb,
            )

    @pytest.mark.parametrize("local", [True, False])
    def test_iso_tz_now(self, local):
        time_str = FXUtil.iso_tz_now(local)
        assert '20' == time_str[:2]
        if local:
            curtz = strftime('%z')
            assert (curtz[:3] + ':' + curtz[3:]) == time_str[-6:]
        else:
            assert '+00:00' == time_str[-6:]
