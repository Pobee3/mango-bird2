import unittest
from datetime import datetime

from time_parser import parse_chinese_time


class ParseChineseTimeTests(unittest.TestCase):
    def setUp(self) -> None:
        # Monday, June 15, 2026 at 14:20.
        self.now = datetime(2026, 6, 15, 14, 20, 45)

    def assert_parsed(
        self, text: str, event: str, expected: datetime
    ) -> None:
        result = parse_chinese_time(text, now=self.now)
        self.assertEqual(result["raw"], text)
        self.assertEqual(result["event"], event)
        self.assertEqual(result["trigger_at"], expected)

    def test_absolute_month_day_defaults_to_midnight(self) -> None:
        self.assert_parsed(
            "3月5日交报告",
            "交报告",
            datetime(2026, 3, 5, 0, 0),
        )

    def test_absolute_month_day_with_afternoon_time(self) -> None:
        self.assert_parsed(
            "3月5日下午2点见客户",
            "见客户",
            datetime(2026, 3, 5, 14, 0),
        )

    def test_absolute_month_day_with_exact_minutes(self) -> None:
        self.assert_parsed(
            "3月5日14点20分发布版本",
            "发布版本",
            datetime(2026, 3, 5, 14, 20),
        )

    def test_clock_with_half_hour_uses_today_when_future(self) -> None:
        self.assert_parsed(
            "下午3点半开会",
            "开会",
            datetime(2026, 6, 15, 15, 30),
        )

    def test_clock_with_exact_minutes(self) -> None:
        self.assert_parsed(
            "下午3点25分打电话",
            "打电话",
            datetime(2026, 6, 15, 15, 25),
        )

    def test_tomorrow_morning_with_colon_clock(self) -> None:
        self.assert_parsed(
            "明早8:30开会",
            "开会",
            datetime(2026, 6, 16, 8, 30),
        )

    def test_full_width_colon_clock(self) -> None:
        self.assert_parsed(
            "明天上午9：15提交申请",
            "提交申请",
            datetime(2026, 6, 16, 9, 15),
        )

    def test_past_clock_rolls_to_tomorrow(self) -> None:
        self.assert_parsed(
            "上午10点写周报",
            "写周报",
            datetime(2026, 6, 16, 10, 0),
        )

    def test_this_week_future_weekday(self) -> None:
        self.assert_parsed(
            "本周三下午三点半开组会",
            "开组会",
            datetime(2026, 6, 17, 15, 30),
        )

    def test_this_week_past_weekday_rolls_to_next_week(self) -> None:
        thursday = datetime(2026, 6, 18, 12, 0)
        result = parse_chinese_time("这周三交材料", now=thursday)
        self.assertEqual(result["trigger_at"], datetime(2026, 6, 24, 0, 0))

    def test_next_week(self) -> None:
        self.assert_parsed(
            "下周一早上同步进度",
            "同步进度",
            datetime(2026, 6, 22, 9, 0),
        )

    def test_minutes_from_now(self) -> None:
        self.assert_parsed(
            "5分钟后提醒我喝水",
            "喝水",
            datetime(2026, 6, 15, 14, 25, 45),
        )

    def test_remind_me_is_removed_from_absolute_event(self) -> None:
        self.assert_parsed(
            "今天晚上8点提醒我健身",
            "健身",
            datetime(2026, 6, 15, 20, 0),
        )

    def test_hours_from_now(self) -> None:
        self.assert_parsed(
            "2小时后关烤箱",
            "关烤箱",
            datetime(2026, 6, 15, 16, 20, 45),
        )

    def test_half_hour_from_now(self) -> None:
        self.assert_parsed(
            "半小时后提醒我喝水",
            "喝水",
            datetime(2026, 6, 15, 14, 50, 45),
        )

    def test_arabic_hours_and_chinese_minutes(self) -> None:
        self.assert_parsed(
            "1小时三十分钟后提醒我开会",
            "开会",
            datetime(2026, 6, 15, 15, 50, 45),
        )

    def test_chinese_hours_and_arabic_minutes(self) -> None:
        self.assert_parsed(
            "两小时30分钟后提交报告",
            "提交报告",
            datetime(2026, 6, 15, 16, 50, 45),
        )

    def test_one_and_a_half_hours(self) -> None:
        self.assert_parsed(
            "1个半小时后提醒我出发",
            "出发",
            datetime(2026, 6, 15, 15, 50, 45),
        )

    def test_financial_chinese_numerals(self) -> None:
        self.assert_parsed(
            "壹小时叁拾分钟后提醒我关火",
            "关火",
            datetime(2026, 6, 15, 15, 50, 45),
        )

    def test_minute_abbreviation(self) -> None:
        self.assert_parsed(
            "30min后提醒我喝水",
            "喝水",
            datetime(2026, 6, 15, 14, 50, 45),
        )

    def test_hour_abbreviation(self) -> None:
        self.assert_parsed(
            "2h后提醒我关烤箱",
            "关烤箱",
            datetime(2026, 6, 15, 16, 20, 45),
        )

    def test_mixed_abbreviated_units(self) -> None:
        self.assert_parsed(
            "1h30min后提醒我开会",
            "开会",
            datetime(2026, 6, 15, 15, 50, 45),
        )

    def test_chinese_number_with_abbreviated_units(self) -> None:
        self.assert_parsed(
            "两h三十min后提交报告",
            "提交报告",
            datetime(2026, 6, 15, 16, 50, 45),
        )

    def test_this_month_day(self) -> None:
        self.assert_parsed(
            "本月18号上午10点交报告",
            "交报告",
            datetime(2026, 6, 18, 10, 0),
        )

    def test_today_evening(self) -> None:
        self.assert_parsed(
            "今天晚上8点健身",
            "健身",
            datetime(2026, 6, 15, 20, 0),
        )

    def test_tomorrow_uses_one_day_offset_before_clock(self) -> None:
        self.assert_parsed(
            "明天上午8点30分开会",
            "开会",
            datetime(2026, 6, 16, 8, 30),
        )

    def test_day_after_tomorrow_uses_two_day_offset_before_clock(self) -> None:
        self.assert_parsed(
            "后天下午3点提醒我交材料",
            "交材料",
            datetime(2026, 6, 17, 15, 0),
        )

    def test_noon_without_clock_defaults_to_1130(self) -> None:
        self.assert_parsed(
            "中午吃饭",
            "吃饭",
            datetime(2026, 6, 16, 11, 30),
        )

    def test_morning_without_clock_defaults_to_0900(self) -> None:
        self.assert_parsed(
            "明天早上跑步",
            "跑步",
            datetime(2026, 6, 16, 9, 0),
        )

    def test_invalid_period_hour_returns_failure(self) -> None:
        text = "上午15点开会"
        result = parse_chinese_time(text, now=self.now)
        self.assertEqual(
            result,
            {"event": text, "trigger_at": None, "raw": text},
        )

    def test_unparseable_text_returns_failure(self) -> None:
        text = "记得买牛奶"
        result = parse_chinese_time(text, now=self.now)
        self.assertEqual(
            result,
            {"event": text, "trigger_at": None, "raw": text},
        )


if __name__ == "__main__":
    unittest.main()
