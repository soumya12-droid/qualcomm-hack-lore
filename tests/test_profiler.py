import logging
import time

from pc.indexer.profiler import InferenceProfiler


def test_summary_with_no_records():
    profiler = InferenceProfiler()
    assert profiler.summary() == {
        "total_inferences": 0,
        "backends": {},
        "any_fallback": False,
        "avg_latency_ms": 0.0,
    }


def test_backend_for_maps_known_providers():
    profiler = InferenceProfiler()
    assert profiler.backend_for("QNNExecutionProvider") == "NPU"
    assert profiler.backend_for("DmlExecutionProvider") == "GPU"
    assert profiler.backend_for("CUDAExecutionProvider") == "GPU"
    assert profiler.backend_for("CPUExecutionProvider") == "CPU"


def test_backend_for_unknown_provider_defaults_to_cpu():
    profiler = InferenceProfiler()
    assert profiler.backend_for("SomeMadeUpExecutionProvider") == "CPU"


def test_record_on_preferred_provider_is_not_a_fallback(caplog):
    profiler = InferenceProfiler(preferred_providers=["QNNExecutionProvider", "CPUExecutionProvider"])
    with caplog.at_level(logging.WARNING, logger="pc.indexer.profiler"):
        entry = profiler.record("QNNExecutionProvider", latency_ms=12.5)

    assert entry["fallback"] is False
    assert entry["backend"] == "NPU"
    assert caplog.text == ""


def test_record_falling_back_to_cpu_logs_warning(caplog):
    profiler = InferenceProfiler(preferred_providers=["QNNExecutionProvider", "CPUExecutionProvider"])
    with caplog.at_level(logging.WARNING, logger="pc.indexer.profiler"):
        entry = profiler.record("CPUExecutionProvider", latency_ms=40.0)

    assert entry["fallback"] is True
    assert "fell back" in caplog.text
    assert "QNNExecutionProvider" in caplog.text
    assert "CPUExecutionProvider" in caplog.text


def test_summary_computes_percentages_and_average_latency():
    profiler = InferenceProfiler(preferred_providers=["QNNExecutionProvider", "CPUExecutionProvider"])
    profiler.record("QNNExecutionProvider", latency_ms=10.0)
    profiler.record("QNNExecutionProvider", latency_ms=20.0)
    profiler.record("CPUExecutionProvider", latency_ms=30.0)
    profiler.record("CPUExecutionProvider", latency_ms=40.0)

    summary = profiler.summary()

    assert summary["total_inferences"] == 4
    assert summary["backends"]["NPU"]["count"] == 2
    assert summary["backends"]["NPU"]["percentage"] == 50.0
    assert summary["backends"]["CPU"]["count"] == 2
    assert summary["backends"]["CPU"]["percentage"] == 50.0
    assert summary["avg_latency_ms"] == 25.0
    assert summary["any_fallback"] is True


def test_summary_no_fallback_when_all_on_preferred_provider():
    profiler = InferenceProfiler(preferred_providers=["QNNExecutionProvider"])
    profiler.record("QNNExecutionProvider", latency_ms=5.0)
    profiler.record("QNNExecutionProvider", latency_ms=7.0)

    assert profiler.summary()["any_fallback"] is False


def test_track_context_manager_records_latency_and_provider():
    profiler = InferenceProfiler(preferred_providers=["CPUExecutionProvider"])
    with profiler.track("CPUExecutionProvider"):
        time.sleep(0.01)

    summary = profiler.summary()
    assert summary["total_inferences"] == 1
    assert summary["avg_latency_ms"] >= 10.0
    assert summary["any_fallback"] is False


def test_reset_clears_records():
    profiler = InferenceProfiler()
    profiler.record("CPUExecutionProvider", latency_ms=1.0)
    profiler.reset()
    assert profiler.summary()["total_inferences"] == 0
