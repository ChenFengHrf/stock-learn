from stock_learn_agent.knowledge import chunk_text


def test_chunk_text_keeps_short_text_together():
    assert chunk_text("仓位管理很重要", max_chars=100) == ["仓位管理很重要"]


def test_chunk_text_splits_long_text():
    text = "风险。" * 1000
    chunks = chunk_text(text, max_chars=500, overlap=50)
    assert len(chunks) > 1
    assert all(chunk for chunk in chunks)

