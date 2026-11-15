from enum import StrEnum


class CallState(StrEnum):
    NEW = "new"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ENDED = "ended"


_ALLOWED: dict[CallState, set[CallState]] = {
    CallState.NEW: {CallState.LISTENING, CallState.ENDED},
    CallState.LISTENING: {CallState.THINKING, CallState.ENDED},
    CallState.THINKING: {CallState.SPEAKING, CallState.LISTENING, CallState.ENDED},
    CallState.SPEAKING: {CallState.LISTENING, CallState.ENDED},
    CallState.ENDED: set(),
}


class InvalidTransition(ValueError):
    pass


class CallStateMachine:
    def __init__(self) -> None:
        self.state = CallState.NEW

    def transition(self, target: CallState) -> None:
        if target not in _ALLOWED[self.state]:
            raise InvalidTransition(f"cannot transition {self.state} -> {target}")
        self.state = target
