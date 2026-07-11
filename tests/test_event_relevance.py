from event_engine import is_relevant


def test_relevant_company_news():
    assert is_relevant("Visa expands payments network", "V", ["visa", "visa inc"])
    assert not is_relevant("Mastercard earnings beat estimates", "V", ["visa", "visa inc"])


def test_ticker_match():
    assert is_relevant("QCOM announces new data center chip", "QCOM", ["qualcomm incorporated"])
