import pytest

from app.state import CallState, CallStateMachine, InvalidTransition


def test_call_state_transitions_and_rejects_skips() -> None:
    machine = CallStateMachine()
    machine.transition(CallState.LISTENING)
    machine.transition(CallState.THINKING)
    machine.transition(CallState.SPEAKING)
    machine.transition(CallState.LISTENING)
    machine.transition(CallState.ENDED)
    with pytest.raises(InvalidTransition):
        machine.transition(CallState.LISTENING)


def test_barge_in_state_can_return_to_listening() -> None:
    machine = CallStateMachine()
    machine.transition(CallState.LISTENING)
    machine.transition(CallState.THINKING)
    machine.transition(CallState.SPEAKING)
    machine.transition(CallState.LISTENING)
    assert machine.state is CallState.LISTENING
