from zenplayer.audio.extractor import TrackInfo


def test_trackinfo_construction_required_fields():
    t = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t.id == "abc"
    assert t.title == "Song"
    assert t.artist == "Artist"
    assert t.duration == 180
    assert t.url == "https://example.com"


def test_trackinfo_construction_all_fields():
    t = TrackInfo(
        id="abc", title="Song", artist="Artist", duration=180,
        url="https://example.com", thumbnail="https://example.com/thumb.jpg",
        description="A song", source="soundcloud",
    )
    assert t.thumbnail == "https://example.com/thumb.jpg"
    assert t.description == "A song"
    assert t.source == "soundcloud"


def test_trackinfo_defaults_thumbnail_none():
    t = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t.thumbnail is None


def test_trackinfo_defaults_description_none():
    t = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t.description is None


def test_trackinfo_defaults_source_youtube():
    t = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t.source == "youtube"


def test_trackinfo_equality():
    t1 = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    t2 = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t1 == t2


def test_trackinfo_different_objects_not_identical():
    t1 = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    t2 = TrackInfo(id="abc", title="Song", artist="Artist", duration=180, url="https://example.com")
    assert t1 is not t2
