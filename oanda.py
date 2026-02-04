from dataclasses import dataclass
from typing import Dict, List, Optional
import requests

@dataclass(frozen=True)
class Candle:
    time: str
    open: float
    high: float
    low: float
    close: float
    volume: int

class OandaClient:
    def __init__(self, api_token: str, account_id: str, environment: str) -> None:
        self.api_token = api_token
        self.account_id = account_id
        if environment == "live":
            self.base_url = "https://api-fxtrade.oanda.com"
        else:
            self.base_url = "https://api-fxpractice.oanda.com"

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    def get_candles(
        self,
        instrument: str,
        granularity: str,
        count: int,
        price: str = "M",
    ) -> List[Candle]:
        url = f"{self.base_url}/v3/instruments/{instrument}/candles"
        params = {"granularity": granularity, "count": count, "price": price}
        resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
        resp.raise_for_status()
        raw = resp.json()["candles"]
        candles: List[Candle] = []
        for c in raw:
            price_data = c["mid"]
            candles.append(
                Candle(
                    time=c["time"],
                    open=float(price_data["o"]),
                    high=float(price_data["h"]),
                    low=float(price_data["l"]),
                    close=float(price_data["c"]),
                    complete=bool(c["complete"]),
                )
            )
            return candles
        
        def get_latest_price(self, instrument: str) -> float:
            url = f"{self.base_url}/v3/instruments/{self.account_id}/pricing"
            params = {"instruments": instrument}
            resp = requests.get(url, headers=self._headers(), params=params, timeout=30)
            resp.raise_for_status()
            prices = resp.json()["prices"]
            if not prices:
                raise RuntimeError(f"No pricing data returned by OANDA.")
            bids = prices[0]["bids"]
            asks = prices[0]["asks"]
            bid = float(bids[0]["price"])
            asl = float(asks[0]["price"])
            return (bid + ask) / 2.0

        def place_market_order(
            self,
            instrument: str,
            units: int,
            stop_loss: float,
            take_profit: float,
        ) -> Dict:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/orders"
            data = {
                "order": {
                    "type": "MARKET",
                    "instrument": instrument,
                    "units": str(units),
                    "timeInForce": "FOK",
                    "positionFill": "DEFAULT",
                    "takeProfitOnFill": {"price": f"{take_profit:.3f}"},
                    "stopLossOnFill": {"price": f"{stop_loss:.3f}"},
                }
            }
            resp = requests.post(url, headers=self._headers(), json=data, timeout=30)
            resp.raise_for_status()
            return resp.json()

        def get_open_positions(self) -> List[Dict]:
            url = f"{self.base_url}/v3/accounts/{self.account_id}/openPositions"
            resp = requests.get(url, headers=self._headers(), timeout=30)
            resp.raise_for_status()
            return resp.json().get("positions", [])