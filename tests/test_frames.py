from tests.frame_examples import frames
from b2c2.frames import ErrorResponseFrame


def test_error_resp_to_exception():
    frame = ErrorResponseFrame(**frames.error_response_bad_instrument)
    exc = frame.to_exception()
    assert (
        repr(exc) ==
        "InvalidSubscriptionRequest('Invalid subscription request.')"
    )
    assert exc.error_response is frame
