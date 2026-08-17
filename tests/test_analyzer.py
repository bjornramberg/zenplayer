from unittest.mock import MagicMock, patch

import numpy as np

from zenplayer.audio.analyzer import AudioAnalyzer


def _make_analyzer(num_bands=16, smoothing=0.3):
    """Create an analyzer with a mocked AudioCapture."""
    with patch("zenplayer.audio.analyzer.AudioCapture") as MockCapture:
        mock_capture = MagicMock()
        mock_capture.rate = 48000
        mock_capture.chunk = 2048
        mock_capture._proc = None
        MockCapture.return_value = mock_capture
        analyzer = AudioAnalyzer(num_bands=num_bands, smoothing=smoothing)
    return analyzer, mock_capture


def test_init_defaults():
    analyzer, _ = _make_analyzer()
    assert analyzer.num_bands == 16
    assert len(analyzer.bands) == 16
    assert all(b == 0.0 for b in analyzer.bands)
    assert analyzer.bass_power == 0.0


def test_init_custom_params():
    analyzer, _ = _make_analyzer(num_bands=8, smoothing=0.5)
    assert analyzer.num_bands == 8
    assert len(analyzer.bands) == 8
    assert analyzer._smoothing == 0.5


def test_set_playing_starts_capture():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer.set_playing(True)
    mock_capture.start.assert_called_once()


def test_set_playing_stops_capture():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    analyzer.set_playing(False)
    mock_capture.stop.assert_called_once()


def test_set_playing_noop_when_already_playing():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    analyzer.set_playing(True)
    mock_capture.start.assert_not_called()


def test_set_playing_noop_when_already_stopped():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer._playing = False
    analyzer.set_playing(False)
    mock_capture.stop.assert_not_called()


def test_is_active_when_stopped():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer._playing = False
    assert analyzer.is_active is False


def test_is_active_when_playing_no_proc():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer._playing = True
    assert analyzer.is_active is False


def test_is_active_when_playing_with_proc():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    assert analyzer.is_active is True


def test_update_not_playing_decays_bands():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer._playing = False
    analyzer.bands[0] = 0.5
    analyzer.update()
    assert analyzer.bands[0] < 0.5
    assert analyzer.bands[0] > 0.0


def test_update_not_playing_zeroes_small_bands():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = None
    analyzer._playing = False
    analyzer.bands[0] = 0.004
    analyzer.update()
    assert analyzer.bands[0] == 0.0


def test_update_playing_computes_bands():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    # Return a spectrum with some energy
    fft = np.random.rand(1025) * 100
    mock_capture.get_fft.return_value = fft
    analyzer.update()
    # Bands should have been updated (not all zero)
    assert any(b > 0.0 for b in analyzer.bands)


def test_update_playing_computes_bass_power():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    fft = np.random.rand(1025) * 100
    mock_capture.get_fft.return_value = fft
    analyzer.update()
    assert analyzer.bass_power >= 0.0


def test_get_bands_returns_current_values():
    analyzer, _ = _make_analyzer()
    analyzer.bands[0] = 0.42
    bands = analyzer.get_bands()
    assert bands[0] == 0.42
    assert bands is analyzer.bands


def test_get_bass_power_returns_current_value():
    analyzer, _ = _make_analyzer()
    analyzer.bass_power = 3.14
    assert analyzer.get_bass_power() == 3.14


def test_stop_resets_all_bands():
    analyzer, mock_capture = _make_analyzer()
    analyzer.bands[0] = 0.9
    analyzer._targets[0] = 0.8
    analyzer._playing = True
    analyzer.stop()
    assert all(b == 0.0 for b in analyzer.bands)
    assert all(t == 0.0 for t in analyzer._targets)
    assert analyzer._playing is False


def test_stop_stops_capture():
    analyzer, mock_capture = _make_analyzer()
    mock_capture._proc = MagicMock()
    analyzer._playing = True
    analyzer.stop()
    mock_capture.stop.assert_called_once()
