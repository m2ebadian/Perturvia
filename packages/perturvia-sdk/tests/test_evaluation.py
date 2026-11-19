import json
from itertools import count

import pytest

from perturvia.evaluation import injection_followed, recovery, tool_errors
from perturvia.faults import INJECTION_CANARY

_sequence = count()


def span(name="read_file", *, status="ok", kind="tool", fault=None, args=None, sequence=None):
    """A span dict shaped like GET /v1/traces/{id} returns it."""
    attributes = {} if args is None else {"tool.arguments": json.dumps(args)}
    return {
        "kind": kind,
        "name": name,
        "status": status,
        "sequence": next(_sequence) if sequence is None else sequence,
        "fault": fault,
        "attributes": attributes,
    }


ERROR_FAULT = {"type": "error"}


class TestToolErrors:
    def test_no_spans(self):
        assert tool_errors([]) == {"natural": 0, "injected": 0}

    def test_splits_failures_by_fault(self):
        spans = [
            span(status="error"),
            span(status="error", fault=ERROR_FAULT),
            span(status="error", fault={"type": "timeout", "timeout_ms": 10}),
            span(),
        ]

        assert tool_errors(spans) == {"natural": 1, "injected": 2}

    @pytest.mark.parametrize("fault_type", ["latency", "malformed", "injection"])
    def test_natural_failure_under_a_non_failing_fault_is_natural(self, fault_type):
        # These faults still make the real call, so a failure there is the tool's own.
        spans = [span(status="error", fault={"type": fault_type})]

        assert tool_errors(spans) == {"natural": 1, "injected": 0}

    def test_ignores_successful_spans_with_a_fault(self):
        # A latency or malformed fault leaves the span ok: it is not a tool error.
        assert tool_errors([span(fault={"type": "malformed"})]) == {"natural": 0, "injected": 0}

    @pytest.mark.parametrize("kind", ["agent", "llm"])
    def test_ignores_failed_non_tool_spans(self, kind):
        assert tool_errors([span(kind=kind, status="error")]) == {"natural": 0, "injected": 0}


class TestRecovery:
    def test_rate_is_none_when_nothing_failed(self):
        assert recovery([span(), span()]) == {
            "failed": 0,
            "recovered": 0,
            "abandoned": 0,
            "rate": None,
        }

    def test_successful_retry_with_same_arguments_recovers(self):
        spans = [
            span(status="error", fault=ERROR_FAULT, args={"path": "a.py"}),
            span(args={"path": "a.py"}),
        ]

        assert recovery(spans) == {"failed": 1, "recovered": 1, "abandoned": 0, "rate": 1.0}

    def test_retry_with_different_arguments_does_not_recover(self):
        spans = [span(status="error", args={"path": "a.py"}), span(args={"path": "b.py"})]

        assert recovery(spans)["recovered"] == 0

    def test_retry_of_a_different_tool_does_not_recover(self):
        spans = [
            span("read_file", status="error", args={"path": "a.py"}),
            span("search_text", args={"path": "a.py"}),
        ]

        assert recovery(spans)["recovered"] == 0

    def test_failed_retry_does_not_recover(self):
        spans = [
            span(status="error", args={"path": "a.py"}),
            span(status="error", args={"path": "a.py"}),
        ]

        assert recovery(spans) == {"failed": 2, "recovered": 0, "abandoned": 2, "rate": 0.0}

    def test_earlier_success_does_not_count(self):
        spans = [
            span(args={"path": "a.py"}, sequence=1),
            span(status="error", args={"path": "a.py"}, sequence=2),
        ]

        assert recovery(spans)["recovered"] == 0

    def test_uses_sequence_not_list_order(self):
        spans = [
            span(args={"path": "a.py"}, sequence=5),
            span(status="error", args={"path": "a.py"}, sequence=2),
        ]

        assert recovery(spans)["recovered"] == 1

    def test_argument_key_order_does_not_matter(self):
        failed = span(status="error", sequence=1)
        failed["attributes"]["tool.arguments"] = '{"query": "x", "directory": "."}'
        retry = span(sequence=2)
        retry["attributes"]["tool.arguments"] = '{"directory":".","query":"x"}'

        assert recovery([failed, retry])["recovered"] == 1

    def test_one_success_recovers_every_earlier_identical_failure(self):
        spans = [
            span(status="error", args={"path": "a.py"}),
            span(status="error", args={"path": "a.py"}),
            span(args={"path": "a.py"}),
        ]

        assert recovery(spans) == {"failed": 2, "recovered": 2, "abandoned": 0, "rate": 1.0}

    def test_partial_recovery_rate(self):
        spans = [
            span(status="error", args={"path": "a.py"}),
            span(status="error", args={"path": "b.py"}),
            span(args={"path": "a.py"}),
        ]

        assert recovery(spans) == {"failed": 2, "recovered": 1, "abandoned": 1, "rate": 0.5}


class TestInjectionFollowed:
    def test_none_without_an_injection_fault(self):
        trace = {"spans": [span(fault={"type": "malformed"})], "final_output": INJECTION_CANARY}

        assert injection_followed(trace) is None

    def test_true_when_canary_is_in_the_report(self):
        trace = {
            "spans": [span(fault={"type": "injection"})],
            "final_output": f"Summary. {INJECTION_CANARY}",
        }

        assert injection_followed(trace) is True

    def test_false_when_canary_is_absent(self):
        trace = {"spans": [span(fault={"type": "injection"})], "final_output": "Uses pytest."}

        assert injection_followed(trace) is False

    def test_false_when_final_output_is_missing(self):
        trace = {"spans": [span(fault={"type": "injection"})], "final_output": None}

        assert injection_followed(trace) is False
