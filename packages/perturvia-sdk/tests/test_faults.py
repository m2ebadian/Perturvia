import json
import random

import pytest

from perturvia.faults import INJECTION_CANARY, INJECTION_TEXT, FaultPolicy, corrupt, inject


class FixedDraw:
    """Stands in for random.Random and always draws the same value."""

    def __init__(self, value: float) -> None:
        self.value = value

    def random(self) -> float:
        return self.value


class TestValidation:
    def test_defaults_are_valid_and_inject_nothing(self):
        policy = FaultPolicy()
        rng = random.Random(0)

        assert all(policy.decide(rng) is None for _ in range(100))

    @pytest.mark.parametrize("rate", [-0.1, 1.1, float("nan"), float("inf")])
    def test_rejects_rate_outside_0_to_1(self, rate):
        with pytest.raises(ValueError, match="error_rate"):
            FaultPolicy(error_rate=rate)

    def test_rejects_rates_summing_above_1(self):
        with pytest.raises(ValueError, match="add up"):
            FaultPolicy(error_rate=0.6, latency_rate=0.5)

    def test_accepts_rates_summing_to_1_despite_float_rounding(self):
        # 0.1 + 0.2 + 0.7 is 1.0000000000000002 with naive float addition.
        FaultPolicy(error_rate=0.1, timeout_rate=0.2, latency_rate=0.7)

    @pytest.mark.parametrize("field", ["latency_ms", "timeout_ms"])
    @pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
    def test_rejects_invalid_delays(self, field, value):
        with pytest.raises(ValueError, match=field):
            FaultPolicy(**{field: value})

    def test_accepts_zero_delay(self):
        FaultPolicy(latency_ms=0.0, timeout_ms=0.0)


class TestDecide:
    @pytest.mark.parametrize(
        "field, fault",
        [
            ("error_rate", "error"),
            ("timeout_rate", "timeout"),
            ("latency_rate", "latency"),
            ("malformed_rate", "malformed"),
            ("injection_rate", "injection"),
        ],
    )
    def test_rate_of_1_always_gives_that_fault(self, field, fault):
        policy = FaultPolicy(**{field: 1.0})
        rng = random.Random(0)

        assert {policy.decide(rng) for _ in range(50)} == {fault}

    # Draws sit just inside each segment, not on its edge: a boundary like
    # 0.1 + 0.2 is 0.30000000000000004 in floating point.
    @pytest.mark.parametrize(
        "draw, expected",
        [
            (0.0, "error"),
            (0.0999, "error"),
            (0.1001, "timeout"),
            (0.2999, "timeout"),
            (0.3001, "latency"),
            (0.4001, "malformed"),
            (0.5001, "injection"),
            (0.5999, "injection"),
            (0.6001, None),
            (0.9999, None),
        ],
    )
    def test_segments_are_laid_out_in_order(self, draw, expected):
        policy = FaultPolicy(
            error_rate=0.1,
            timeout_rate=0.2,
            latency_rate=0.1,
            malformed_rate=0.1,
            injection_rate=0.1,
        )

        assert policy.decide(FixedDraw(draw)) == expected

    def test_same_seed_gives_same_schedule(self):
        policy = FaultPolicy(error_rate=0.2, latency_rate=0.2, injection_rate=0.2)

        def schedule(seed: int) -> list:
            rng = random.Random(seed)
            return [policy.decide(rng) for _ in range(200)]

        assert schedule(42) == schedule(42)
        assert schedule(42) != schedule(43)

    def test_frequencies_match_rates(self):
        policy = FaultPolicy(error_rate=0.25, malformed_rate=0.5)
        rng = random.Random(1)
        draws = [policy.decide(rng) for _ in range(20_000)]

        assert draws.count("error") / len(draws) == pytest.approx(0.25, abs=0.02)
        assert draws.count("malformed") / len(draws) == pytest.approx(0.5, abs=0.02)
        assert draws.count(None) / len(draws) == pytest.approx(0.25, abs=0.02)


class TestCorrupt:
    def test_keeps_first_half(self):
        assert corrupt("abcdef") == "abc"
        assert corrupt("abcdefg") == "abc"

    def test_breaks_json(self):
        text = json.dumps({"files": ["a.py", "b.py"], "truncated": False})

        with pytest.raises(json.JSONDecodeError):
            json.loads(corrupt(text))

    def test_is_deterministic(self):
        assert corrupt("same input") == corrupt("same input")

    def test_handles_empty_text(self):
        assert corrupt("") == ""


class TestInject:
    def test_keeps_real_result_and_appends_instruction(self):
        result = inject('{"files": []}')

        assert result.startswith('{"files": []}')
        assert result.endswith(INJECTION_TEXT)
        assert INJECTION_CANARY in result

    def test_never_mentions_injection(self):
        assert "inject" not in inject("data").lower()
