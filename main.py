from datetime import datetime, timezone
import time

from config import load_config
from oanda import OandaClient
from strategy import (
    SessionState,
    compute_range_from_hour_candle,
    compute_sl_tp,
    compute_units_for_risk,
    find_fvg_breakout,
    get_range_window_et,
    in_session,
    is_retest_candle,
)

def main() -> None:
    config = load_config()
    client = OandaClient(config.api_token, config.account_id, config.environment)
    state = SessionState()

    print("USDJPY FVG bot started")

    while True:
        now_utc = datetime.now(timezone.utc)

        # reset state when session is not active
        if not in_session(
            now_utc,
            config.session_tz,
            config.session_start_hour,
            config.session_start_minute,
            config.session_end_hour,
            config.session_end_minute,
        ):
            state = SessionState()
            time.sleep(config.poll_interval_seconds)
            continue

        range_start_et, range_end_et = get_range_window_et(
            now_utc,
            config.session_tz,
            config.session_start_hour,
            config.session_start_minute,
            config.session_end_hour,
            config.session_end_minute,
        )

        if state.range_high is None or state.range_low is None:
            candles_1h = client.get_candles(
                config.instrument, granularity="H1", count=48
            )
            range_data = compute_range_from_hour_candle(
                candles_1h, range_start_et, range_end_et, config.session_tz
            )
            if range_data:
                state.range_high, state.range_low, state.range_date = range_data
                print(
                    f"Range set: high={state.range_high}, "
                    f"low={state.range_low:.3f}"
                )
            time.sleep(config.poll_interval_seconds)
            continue

        candles_5m = client.get_candles(
            config.instrument, granularity="M5", count=30
        )

        if not state.breakout_entered:
            fvg_box = find_fvg_breakout(
                candles_5m,
                state.range_high,
                state.range_low,
                config.session_tz,
            )
            if fvg_box:
                price = client.get_latest_price(config.instrument)
                sl, tp = compute_sl_tp(
                    price, state.range_high, state.range_low, fvg_box.direction
                )
                units = compute_units_for_risk(
                    config.initial_risk_usd, price, sl, fvg_box.direction
                )
                if units == 0:
                    print("Units computed as 0; skipping trade")
                else:
                    client.place_market_order(
                        config.instrument, units, stop_loss=sl, take_profit=tp
                    )
                    state.fvg_box = fvg_box
                    state.breakout_entered = True
                    print(
                        f"Breakout entry placed ({fvg_box.direction})."
                        f"Units={units}"
                    )
            
        if state.breakout_entered and not state.add_on_entered and state.fvg_box:
            last_complete = [c for c in candles_5m if c.complete][-1:]
            if last_complete and is_retest_candle(last_complete[0], state.fvg_box):
                price = client.get_latest_price(config.instrument)
                sl, tp = compute_sl_tp(
                    price,
                    state.range_high,
                    state.range_low,
                    state.fvg_box.direction,
                )
                if units == 0:
                    print("Units computed as 0; skipping add-on.")
                else:
                    client.place_market_order(
                        config.instrument, units, stop_loss=sl, take_profit=tp
                    )
                    state.add_on_entered = True
                    print(f"Add-on placed. Units={units}")

        time.sleep(config.poll_interval_seconds)

if __name__ == "__main__":
    main()