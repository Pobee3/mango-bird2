"""Rule-based Chinese natural-language time parser."""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional, TypedDict


class ParseResult(TypedDict):
    event: str
    trigger_at: Optional[datetime]
    raw: str


_NUMBER = r"(?:\d{1,4}|[零〇一二两三四五六七八九十百壹贰叁肆伍陆柒捌玖拾佰]+)"
_RELATIVE_RE = re.compile(
    rf"(?:"
    rf"(?P<hour_half>{_NUMBER})\s*个?半(?:小时|h)"
    rf"|(?P<half_hour>半(?:小时|h))"
    rf"|(?P<hours>{_NUMBER})\s*个?(?:小时|h)"
    rf"(?:\s*(?P<minutes>{_NUMBER})\s*(?:分钟|min))?"
    rf"|(?P<minutes_only>{_NUMBER})\s*(?:分钟|min)"
    rf")后",
    re.IGNORECASE,
)
_WEEK_RE = re.compile(
    r"(?P<prefix>本周|这周|下周)(?:星期|周)?"
    r"(?P<weekday>[一二三四五六日天1-7])"
)
_MONTH_DAY_RE = re.compile(
    rf"(?P<month>{_NUMBER})月(?P<day>{_NUMBER})(?:日|号)"
)
_THIS_MONTH_RE = re.compile(rf"本月(?P<day>{_NUMBER})(?:日|号)")
_DAY_WORD_RE = re.compile(r"今天|明天|明早|后天")
_CLOCK_RE = re.compile(
    rf"(?P<period>上午|下午|晚上|中午|早上)?\s*"
    rf"(?P<hour>{_NUMBER})点"
    rf"(?:(?P<minute>{_NUMBER})分|(?P<half>半))?"
)
_COLON_CLOCK_RE = re.compile(
    rf"(?P<period>上午|下午|晚上|中午|早上)?\s*"
    rf"(?P<hour>{_NUMBER})[:：](?P<minute>{_NUMBER})"
)
_DEFAULT_PERIOD_RE = re.compile(r"中午|早上")

_CHINESE_DIGITS = {
    "零": 0,
    "〇": 0,
    "一": 1,
    "二": 2,
    "两": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "壹": 1,
    "贰": 2,
    "叁": 3,
    "肆": 4,
    "伍": 5,
    "陆": 6,
    "柒": 7,
    "捌": 8,
    "玖": 9,
}
_WEEKDAYS = {
    "一": 0,
    "二": 1,
    "三": 2,
    "四": 3,
    "五": 4,
    "六": 5,
    "日": 6,
    "天": 6,
    "1": 0,
    "2": 1,
    "3": 2,
    "4": 3,
    "5": 4,
    "6": 5,
    "7": 6,
}


def _parse_number(value: str) -> int:
    if value.isdigit():
        return int(value)

    if all(char in _CHINESE_DIGITS for char in value):
        return int("".join(str(_CHINESE_DIGITS[char]) for char in value))

    total = 0
    current = 0
    for char in value:
        if char in _CHINESE_DIGITS:
            current = _CHINESE_DIGITS[char]
        elif char in {"十", "拾"}:
            total += (current or 1) * 10
            current = 0
        elif char in {"百", "佰"}:
            total += (current or 1) * 100
            current = 0
        else:
            raise ValueError(f"Unsupported Chinese number: {value}")
    return total + current


def _clock_values(match: re.Match[str]) -> tuple[int, int]:
    values = match.groupdict()
    period = values.get("period")
    hour = _parse_number(values["hour"])
    minute = (
        30
        if values.get("half")
        else _parse_number(values.get("minute") or "0")
    )

    if not 0 <= minute <= 59:
        raise ValueError("Minute must be between 0 and 59")

    if period in {"上午", "早上"}:
        if not 1 <= hour <= 11:
            raise ValueError(f"{period} only accepts hours from 1 to 11")
    elif period == "下午":
        if not 1 <= hour <= 6:
            raise ValueError("下午 only accepts hours from 1 to 6")
        hour += 12
    elif period == "晚上":
        if not 7 <= hour <= 11:
            raise ValueError("晚上 only accepts hours from 7 to 11")
        hour += 12
    elif period == "中午":
        if hour not in {11, 12}:
            raise ValueError("中午 only accepts 11点 or 12点")
    elif not 0 <= hour <= 23:
        raise ValueError("Hour must be between 0 and 23")

    return hour, minute


def _event_without_spans(raw: str, spans: list[tuple[int, int]]) -> str:
    chars = list(raw)
    for start, end in spans:
        chars[start:end] = [" "] * (end - start)
    event = re.sub(r"\s+", " ", "".join(chars)).strip()
    event = event.replace("提醒我", "")
    event = re.sub(r"\s+", " ", event).strip()
    return event.strip("，,。；;：:")


def _failed(raw: str) -> ParseResult:
    return {"event": raw, "trigger_at": None, "raw": raw}


def parse_chinese_time(text: str, now: Optional[datetime] = None) -> ParseResult:
    """Parse a supported Chinese time expression from ``text``.

    ``now`` is injectable for deterministic tests. Production callers should
    omit it so the parser uses the current local time.
    """

    raw = text
    base = now or datetime.now()
    if not text or not text.strip():
        return _failed(raw)

    relative_match = _RELATIVE_RE.search(text)
    if relative_match:
        try:
            values = relative_match.groupdict()
            if values["hour_half"]:
                delta = timedelta(
                    hours=_parse_number(values["hour_half"]), minutes=30
                )
            elif values["half_hour"]:
                delta = timedelta(minutes=30)
            elif values["hours"]:
                delta = timedelta(
                    hours=_parse_number(values["hours"]),
                    minutes=_parse_number(values["minutes"] or "0"),
                )
            else:
                delta = timedelta(
                    minutes=_parse_number(values["minutes_only"])
                )
            event = _event_without_spans(text, [relative_match.span()])
            return {"event": event, "trigger_at": base + delta, "raw": raw}
        except ValueError:
            return _failed(raw)

    spans: list[tuple[int, int]] = []
    explicit_date = False
    roll_if_past = False

    try:
        week_match = _WEEK_RE.search(text)
        month_day_match = _MONTH_DAY_RE.search(text)
        this_month_match = _THIS_MONTH_RE.search(text)
        day_word_match = _DAY_WORD_RE.search(text)

        if week_match:
            target_weekday = _WEEKDAYS[week_match.group("weekday")]
            monday = (base - timedelta(days=base.weekday())).date()
            week_offset = 7 if week_match.group("prefix") == "下周" else 0
            target_date = monday + timedelta(days=week_offset + target_weekday)
            explicit_date = True
            spans.append(week_match.span())
        elif this_month_match:
            target_date = base.date().replace(
                day=_parse_number(this_month_match.group("day"))
            )
            explicit_date = True
            spans.append(this_month_match.span())
        elif month_day_match:
            target_date = base.date().replace(
                month=_parse_number(month_day_match.group("month")),
                day=_parse_number(month_day_match.group("day")),
            )
            explicit_date = True
            spans.append(month_day_match.span())
        elif day_word_match:
            day_offsets = {"今天": 0, "明天": 1, "明早": 1, "后天": 2}
            day_offset = day_offsets[day_word_match.group()]
            target_date = base.date() + timedelta(days=day_offset)
            explicit_date = True
            roll_if_past = day_offset == 0
            spans.append(day_word_match.span())
        else:
            target_date = base.date()
            roll_if_past = True

        clock_match = _CLOCK_RE.search(text) or _COLON_CLOCK_RE.search(text)
        if clock_match:
            hour, minute = _clock_values(clock_match)
            spans.append(clock_match.span())
        else:
            default_period_match = _DEFAULT_PERIOD_RE.search(text)
            if default_period_match:
                if default_period_match.group() == "中午":
                    hour, minute = 11, 30
                else:
                    hour, minute = 9, 0
                spans.append(default_period_match.span())
            elif explicit_date:
                hour, minute = 0, 0
            else:
                return _failed(raw)

        trigger_at = datetime.combine(
            target_date,
            base.time().replace(
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0,
            ),
        )

        if week_match and week_match.group("prefix") in {"本周", "这周"}:
            if trigger_at <= base:
                trigger_at += timedelta(days=7)
        elif roll_if_past and trigger_at <= base:
            trigger_at += timedelta(days=1)

        event = _event_without_spans(text, spans)
        return {"event": event, "trigger_at": trigger_at, "raw": raw}
    except (KeyError, TypeError, ValueError):
        return _failed(raw)


__all__ = ["ParseResult", "parse_chinese_time"]
