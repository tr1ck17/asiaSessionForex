from dataclasses import dataclass
from dotenv import load_dotenv
import os


load_dotenv()


@dataclass(frozen=True)
class Config:
    api_token: str
    account_id: str
    environment: str

    instrument: str = "USD_JPY"
    session_tz: str = "America/New_York"

    # Session times in local (ET) time.
    session_start_hour: int = 20
    session_start_minute: int = 0
    session_end_hour: int = 2
    session_end_minute: int = 30

    # Range candle window: 7pm-8pm ET
    range_start_hour: int = 19
    range_start_minute: int = 0
    range_end_hour: int = 20
    range_end_minute: int = 0

    # Risk targets
    initial_risk_usd: float = 50.0
    add_on_total_risk_usd: float = 100.0

    poll_interval_seconds: int = 10


def load_config() -> Config:
    token = os.getenv("OANDA_API_TOKEN", "").strip()
    account_id = os.getenv("OANDA_ACCOUNT_ID", "").strip()
    env = os.getenv("OANDA_ENV", "practice").strip().lower()

    if not token or not account_id:
        raise RuntimeError(
            "Missing OANDA_API_TOKEN or OANDA_ACCOUNT_ID in environment."
        )

    if env not in {"practice", "live"}:
        raise RuntimeError("OANDA_ENV must be 'practice' or 'live'.")

    return Config(
        api_token=token,
        account_id=account_id,
        environment=env,
    )

