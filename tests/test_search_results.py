import pytest

from zenplayer.widgets.search_results import SearchResults


@pytest.mark.asyncio
async def test_shift_up_down_bindings_exist():
    widget = SearchResults()
    binding_keys = [b.key for b in widget.BINDINGS]
    assert "shift+up" in binding_keys
    assert "shift+down" in binding_keys


@pytest.mark.asyncio
async def test_shift_up_down_volume_actions():
    from zenplayer.app import ZenPlayer

    app = ZenPlayer(debug=True)
    async with app.run_test(size=(80, 24)) as pilot:
        await pilot.pause(0.1)
        results = app.screen.query_one(SearchResults)
        binding_map = {b.key: b.action for b in results.BINDINGS}
        assert binding_map["shift+up"] == "app.volume_up"
        assert binding_map["shift+down"] == "app.volume_down"
