from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any


A_SHARE_ALIASES = {
    "通富微电": "002156",
    "通富维电": "002156",
    "通富微電子": "002156",
    "通富微電": "002156",
    "tongfu": "002156",
    "tongfu microelectronics": "002156",
    "tfwd": "002156",
}

CANONICAL_A_SHARE_NAMES = {
    "002156": "通富微电",
}


def normalize_query(symbol: str) -> str:
    return re.sub(r"\s+", " ", symbol.strip()).lower()


def resolve_stock_symbol(symbol: str) -> dict[str, str]:
    """Resolve a user-facing stock name/code to a provider-specific symbol."""
    raw = symbol.strip()
    normalized = normalize_query(raw)
    alias_code = A_SHARE_ALIASES.get(normalized)
    if alias_code:
        return _a_share_result(raw, alias_code)

    six_digit = re.fullmatch(r"\d{6}", raw)
    if six_digit:
        return _a_share_result(raw, raw)

    yahoo_a_share = re.fullmatch(r"(\d{6})\.(sz|ss|sh)", normalized)
    if yahoo_a_share:
        code = yahoo_a_share.group(1)
        return _a_share_result(raw, code)

    return {
        "input": raw,
        "provider": "yfinance",
        "symbol": raw,
        "name": raw,
        "market": "global",
    }


def _a_share_result(raw: str, code: str) -> dict[str, str]:
    exchange = "SH" if code.startswith("6") else "SZ"
    secid_prefix = "1" if exchange == "SH" else "0"
    return {
        "input": raw,
        "provider": "eastmoney",
        "symbol": f"{code}.{exchange}",
        "code": code,
        "secid": f"{secid_prefix}.{code}",
        "name": CANONICAL_A_SHARE_NAMES.get(code, raw),
        "market": "cn_a_share",
    }


def _http_json(url: str) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def _eastmoney_number(value: Any, scale: int = 100) -> float | None:
    if value is None or value == "-":
        return None
    return round(float(value) / scale, 4)


def _eastmoney_timestamp(value: Any) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromtimestamp(int(value)).isoformat(sep=" ")
    except Exception:
        return None


def get_eastmoney_quote(resolved: dict[str, str]) -> dict[str, Any]:
    fields = ",".join(
        [
            "f43",
            "f44",
            "f45",
            "f46",
            "f47",
            "f48",
            "f57",
            "f58",
            "f60",
            "f86",
            "f116",
            "f152",
            "f169",
            "f170",
            "f171",
        ]
    )
    query = urllib.parse.urlencode({"secid": resolved["secid"], "fields": fields}, safe=",")
    url = f"https://push2.eastmoney.com/api/qt/stock/get?{query}"
    payload = _http_json(url)
    data = payload.get("data")
    if not data:
        raise ValueError(f"东方财富没有返回 {resolved['input']} 的行情数据")

    name = data.get("f58") or resolved["name"]
    quote = {
        "input": resolved["input"],
        "provider": "eastmoney",
        "symbol": resolved["symbol"],
        "code": data.get("f57") or resolved["code"],
        "name": name,
        "market": "A股",
        "currency": "CNY",
        "source_url": f"https://quote.eastmoney.com/{resolved['symbol'].lower().replace('.', '')}.html",
        "quote_time": _eastmoney_timestamp(data.get("f86")),
        "latest_price": _eastmoney_number(data.get("f43")),
        "previous_close": _eastmoney_number(data.get("f60")),
        "open": _eastmoney_number(data.get("f46")),
        "high": _eastmoney_number(data.get("f44")),
        "low": _eastmoney_number(data.get("f45")),
        "change": _eastmoney_number(data.get("f169")),
        "change_percent": _eastmoney_number(data.get("f170")),
        "amplitude_percent": _eastmoney_number(data.get("f171")),
        "volume_lots": data.get("f47"),
        "turnover_cny": data.get("f48"),
        "market_cap_cny": data.get("f116"),
    }
    return quote


def _to_float(value: str) -> float | None:
    if value in {"", "-", " "}:
        return None
    return float(value)


def _tencent_symbol(resolved: dict[str, str]) -> str:
    prefix = "sh" if resolved["symbol"].endswith(".SH") else "sz"
    return f"{prefix}{resolved['code']}"


def _tencent_timestamp(value: str) -> str | None:
    if not value or len(value) != 14:
        return None
    try:
        return datetime.strptime(value, "%Y%m%d%H%M%S").isoformat(sep=" ")
    except ValueError:
        return None


def get_tencent_quote(resolved: dict[str, str], *, fallback_error: str | None = None) -> dict[str, Any]:
    tencent_symbol = _tencent_symbol(resolved)
    url = f"https://qt.gtimg.cn/q={tencent_symbol}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=12) as response:
        raw = response.read().decode("gbk", errors="replace")

    if '="' not in raw:
        raise ValueError(f"腾讯行情没有返回 {resolved['input']} 的行情数据")

    values = raw.split('="', 1)[1].rstrip('";\n').split("~")
    if len(values) < 46:
        raise ValueError(f"腾讯行情返回格式异常：{raw[:120]}")

    quote = {
        "input": resolved["input"],
        "provider": "tencent",
        "fallback_from": fallback_error,
        "symbol": resolved["symbol"],
        "code": values[2] or resolved["code"],
        "name": values[1] or resolved["name"],
        "market": "A股",
        "currency": values[82] if len(values) > 82 and values[82] else "CNY",
        "source_url": f"https://gu.qq.com/{tencent_symbol}/gp",
        "quote_time": _tencent_timestamp(values[30]),
        "latest_price": _to_float(values[3]),
        "previous_close": _to_float(values[4]),
        "open": _to_float(values[5]),
        "high": _to_float(values[33]),
        "low": _to_float(values[34]),
        "change": _to_float(values[31]),
        "change_percent": _to_float(values[32]),
        "amplitude_percent": _to_float(values[43]),
        "turnover_rate_percent": _to_float(values[38]),
        "volume_lots": int(values[36]) if values[36].isdigit() else None,
        "turnover_cny_10k": _to_float(values[37]),
        "pe_ttm": _to_float(values[39]),
        "market_cap_cny_100m": _to_float(values[45]),
    }
    return quote


def get_yfinance_quote(symbol: str, period: str, interval: str) -> dict[str, Any]:
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError("yfinance 未安装；请先执行 uv pip install -e .") from exc

    ticker = yf.Ticker(symbol)
    history = ticker.history(period=period, interval=interval, auto_adjust=False)
    if history.empty:
        raise ValueError(f"没有查到 {symbol} 的行情数据。")

    latest = history.tail(1).iloc[0]
    return {
        "input": symbol,
        "provider": "yfinance",
        "symbol": symbol,
        "market": "global",
        "latest_bar": {
            "date": str(history.tail(1).index[0]),
            "open": float(latest["Open"]),
            "high": float(latest["High"]),
            "low": float(latest["Low"]),
            "close": float(latest["Close"]),
            "volume": int(latest["Volume"]),
        },
        "recent_bars": [
            {
                "date": str(index),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]),
            }
            for index, row in history.tail(10).iterrows()
        ],
    }


def get_recent_quote(symbol: str, period: str = "5d", interval: str = "1d") -> dict[str, Any]:
    resolved = resolve_stock_symbol(symbol)
    if resolved["provider"] == "eastmoney":
        try:
            return get_eastmoney_quote(resolved)
        except Exception as exc:
            return get_tencent_quote(resolved, fallback_error=str(exc))
    return get_yfinance_quote(resolved["symbol"], period, interval)


def format_quote(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def analyze_recent_price(symbol: str) -> dict[str, Any]:
    quote = get_recent_quote(symbol)
    latest = quote.get("latest_price")
    previous_close = quote.get("previous_close")
    high = quote.get("high")
    low = quote.get("low")
    change_percent = quote.get("change_percent")
    amplitude = quote.get("amplitude_percent")
    turnover_rate = quote.get("turnover_rate_percent")

    observations: list[str] = []
    risks: list[str] = []
    watch_points: list[str] = []

    if latest is not None and previous_close is not None:
        if latest < previous_close:
            observations.append(
                f"最新价 {latest} 低于昨收 {previous_close}，当日价格表现偏弱。"
            )
        elif latest > previous_close:
            observations.append(
                f"最新价 {latest} 高于昨收 {previous_close}，当日价格表现偏强。"
            )
        else:
            observations.append(f"最新价 {latest} 与昨收 {previous_close} 基本持平。")

    if change_percent is not None:
        if change_percent <= -5:
            risks.append(f"单日跌幅 {change_percent}% 较大，短线情绪和波动风险偏高。")
        elif change_percent >= 5:
            risks.append(f"单日涨幅 {change_percent}% 较大，追高和回撤风险需要控制。")

    if latest is not None and high is not None and low is not None and high > low:
        close_position = (latest - low) / (high - low)
        if close_position < 0.25:
            observations.append("收盘/最新价接近日内低位，说明卖压尚未明显释放完。")
        elif close_position > 0.75:
            observations.append("收盘/最新价接近日内高位，说明盘中承接相对较强。")

    if amplitude is not None and amplitude >= 6:
        risks.append(f"振幅 {amplitude}% 较高，说明分歧大，仓位不宜按低波动环境处理。")

    if turnover_rate is not None and turnover_rate >= 8:
        observations.append(f"换手率 {turnover_rate}% 较高，筹码交换活跃。")

    if low is not None:
        watch_points.append(f"观察是否跌破最近低点 {low}。")
    if previous_close is not None:
        watch_points.append(f"观察能否重新站回昨收/压力参考 {previous_close}。")

    if not risks:
        risks.append("当前行情数据没有触发极端波动提示，但仍需结合趋势、位置和仓位判断。")

    return {
        "quote": quote,
        "analysis": {
            "facts": observations,
            "risks": risks,
            "watch_points": watch_points,
            "disclaimer": "仅用于学习和复盘，不构成投资建议。",
        },
    }
