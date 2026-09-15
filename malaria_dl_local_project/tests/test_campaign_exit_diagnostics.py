"""Synthetic coordinator outcomes; no database, child process or model."""
import pytest

from src.malaria_dl.execution.campaign import execute_campaign


@pytest.mark.parametrize('exit_code,expected', [
    (-9, 'CHILD_EXIT_-9'),
    (2, 'CHILD_EXIT_2'),
    (0, 'CHILD_EXIT_0_INCOMPLETE_RESULTS'),
])
def test_child_exit_preserved_without_accepting_partial_results(exit_code, expected):
    class Repository:
        claims = 0
        outcomes = []

        def get(self, *args):
            return {'state': 'frozen'}

        def claim(self, *args):
            self.claims += 1
            return {'run_id': 'synthetic'} if self.claims == 1 else None

        def session(self, *args):
            return {'state': 'active'}

        def finish(self, run, owner, state, **kwargs):
            self.outcomes.append((run, state, kwargs['cause']))

        def finalize_terminal(self, *args):
            pass

        def summary(self, *args):
            return {'matrix_complete': False}

        def pause(self, *args):
            pytest.fail('Unexpected systemic failure')

    repo = Repository()
    status, _ = execute_campaign(
        repo, 'synthetic', 'unused', check=lambda *args: None,
        launch=lambda *args: exit_code,
    )
    assert status == 2
    assert repo.outcomes == [('synthetic', 'failed', expected)]
