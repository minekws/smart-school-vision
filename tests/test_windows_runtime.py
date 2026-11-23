from windows_bundle.runtime import resolve_video_source, stage_web_assets


def test_runtime_assets_preserve_user_photos(tmp_path):
    bundle = tmp_path / "bundle"
    (bundle / "static").mkdir(parents=True)
    (bundle / "static" / "main.js").write_text("// bundled", encoding="utf-8")
    (bundle / "site").mkdir()
    (bundle / "site" / "index.html").write_text("dashboard", encoding="utf-8")
    state = tmp_path / "state"
    photos = state / "static" / "images"
    photos.mkdir(parents=True)
    (photos / "existing.jpg").write_bytes(b"existing")

    stage_web_assets(bundle, state)

    assert (state / "site" / "index.html").read_text() == "dashboard"
    assert (photos / "existing.jpg").read_bytes() == b"existing"


def test_video_source_resolves_before_changing_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "clip.mp4").touch()

    assert resolve_video_source(None) is None
    assert resolve_video_source("clip.mp4") == str(tmp_path / "clip.mp4")
