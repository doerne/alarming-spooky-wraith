from app.application.scan_progress import (
    GITHUB_SYNC_STEP,
    PERSIST_STEP,
    ScanStep,
    StepState,
    initial_steps,
)
from tests.fakes import descriptor


def test_initial_steps_list_sources_then_persist_and_sync() -> None:
    steps = initial_steps([descriptor("osv"), descriptor("nvd")])
    assert [step.key for step in steps] == ["osv", "nvd", PERSIST_STEP, GITHUB_SYNC_STEP]
    assert steps[-2] == ScanStep(PERSIST_STEP, "Funde speichern")
    assert steps[-1] == ScanStep(GITHUB_SYNC_STEP, "GitHub-Abgleich")
    assert all(step.state == StepState.PENDING for step in steps)


def test_source_step_uses_the_source_name() -> None:
    source = descriptor("osv")
    assert initial_steps([source])[0].label == source.name
