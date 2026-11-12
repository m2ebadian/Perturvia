from concurrent.futures import ThreadPoolExecutor

from opentelemetry import context
from opentelemetry.sdk.trace import TracerProvider

from perturvia._processor import SEQUENCE_ATTRIBUTE, SequenceProcessor


def test_numbers_spans_in_start_order(recorded_spans):
    tracer, exporter = recorded_spans
    with tracer.start_as_current_span("root"):
        with tracer.start_as_current_span("first"):
            pass
        with tracer.start_as_current_span("second"):
            pass

    sequences = {s.name: s.attributes[SEQUENCE_ATTRIBUTE] for s in exporter.get_finished_spans()}
    assert sequences == {"root": 0, "first": 1, "second": 2}


def test_traces_are_numbered_independently(recorded_spans):
    tracer, exporter = recorded_spans
    for _ in range(2):
        with tracer.start_as_current_span("root"):
            pass

    assert [s.attributes[SEQUENCE_ATTRIBUTE] for s in exporter.get_finished_spans()] == [0, 0]


def test_sequences_are_unique_under_concurrency(recorded_spans):
    tracer, exporter = recorded_spans
    with tracer.start_as_current_span("root"):
        ctx = context.get_current()

        def child(_):
            token = context.attach(ctx)
            try:
                with tracer.start_as_current_span("child"):
                    pass
            finally:
                context.detach(token)

        with ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(child, range(200)))

    sequences = sorted(s.attributes[SEQUENCE_ATTRIBUTE] for s in exporter.get_finished_spans())
    assert sequences == list(range(201))


def test_counter_removed_when_root_ends():
    processor = SequenceProcessor()
    provider = TracerProvider()
    provider.add_span_processor(processor)
    with provider.get_tracer("test").start_as_current_span("root"):
        assert len(processor._counters) == 1

    assert processor._counters == {}
