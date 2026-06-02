from stock_learn_agent.knowledge import chunk_text
from stock_learn_agent.market_data import analyze_recent_price, resolve_stock_symbol


def test_chunk_text_keeps_short_text_together():
    assert chunk_text("仓位管理很重要", max_chars=100) == ["仓位管理很重要"]


def test_chunk_text_splits_long_text():
    text = "风险。" * 1000
    chunks = chunk_text(text, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)


def test_resolve_tongfu_typo_to_a_share_code():
    resolved = resolve_stock_symbol("通富维电")
    assert resolved["provider"] == "eastmoney"
    assert resolved["symbol"] == "002156.SZ"


def test_analyze_recent_price_uses_quote(monkeypatch):
    def fake_quote(symbol):
        return {
            "input": symbol,
            "latest_price": 61.39,
            "previous_close": 66.0,
            "high": 66.0,
            "low": 60.96,
            "change_percent": -6.98,
            "amplitude_percent": 7.64,
            "turnover_rate_percent": 10.46,
        }

    monkeypatch.setattr("stock_learn_agent.market_data.get_recent_quote", fake_quote)
    result = analyze_recent_price("通富维电")
    assert result["quote"]["latest_price"] == 61.39
    assert any("跌幅" in risk for risk in result["analysis"]["risks"])
