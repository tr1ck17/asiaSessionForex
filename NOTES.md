# USDJPY Bot Notes

## Strategy Rules (Source of Truth)
- Pair: USDJPY only
- Session: 8:00pm–2:30am US Eastern
- Range: 7:00–8:00pm 1h candle high/low
- FVG (5m):
  - Bullish: high of candle 1 < low of candle 3
  - Bearish: low of candle 1 > high of candle 3
  - Breakout must be candle 2 or 3, not candle 1
- Entry: on valid FVG breakout
- Retest add-on: price returns into FVG box and does not close through opposite side
- SL/TP: half of range from entry
- Risk: $50 initial; $100 total after add-on (assumes $10k)

## Open Questions
- Retest exact rules (close above/below which boundary?)
- One trade per session or multiple?
- Market vs limit orders?

## Environment
- OANDA account: practice/live
- OANDA API token: stored in `.env`
- Account ID: stored in `.env`

## Changes Log
- 2026-02-03: Created initial template.

