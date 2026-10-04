import pytest

from zenplayer.screens.player_screen import FooterBar


@pytest.mark.asyncio
async def test_footer_volume_initial():
    bar = FooterBar(volume=50)
    text = bar._vol_text(50)
    assert "█████" in text.plain
    assert "░░░░░" in text.plain


@pytest.mark.asyncio
async def test_footer_volume_zero():
    bar = FooterBar(volume=0)
    text = bar._vol_text(0)
    assert text.plain == "░" * 10


@pytest.mark.asyncio
async def test_footer_volume_full():
    bar = FooterBar(volume=100)
    text = bar._vol_text(100)
    assert text.plain == "█" * 10


@pytest.mark.asyncio
async def test_footer_volume_clamped():
    bar = FooterBar(volume=150)
    text = bar._vol_text(150)
    assert text.plain == "█" * 10


@pytest.mark.asyncio
async def test_footer_volume_negative_clamped():
    bar = FooterBar(volume=-10)
    text = bar._vol_text(-10)
    assert text.plain == "░" * 10


@pytest.mark.asyncio
async def test_footer_hints_text():
    from zenplayer.app import ZenPlayer

    app = ZenPlayer(debug=True)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(0.1)
        footer = app.screen.query_one(FooterBar)
        rendered = footer.render()
        plain = rendered.plain
        assert "[space] Play" in plain
        assert "[/] Search" in plain
        assert "[h] History" in plain
        assert "[r] Resume last session" in plain
        assert "[q] Quit" in plain
        assert "Volume" in plain
        assert "[p] Prev" not in plain
        assert "[n] Next" not in plain
        assert "[esc] Back" not in plain
