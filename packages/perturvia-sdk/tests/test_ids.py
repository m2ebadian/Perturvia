from perturvia._ids import span_uuid, trace_uuid

TRACE_ID = 0x0123456789ABCDEF_FEDCBA9876543210
SPAN_ID = 0x1122334455667788


def test_trace_uuid_keeps_all_128_bits():
    assert trace_uuid(TRACE_ID).int == TRACE_ID


def test_span_uuid_combines_trace_prefix_and_span_id():
    value = span_uuid(TRACE_ID, SPAN_ID).int
    assert value >> 64 == TRACE_ID >> 64
    assert value & (2**64 - 1) == SPAN_ID


def test_span_uuid_is_deterministic():
    assert span_uuid(TRACE_ID, SPAN_ID) == span_uuid(TRACE_ID, SPAN_ID)


def test_same_span_id_in_different_traces_does_not_collide():
    other_trace = TRACE_ID ^ (1 << 100)
    assert span_uuid(TRACE_ID, SPAN_ID) != span_uuid(other_trace, SPAN_ID)
