import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from epc.api import (
    attach_ue, detach_ue, add_bearer, delete_bearer,
    start_traffic, stop_traffic, get_ues_stats,
    list_ues, get_ue, reset_all
)

def test_attach_ue_success():
    mock_repo = MagicMock()
    resp = attach_ue(body=MagicMock(ue_id=1), repo=mock_repo)
    assert resp.status == "attached"

def test_attach_ue_error_400():
    mock_repo = MagicMock()
    mock_repo.attach_ue.side_effect = ValueError("UE already attached")
    with pytest.raises(HTTPException) as exc:
        attach_ue(body=MagicMock(ue_id=1), repo=mock_repo)
    assert exc.value.status_code == 400

def test_detach_ue_success():
    mock_repo = MagicMock()
    resp = detach_ue(ue_id=1, repo=mock_repo)
    assert resp.status == "detached"

def test_detach_ue_error_400():
    mock_repo = MagicMock()
    mock_repo.detach_ue.side_effect = ValueError("UE not found")
    with pytest.raises(HTTPException) as exc:
        detach_ue(ue_id=1, repo=mock_repo)
    assert exc.value.status_code == 400

def test_add_bearer_success():
    mock_repo = MagicMock()
    resp = add_bearer(ue_id=1, body=MagicMock(bearer_id=5), repo=mock_repo)
    assert resp.status == "bearer_added"

def test_add_bearer_error_400():
    mock_repo = MagicMock()
    mock_repo.add_bearer.side_effect = ValueError("Bearer already exists")
    with pytest.raises(HTTPException) as exc:
        add_bearer(ue_id=1, body=MagicMock(bearer_id=5), repo=mock_repo)
    assert exc.value.status_code == 400

@patch("epc.api.get_traffic_manager")
def test_delete_bearer_success_stops_traffic(mock_get_tm):
    mock_repo, mock_tm = MagicMock(), MagicMock()
    mock_get_tm.return_value = mock_tm
    
    mock_repo.get_ue.return_value = MagicMock(bearers={5: MagicMock()})
    mock_tm.is_running.return_value = True
    
    resp = delete_bearer(ue_id=1, bearer_id=5, repo=mock_repo)
    
    mock_tm.stop.assert_called_once_with(1, 5)
    mock_repo.delete_bearer.assert_called_once_with(1, 5)
    assert resp.status == "bearer_deleted"

def test_delete_bearer_error_400():
    mock_repo = MagicMock()
    mock_repo.get_ue.side_effect = ValueError("UE not found")
    with pytest.raises(HTTPException) as exc:
        delete_bearer(ue_id=1, bearer_id=5, repo=mock_repo)
    assert exc.value.status_code == 400

@patch("epc.api.get_traffic_manager")
def test_start_traffic_success(mock_get_tm):
    mock_repo = MagicMock()
    mock_state = MagicMock(bearers={5: MagicMock()}, stats={})
    mock_repo.get_ue.return_value = mock_state
    
    resp = start_traffic(ue_id=1, bearer_id=5, body=MagicMock(protocol="udp"), repo=mock_repo)
    assert resp.status == "traffic_started"

@patch("epc.api.get_traffic_manager")
def test_start_traffic_error_400(mock_get_tm):
    mock_repo = MagicMock()
    mock_get_tm.return_value.start.side_effect = ValueError("Traffic already running")
    mock_repo.get_ue.return_value = MagicMock(bearers={5: MagicMock()}, stats={})
    
    with pytest.raises(HTTPException) as exc:
        start_traffic(ue_id=1, bearer_id=5, body=MagicMock(protocol="udp"), repo=mock_repo)
    assert exc.value.status_code == 400

@patch("epc.api.get_traffic_manager")
def test_stop_traffic_success(mock_get_tm):
    mock_repo = MagicMock()
    mock_repo.get_ue.return_value = MagicMock(bearers={5: MagicMock()})
    
    resp = stop_traffic(ue_id=1, bearer_id=5, repo=mock_repo)
    assert resp.status == "traffic_stopped"

def test_stop_traffic_error_400():
    mock_repo = MagicMock()
    mock_repo.get_ue.return_value = MagicMock(bearers={}) #brak bearera
    
    with pytest.raises(HTTPException) as exc:
        stop_traffic(ue_id=1, bearer_id=5, repo=mock_repo)
    assert exc.value.status_code == 400

@patch("epc.api.get_traffic_manager")
def test_get_ues_stats_scope_all(mock_get_tm):
    mock_repo = MagicMock()
    mock_repo.list_ues.return_value = [1, 2]
    mock_repo.get_ue.return_value = MagicMock(stats={})
    
    resp = get_ues_stats(repo=mock_repo, ue_id=None, include_details=False)
    assert resp.scope == "all"
    assert resp.ue_count == 2

@patch("epc.api.get_traffic_manager")
def test_get_ues_stats_scope_ue_and_details(mock_get_tm):
    mock_repo = MagicMock()
    mock_repo.ue_exists.return_value = True
    
    mock_stats = MagicMock(bytes_tx=100, bytes_rx=50, start_ts=1000, last_update_ts=1010)
    mock_repo.get_ue.return_value = MagicMock(stats={9: mock_stats})
    mock_get_tm.return_value.is_running.return_value = False
    
    resp = get_ues_stats(repo=mock_repo, ue_id=1, include_details=True)
    
    assert resp.scope == "ue:1"
    assert resp.details is not None
    assert "1" in resp.details and "9" in resp.details["1"]

def test_get_ues_stats_error_400():
    mock_repo = MagicMock()
    mock_repo.ue_exists.return_value = False #UE nie istnieje
    with pytest.raises(HTTPException) as exc:
        get_ues_stats(repo=mock_repo, ue_id=99)
    assert exc.value.status_code == 400

def test_list_ues_success():
    mock_repo = MagicMock()
    list_ues(repo=mock_repo)
    mock_repo.list_ues.assert_called_once()

def test_get_ue_error_400():
    mock_repo = MagicMock()
    mock_repo.get_ue.side_effect = ValueError("Not found")
    with pytest.raises(HTTPException) as exc:
        get_ue(ue_id=1, repo=mock_repo)
    assert exc.value.status_code == 400

@patch("epc.api.get_traffic_manager")
def test_reset_all_success(mock_get_tm):
    mock_repo = MagicMock()
    reset_all(repo=mock_repo)
    mock_get_tm.return_value.stop_all.assert_called_once()
    mock_repo.reset_all.assert_called_once()