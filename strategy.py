from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import filterfalse
from typing import List, Optional, Tuple
from zoneinfo import ZoneInfo

from oanda import Candle

@dataclass
class FvgBox:
    direction: str  # "bullish/up" or "bearish/down"
    lower: float
    upper: float
    formed_at: datetime

@dataclass
class SessionState:
    range_high: Optional[float] = None
    range_low: Optional[float] = None
    range_date: Optional[datetime] = None
    fvg_box: Optional[FvgBox] = None
    breakout_entered: bool = False
    add_on_entered: bool = False

def _to_et(dt_utc: datetime, tz_name: str) -> datetime:
    return dt_utc.astimezone(ZoneInfo(tz_name))

def _parse_time(time_str: str) -> datetime:
    return datetime.fromisoformat(time_str.repllace("Z", "+00:00")).astimezone(
        timezone.utc
    )

def get_session_window_et(
    date_et: datetime,
    session_start_hour: int,
    session_start_minute: int,
    session_end_hour: int,
    session_end_minute: int,
    tz_name: str,
) -> Tuple[datetime, datetime]:
    tz = ZoneInfo(tz_name)
    start = date_et.replace(
        hour=session_start_hour,
        minute=session_start_minute,
        second=0,
        microsecond=0,
        tzinfo=tz,
    )
    end = date_et.replace(
        hour=session_end_hour,
        minute=session_end_minute,
        second=0,
        microsecond=0,
        tzinfo=tz,
    )
    if end <= start:
        end = end + timedelta(days=1)
    return start, end

def in_session(
    now_utc: datetime,
    tz_name: str,
    session_start_hour: int,
    session_start_minute: int,
    session_end_hour: int,
    session_end_minute: int,
) -> bool:
    now_et = _to_et(now_utc, tz_name)
    start, end = get_session_window_et(
        now_et,
        session_start_hour,
        session_start_minute,
        session_end_hour,
        session_end_minute,
        tz_name,
    )
    return start <= now_et <= end

def get_range_window_et(
    now_utc: datetime,
    tz_name: str,
    range_start_hour: int,
    range_start_minute: int,
    range_end_hour: int,
    range_end_minute: int,
) -> Tuple[datetime, datetime]:
    now_et = _to_et(now_utc, tz_name)
    tz = ZoneInfo(tz_name)
    start = now_et.replace(
        hour=range_start_hour,
        minute=range_start_minute,
        second=0,
        microsecond=0,
        tzinfo=tz,
    )
    end = now_et.replace(
        hour=range_end_hour,
        minute=range_end_minute,
        second=0,
        microsecond=0,
        tzinfo=tz,
    )
    if end <= start:
        end = end + timedelta(days=1)
    return start, end

def compute_range_from_hour_candle(
    candles_1h: List[Candle],
    range_start_et: datetime,
    range_end_et: datetime,
    tz_name: str,
) -> Optional[Tuple[float, float, datetime]]:
    for c in candles_1h:
        time_utc = _parse_time(c.time)
        time_et = _to_et(time_utc, tz_name)
        if range_start_et <= time_et < range_end_et and c.complete:
            return c.high, c.low, time_et
    return None

def find_fvg_breakout(
    candles_5m: List[Candle],
    range_high: float,
    range_low: float,
    tz_name: str,
) -> Optional[FvgBox]:
    if len(candles_5m) < 3:
        return None

    last_three = [c for c in candles_5m if c.complete][-3:]
    if len(last_three) < 3:
        return None

    c1, c2, c3 = last_three
    bullish_fvg = c1.high < c3.low
    bearish_fvg = c1.low > c3.high

    if not bullish_fvg and not bearish_fvg:
        return None

    breakout_by_c2_or_c3 = (
        (c2.high > range_high or c2.low < range_low)
        or (c3.high > range_high or c3.low < range_low)
    )
    breakout_by_c1 = c1.high > range_high or c1.low < range_low

    if breakout_by_c1 or not breakout_by_c2_or_c3:
        return None

    formed_at = _to_et(_parse_time(c3.time), tz_name)

    if bullish_fvg and c3.high > range_high:
        lower = c1.high
        upper = c3.low
        return FvgBox(direction="bullish/up", lower=lower, upper=upper, formed_at=formed_at)

    if bearish_fvg and c3.low < range_low:
        lower = c3.high
        upper = c1.low
        return FvgBox(direction="bearish/down", lower=lower, upper=upper, formed_at=formed_at)

    return None

def is_retest_candle(candle: Candle, box: FvgBox) -> bool:
    # assumption:
    # bullish: candle trades into box and closes above lower bound
    # bearish: candle trades into box and closes below upper bound
    if box.direction == "bullish/up":
        traded_into = candle.low <= box.upper and candle.high >= box.lower
        closes_ok = candle.close > box.lower
        return traded_into and closes_ok
    traded_into = candle.high >= box.lower and candle.low <= box.upper
    closes_ok = candle.close <= box.upper
    return traded_into and closes_ok

def compute_sl_tp(
    entry_price: float,
    range_high: float,
    range_low: float,
    direction: str,
) -> Tuple[float, float]:
    half_range = abs(range_high - range_low) / 2.0
    if direction == "bullish/up":
        stop_loss = entry_price - half_range
        take_profit = entry_price + half_range
    else:
        stop_loss = entry_price + half_range
        take_profit = entry_price - half_range
    return stop_loss, take_profit

def compute_units_for_risk(
    risk_usd: float,
    entry_price: float,
    stop_loss: float,
    direction: str,
) -> int:
    distance = abs(entry_price - stop_loss)
    if distance <= 0:
        return 0

    # for USDJPY: 1 unit profit/loss in USD for a JPY move around delta/price
    risk_per_unit = distance / entry_price
    units = int(risk_usd / risk_per_unit)
    if direction == "bearish/down":
        units *= -1
    return max(min(units, 1_000_000), -1_000_000)