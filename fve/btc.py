"""BTC-USD daily closes from the Coinbase Exchange public candles API (UTC days).

Strategy measures bitcoin fair value at its principal market price; the 10-Q/10-K fair value divided by units
gives the filing's own quarter-end price, which we prefer where it exists (see xbrl.implied_btc_price).
Coinbase daily candles fill the gaps and supply the return history for the bootstrap."""
import json
from datetime import date, datetime, timedelta, timezone

from .sources import RAW, fetch

API = "https://api.exchange.coinbase.com/products/BTC-USD/candles?granularity=86400&start={s}&end={e}"
UA = "RahilBhavan-research (github.com/RahilBhavan)"
FIRST = date(2015, 7, 21)


def fetch_all(through, refresh=False):
    """Cache candles in 290-day chunks from FIRST through `through` (inclusive)."""
    s = FIRST
    while s <= through:
        e = min(s + timedelta(days=289), through)
        fetch(API.format(s=s.isoformat(), e=(e + timedelta(days=1)).isoformat()),
              f"coinbase/btc-usd-daily_{s.isoformat()}_{e.isoformat()}.json", refresh=refresh, ua=UA)
        s = e + timedelta(days=1)


def daily_closes():
    """{date: close} from every cached chunk. Candle rows are [time, low, high, open, close, volume]."""
    out = {}
    for p in sorted((RAW / "coinbase").glob("btc-usd-daily_*.json")):
        for row in json.loads(p.read_text()):
            d = datetime.fromtimestamp(row[0], tz=timezone.utc).date()
            out[d] = float(row[4])
    return dict(sorted(out.items()))


def close_on_or_before(closes, d):
    for k in range(10):
        c = closes.get(d - timedelta(days=k))
        if c is not None:
            return c
    raise KeyError(d)
