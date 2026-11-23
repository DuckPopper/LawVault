import threading
import jobs


def test_job_runs_in_background_and_reports_result():
    gate = threading.Event()

    def work(x):
        gate.wait(5)
        return x * 2, None

    assert jobs.start("u1", "chat", "", work, 21, label="Legal assistant", meta={"q": "hi"})
    j = jobs.get("u1", "chat")
    assert j["running"] and j["meta"] == {"q": "hi"}
    assert not jobs.start("u1", "chat", "", work, 1)          # no second copy while the first runs
    assert jobs.running_keys("u1", {"chat"}) == {("u1", "chat", "")}
    assert jobs.get("u2", "chat") is None and jobs.for_user("u2") == []  # other users don't see it
    gate.set()
    jobs._jobs[("u1", "chat", "")]["future"].result(5)
    j = jobs.get("u1", "chat")
    assert not j["running"] and (j["value"], j["error"]) == (42, None)
    assert [x["label"] for x in jobs.for_user("u1")] == ["Legal assistant"]
    jobs.mark_seen("u1", "chat")
    assert jobs.for_user("u1") == []
    jobs.pop("u1", "chat")
    assert jobs.get("u1", "chat") is None


def test_job_crash_becomes_an_error_message():
    def boom():
        raise RuntimeError("network down")

    jobs.start("u3", "review", "d1", boom)
    jobs._jobs[("u3", "review", "d1")]["future"].result(5)
    j = jobs.get("u3", "review", "d1")
    assert j["value"] is None and "try again" in j["error"]
    jobs.pop("u3", "review", "d1")
