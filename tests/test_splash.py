import pytest

from zenplayer.app import ZenPlayer


@pytest.mark.asyncio
async def test_splash_transitions_to_player():
    app = ZenPlayer(debug=False)
    async with app.run_test(size=(80, 24)) as pilot:
        assert app.screen.__class__.__name__ == "SplashScreen"
        await pilot.pause(2.5)
        assert app.screen.__class__.__name__ == "PlayerScreen"


@pytest.mark.asyncio
async def test_debug_mode_skips_splash():
    app = ZenPlayer(debug=True)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(0.1)
        assert app.screen.__class__.__name__ == "PlayerScreen"
