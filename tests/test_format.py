from zenplayer.utils.format import format_duration


def test_format_duration_none_returns_zero():
    assert format_duration(None) == "0:00"


def test_format_duration_zero_returns_zero():
    assert format_duration(0) == "0:00"


def test_format_duration_negative_returns_zero():
    assert format_duration(-5) == "0:00"


def test_format_duration_under_one_minute():
    assert format_duration(45) == "0:45"


def test_format_duration_exact_one_minute():
    assert format_duration(60) == "1:00"


def test_format_duration_under_one_hour():
    assert format_duration(325) == "5:25"


def test_format_duration_exact_one_hour():
    assert format_duration(3600) == "1:00:00"


def test_format_duration_multi_hour():
    assert format_duration(7384) == "2:03:04"


def test_format_duration_large_value_24h():
    assert format_duration(86400) == "24:00:00"


def test_format_duration_float_truncation():
    assert format_duration(59.9) == "0:59"
    assert format_duration(61.7) == "1:01"
