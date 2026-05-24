import pytest

from epc.models import BearerConfig, ThroughputStats


def test_attach_new_ue(repo):
    repo.attach_ue(1)
    assert repo.ue_exists(1)


def test_attach_creates_default_bearer(repo):
    repo.attach_ue(1)
    state = repo.get_ue(1)
    assert 9 in state.bearers


def test_attach_duplicate_raises(repo):
    repo.attach_ue(1)
    with pytest.raises(ValueError, match="already attached"):
        repo.attach_ue(1)


def test_ue_not_exists_before_attach(repo):
    assert not repo.ue_exists(42)


def test_multiple_ues(repo):
    repo.attach_ue(1)
    repo.attach_ue(2)
    assert repo.ue_exists(1)
    assert repo.ue_exists(2)


def test_attach_default_bearer_initial_state(repo):
    repo.attach_ue(1)
    state = repo.get_ue(1)
    bearer = state.bearers[9]
    assert bearer.bearer_id == 9
    assert bearer.active is False
    assert bearer.protocol is None
    assert bearer.target_bps is None


def test_detach_removes_ue(repo):
    repo.attach_ue(1)
    repo.detach_ue(1)
    assert not repo.ue_exists(1)


def test_detach_nonexistent_raises(repo):
    with pytest.raises(ValueError, match="not found"):
        repo.detach_ue(99)


def test_list_ues_empty(repo):
    assert list(repo.list_ues()) == []


def test_list_ues_sorted(repo):
    repo.attach_ue(3)
    repo.attach_ue(1)
    repo.attach_ue(2)
    assert list(repo.list_ues()) == [1, 2, 3]


def test_list_ues_after_detach(repo):
    repo.attach_ue(1)
    repo.attach_ue(2)
    repo.detach_ue(1)
    assert list(repo.list_ues()) == [2]


def test_get_ue_returns_correct_state(repo):
    repo.attach_ue(5)
    state = repo.get_ue(5)
    assert state.ue_id == 5


def test_get_ue_nonexistent_raises(repo):
    with pytest.raises(ValueError, match="not found"):
        repo.get_ue(99)


def test_save_ue_persists_changes(repo):
    repo.attach_ue(1)
    state = repo.get_ue(1)
    state.bearers[1] = BearerConfig(bearer_id=1)
    repo.save_ue(state)
    reloaded = repo.get_ue(1)
    assert 1 in reloaded.bearers


def test_add_bearer(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    state = repo.get_ue(1)
    assert 2 in state.bearers


def test_add_duplicate_bearer_raises(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    with pytest.raises(ValueError, match="already exists"):
        repo.add_bearer(1, 2)


def test_add_bearer_to_nonexistent_ue_raises(repo):
    with pytest.raises(ValueError, match="not found"):
        repo.add_bearer(99, 1)


def test_delete_bearer(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    repo.delete_bearer(1, 2)
    state = repo.get_ue(1)
    assert 2 not in state.bearers


def test_delete_default_bearer_raises(repo):
    repo.attach_ue(1)
    with pytest.raises(ValueError, match="default bearer"):
        repo.delete_bearer(1, 9)


def test_delete_nonexistent_bearer_raises(repo):
    repo.attach_ue(1)
    with pytest.raises(ValueError, match="not found"):
        repo.delete_bearer(1, 5)


def test_delete_bearer_also_removes_stats(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    repo.update_stats(1, ThroughputStats(bearer_id=2, ue_id=1, bytes_tx=100, bytes_rx=200))
    repo.delete_bearer(1, 2)
    state = repo.get_ue(1)
    assert 2 not in state.stats


def test_delete_bearer_9_on_nonexistent_ue_raises_ue_not_found(repo):
    with pytest.raises(ValueError, match="not found"):
        repo.delete_bearer(99, 9)


def test_update_bearer(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    bearer = BearerConfig(bearer_id=2, protocol="tcp", target_bps=1_000_000, active=True)
    repo.update_bearer(1, bearer)
    state = repo.get_ue(1)
    assert state.bearers[2].protocol == "tcp"
    assert state.bearers[2].active is True
    assert state.bearers[2].target_bps == 1_000_000


def test_update_bearer_nonexistent_ue_raises(repo):
    bearer = BearerConfig(bearer_id=2, protocol="udp", target_bps=500)
    with pytest.raises(ValueError, match="not found"):
        repo.update_bearer(99, bearer)


def test_update_bearer_creates_bearer_without_add(repo):
    repo.attach_ue(1)
    bearer = BearerConfig(bearer_id=5, protocol="tcp")
    repo.update_bearer(1, bearer)
    state = repo.get_ue(1)
    assert 5 in state.bearers


def test_update_stats(repo):
    repo.attach_ue(1)
    repo.add_bearer(1, 2)
    repo.update_stats(1, ThroughputStats(bearer_id=2, ue_id=1, bytes_tx=500, bytes_rx=300))
    state = repo.get_ue(1)
    assert state.stats[2].bytes_tx == 500
    assert state.stats[2].bytes_rx == 300


def test_update_stats_nonexistent_ue_raises(repo):
    stats = ThroughputStats(bearer_id=2, ue_id=99, bytes_tx=100, bytes_rx=50)
    with pytest.raises(ValueError, match="not found"):
        repo.update_stats(99, stats)


def test_update_stats_for_nonexistent_bearer(repo):
    repo.attach_ue(1)
    repo.update_stats(1, ThroughputStats(bearer_id=5, ue_id=1, bytes_tx=100, bytes_rx=50))
    state = repo.get_ue(1)
    assert 5 in state.stats
    assert 5 not in state.bearers


def test_reset_removes_all_ues(repo):
    repo.attach_ue(1)
    repo.attach_ue(2)
    repo.reset_all()
    assert list(repo.list_ues()) == []


def test_reset_empty_repo_does_not_raise(repo):
    repo.reset_all()
    assert list(repo.list_ues()) == []