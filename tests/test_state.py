from betternotes.state import FileState, State, load_state, save_state


def test_roundtrip(tmp_path):
    path = tmp_path / "state.json"
    state = State(
        last_sent_date="2026-07-06",
        files={"abc": FileState(modified_time="2026-07-05T20:00:00Z", subject="Mathematik")},
        subject_summaries={"Mathematik": "### Rückblick\n- Ableitungen"},
    )
    save_state(state, path)
    loaded = load_state(path)
    assert loaded == state


def test_missing_file_gives_empty_state(tmp_path):
    state = load_state(tmp_path / "nope.json")
    assert state.last_sent_date == ""
    assert state.files == {}
