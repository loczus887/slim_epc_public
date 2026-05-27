import time

import pytest

import epc.traffic as traffic_module


@pytest.fixture(autouse=True)
def reset_traffic_manager():
    traffic_module.traffic_manager = None
    yield
    if traffic_module.traffic_manager is not None:
        traffic_module.traffic_manager.stop_all()
        traffic_module.traffic_manager = None


def attach(client, ue_id: int = 1):
    return client.post("/ues", json={"ue_id": ue_id})


def add_bearer(client, ue_id: int, bearer_id: int):
    return client.post(f"/ues/{ue_id}/bearers", json={"bearer_id": bearer_id})


def start_traffic(client, ue_id: int, bearer_id: int, **kwargs):
    body = {"protocol": "udp", "Mbps": 1.0, **kwargs}
    return client.post(f"/ues/{ue_id}/bearers/{bearer_id}/traffic", json=body)


def stop_traffic(client, ue_id: int, bearer_id: int):
    return client.delete(f"/ues/{ue_id}/bearers/{bearer_id}/traffic")


# 1. GET /ues

class TestListUes:
    def test_empty_list_returns_200(self, client):
        r = client.get("/ues")
        assert r.status_code == 200

    def test_empty_list_has_correct_shape(self, client):
        body = client.get("/ues").json()
        assert "ues" in body
        assert body["ues"] == []

    def test_attached_ue_appears_in_list(self, client):
        attach(client, 5)
        ues = client.get("/ues").json()["ues"]
        assert 5 in ues

    def test_multiple_ues_appear(self, client):
        for uid in (1, 2, 3):
            attach(client, uid)
        ues = client.get("/ues").json()["ues"]
        assert set(ues) == {1, 2, 3}


# 2. POST /ues

class TestAttachUe:
    def test_attach_returns_200(self, client):
        r = attach(client, 1)
        assert r.status_code == 200

    def test_attach_response_shape(self, client):
        body = attach(client, 1).json()
        assert body["status"] == "attached"
        assert body["ue_id"] == 1

    def test_attach_ue_id_zero_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": 0})
        assert r.status_code == 422

    def test_attach_ue_id_101_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": 101})
        assert r.status_code == 422

    def test_attach_ue_id_negative_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": -1})
        assert r.status_code == 422

    def test_attach_missing_body_returns_422(self, client):
        r = client.post("/ues", json={})
        assert r.status_code == 422

    def test_attach_duplicate_returns_400(self, client):
        attach(client, 7)
        r = attach(client, 7)
        assert r.status_code == 400

    def test_attach_boundary_ue_id_1(self, client):
        assert attach(client, 1).status_code == 200

    def test_attach_boundary_ue_id_100(self, client):
        assert attach(client, 100).status_code == 200


# 3. GET /ues/{ue_id}

class TestGetUe:
    def test_existing_ue_returns_200(self, client):
        attach(client, 2)
        assert client.get("/ues/2").status_code == 200

    def test_ue_response_has_required_fields(self, client):
        attach(client, 2)
        body = client.get("/ues/2").json()
        assert "ue_id" in body
        assert "bearers" in body
        assert "stats" in body

    def test_new_ue_has_default_bearer_9(self, client):
        attach(client, 2)
        body = client.get("/ues/2").json()
        assert "9" in body["bearers"]

    def test_nonexistent_ue_returns_400(self, client):
        r = client.get("/ues/99")
        assert r.status_code == 400

    def test_ue_id_zero_returns_400_or_422(self, client):
        r = client.get("/ues/0")
        assert r.status_code in (400, 422)


# 4. DELETE /ues/{ue_id}

class TestDetachUe:
    def test_detach_existing_returns_200(self, client):
        attach(client, 3)
        assert client.delete("/ues/3").status_code == 200

    def test_detach_response_shape(self, client):
        attach(client, 3)
        body = client.delete("/ues/3").json()
        assert body["status"] == "detached"
        assert body["ue_id"] == 3

    def test_detach_nonexistent_returns_400(self, client):
        assert client.delete("/ues/42").status_code == 400

    def test_detached_ue_no_longer_in_list(self, client):
        attach(client, 3)
        client.delete("/ues/3")
        ues = client.get("/ues").json()["ues"]
        assert 3 not in ues

    def test_double_detach_returns_400(self, client):
        attach(client, 3)
        client.delete("/ues/3")
        r = client.delete("/ues/3")
        assert r.status_code == 400


# 5. POST /ues/{ue_id}/bearers

class TestAddBearer:
    def test_add_bearer_returns_200(self, client):
        attach(client, 1)
        r = add_bearer(client, 1, 1)
        assert r.status_code == 200

    def test_add_bearer_response_shape(self, client):
        attach(client, 1)
        body = add_bearer(client, 1, 1).json()
        assert body["status"] == "bearer_added"
        assert body["ue_id"] == 1
        assert body["bearer_id"] == 1

    def test_add_bearer_id_zero_returns_422(self, client):
        attach(client, 1)
        r = client.post("/ues/1/bearers", json={"bearer_id": 0})
        assert r.status_code == 422

    def test_add_bearer_id_10_returns_422(self, client):
        attach(client, 1)
        r = client.post("/ues/1/bearers", json={"bearer_id": 10})
        assert r.status_code == 422

    def test_add_duplicate_bearer_returns_400(self, client):
        attach(client, 1)
        add_bearer(client, 1, 2)
        r = add_bearer(client, 1, 2)
        assert r.status_code == 400

    def test_add_bearer_to_nonexistent_ue_returns_400(self, client):
        r = add_bearer(client, 99, 1)
        assert r.status_code == 400

    def test_added_bearer_visible_in_get_ue(self, client):
        attach(client, 1)
        add_bearer(client, 1, 3)
        body = client.get("/ues/1").json()
        assert "3" in body["bearers"]

    def test_add_bearer_missing_field_returns_422(self, client):
        attach(client, 1)
        r = client.post("/ues/1/bearers", json={})
        assert r.status_code == 422


# 6. DELETE /ues/{ue_id}/bearers/{bearer_id}

class TestDeleteBearer:
    def test_delete_non_default_bearer_returns_200(self, client):
        attach(client, 1)
        add_bearer(client, 1, 2)
        r = client.delete("/ues/1/bearers/2")
        assert r.status_code == 200

    def test_delete_bearer_response_shape(self, client):
        attach(client, 1)
        add_bearer(client, 1, 2)
        body = client.delete("/ues/1/bearers/2").json()
        assert body["status"] == "bearer_deleted"
        assert body["ue_id"] == 1
        assert body["bearer_id"] == 2

    def test_delete_default_bearer_9_returns_400(self, client):
        attach(client, 1)
        r = client.delete("/ues/1/bearers/9")
        assert r.status_code == 400

    def test_delete_nonexistent_bearer_returns_400(self, client):
        attach(client, 1)
        r = client.delete("/ues/1/bearers/5")
        assert r.status_code == 400

    def test_delete_bearer_on_nonexistent_ue_returns_400(self, client):
        r = client.delete("/ues/99/bearers/9")
        assert r.status_code == 400

    def test_deleted_bearer_not_visible_in_get_ue(self, client):
        attach(client, 1)
        add_bearer(client, 1, 2)
        client.delete("/ues/1/bearers/2")
        body = client.get("/ues/1").json()
        assert "2" not in body["bearers"]


# 7. POST /ues/{ue_id}/bearers/{bearer_id}/traffic

class TestStartTraffic:
    def test_start_traffic_returns_200(self, client):
        attach(client, 1)
        r = start_traffic(client, 1, 9)
        assert r.status_code == 200

    def test_start_traffic_response_shape(self, client):
        attach(client, 1)
        body = start_traffic(client, 1, 9).json()
        assert body["status"] == "traffic_started"
        assert body["ue_id"] == 1
        assert body["bearer_id"] == 9
        assert "target_bps" in body
        assert isinstance(body["target_bps"], int)

    def test_start_traffic_mbps_conversion(self, client):
        attach(client, 1)
        body = client.post(
            "/ues/1/bearers/9/traffic", json={"protocol": "tcp", "Mbps": 2.0}
        ).json()
        assert body["target_bps"] == 2_000_000

    def test_start_traffic_kbps_conversion(self, client):
        attach(client, 1)
        body = client.post(
            "/ues/1/bearers/9/traffic", json={"protocol": "udp", "kbps": 500.0}
        ).json()
        assert body["target_bps"] == 500_000

    def test_start_traffic_bps_conversion(self, client):
        attach(client, 1)
        body = client.post(
            "/ues/1/bearers/9/traffic", json={"protocol": "tcp", "bps": 1234.0}
        ).json()
        assert body["target_bps"] == 1234

    def test_start_traffic_no_throughput_returns_422(self, client):
        attach(client, 1)
        r = client.post("/ues/1/bearers/9/traffic", json={"protocol": "tcp"})
        assert r.status_code == 422

    def test_start_traffic_multiple_throughputs_returns_422(self, client):
        attach(client, 1)
        r = client.post(
            "/ues/1/bearers/9/traffic",
            json={"protocol": "tcp", "Mbps": 1.0, "kbps": 100.0},
        )
        assert r.status_code == 422

    def test_start_traffic_invalid_protocol_returns_422(self, client):
        attach(client, 1)
        r = client.post(
            "/ues/1/bearers/9/traffic", json={"protocol": "quic", "Mbps": 1.0}
        )
        assert r.status_code == 422

    def test_start_traffic_missing_protocol_returns_422(self, client):
        attach(client, 1)
        r = client.post("/ues/1/bearers/9/traffic", json={"Mbps": 1.0})
        assert r.status_code == 422

    def test_start_traffic_on_nonexistent_ue_returns_400(self, client):
        r = start_traffic(client, 99, 9)
        assert r.status_code == 400

    def test_start_traffic_on_nonexistent_bearer_returns_400(self, client):
        attach(client, 1)
        r = start_traffic(client, 1, 5)
        assert r.status_code == 400

    def test_start_traffic_already_running_returns_400(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        r = start_traffic(client, 1, 9)
        assert r.status_code == 400

    def test_start_traffic_tcp_protocol_stored(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9, protocol="tcp", Mbps=1.0)
        body = client.get("/ues/1/bearers/9/traffic").json()
        assert body["protocol"] == "tcp"

    def test_start_traffic_above_limit(self, client):
        attach(client, 1)
        r = start_traffic(client, 1, 9, protocol="tcp", Mbps=101.0)
        assert r.status_code == 422


# 8. DELETE /ues/{ue_id}/bearers/{bearer_id}/traffic

class TestStopTraffic:
    def test_stop_traffic_returns_200(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        r = stop_traffic(client, 1, 9)
        assert r.status_code == 200

    def test_stop_traffic_response_shape(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        body = stop_traffic(client, 1, 9).json()
        assert body["status"] == "traffic_stopped"
        assert body["ue_id"] == 1
        assert body["bearer_id"] == 9

    def test_stop_traffic_on_nonexistent_ue_returns_400(self, client):
        r = stop_traffic(client, 99, 9)
        assert r.status_code == 400

    def test_stop_traffic_on_nonexistent_bearer_returns_400(self, client):
        attach(client, 1)
        r = stop_traffic(client, 1, 5)
        assert r.status_code == 400

    def test_stop_traffic_not_running_still_returns_200(self, client):
        attach(client, 1)
        r = stop_traffic(client, 1, 9)
        assert r.status_code == 200


# 9. GET /ues/{ue_id}/bearers/{bearer_id}/traffic

class TestGetTrafficStats:
    def test_no_stats_yet_returns_200_with_zeros(self, client):
        attach(client, 1)
        r = client.get("/ues/1/bearers/9/traffic")
        assert r.status_code == 200
        body = r.json()
        assert body["tx_bps"] == 0
        assert body["rx_bps"] == 0
        assert body["duration"] == 0

    def test_stats_response_required_fields(self, client):
        attach(client, 1)
        body = client.get("/ues/1/bearers/9/traffic").json()
        for field in ("ue_id", "bearer_id", "tx_bps", "rx_bps", "duration"):
            assert field in body, f"Brak pola: {field}"

    def test_stats_after_traffic_has_nonzero_target_bps(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9, Mbps=5.0, protocol="udp")
        time.sleep(0.1)
        body = client.get("/ues/1/bearers/9/traffic").json()
        assert body["target_bps"] == 5_000_000

    def test_stats_on_nonexistent_ue_returns_400(self, client):
        r = client.get("/ues/99/bearers/9/traffic")
        assert r.status_code == 400

    def test_stats_on_nonexistent_bearer_returns_200_with_zeros(self, client):
        attach(client, 1)
        r = client.get("/ues/1/bearers/5/traffic")
        assert r.status_code == 200
        assert r.json()["tx_bps"] == 0


# 10. GET /ues/stats

class TestGetUesStats:
    def test_returns_200_no_ues(self, client):
        r = client.get("/ues/stats")
        assert r.status_code == 200

    def test_response_shape_required_fields(self, client):
        body = client.get("/ues/stats").json()
        for field in ("scope", "ue_count", "bearer_count", "total_tx_bps", "total_rx_bps"):
            assert field in body, f"Brak pola: {field}"

    def test_scope_all_when_no_ue_id(self, client):
        body = client.get("/ues/stats").json()
        assert body["scope"] == "all"

    def test_scope_per_ue_when_ue_id_given(self, client):
        attach(client, 4)
        body = client.get("/ues/stats?ue_id=4").json()
        assert body["scope"] == "ue:4"

    def test_nonexistent_ue_id_returns_400(self, client):
        r = client.get("/ues/stats?ue_id=77")
        assert r.status_code == 400

    def test_include_details_false_no_details_key(self, client):
        body = client.get("/ues/stats?include_details=false").json()
        assert body.get("details") is None

    def test_include_details_true_returns_dict(self, client):
        attach(client, 1)
        body = client.get("/ues/stats?include_details=true").json()
        assert body["details"] is not None
        assert isinstance(body["details"], dict)

    def test_ue_count_reflects_attached_ues(self, client):
        attach(client, 1)
        attach(client, 2)
        body = client.get("/ues/stats").json()
        assert body["ue_count"] == 2

    def test_bearer_count_is_integer(self, client):
        attach(client, 1)
        body = client.get("/ues/stats").json()
        assert isinstance(body["bearer_count"], int)


# 11. POST /reset

class TestResetAll:
    def test_reset_returns_200(self, client):
        r = client.post("/reset")
        assert r.status_code == 200

    def test_reset_response_shape(self, client):
        body = client.post("/reset").json()
        assert body["status"] == "reset"

    def test_reset_clears_all_ues(self, client):
        attach(client, 1)
        attach(client, 2)
        client.post("/reset")
        ues = client.get("/ues").json()["ues"]
        assert ues == []

    def test_reset_stops_running_traffic(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        client.post("/reset")
        ues = client.get("/ues").json()["ues"]
        assert ues == []

    def test_reset_idempotent(self, client):
        client.post("/reset")
        r = client.post("/reset")
        assert r.status_code == 200


# 12. Pelne przejscia stanow

class TestFullStateTransition:
    def test_full_lifecycle(self, client):
        r = attach(client, 10)
        assert r.status_code == 200, f"Attach failed: {r.json()}"
        assert 10 in client.get("/ues").json()["ues"]

        r = add_bearer(client, 10, 3)
        assert r.status_code == 200, f"Add bearer failed: {r.json()}"

        r = start_traffic(client, 10, 3, protocol="tcp", Mbps=2.0)
        assert r.status_code == 200, f"Start traffic failed: {r.json()}"
        assert r.json()["target_bps"] == 2_000_000

        body = client.get("/ues/10/bearers/3/traffic").json()
        assert body["target_bps"] == 2_000_000

        assert stop_traffic(client, 10, 3).status_code == 200

        assert client.delete("/ues/10/bearers/3").status_code == 200
        assert "3" not in client.get("/ues/10").json()["bearers"]

        assert client.delete("/ues/10").status_code == 200
        assert 10 not in client.get("/ues").json()["ues"]

    def test_delete_bearer_with_active_traffic_returns_200(self, client):
        attach(client, 1)
        add_bearer(client, 1, 2)
        start_traffic(client, 1, 2)
        r = client.delete("/ues/1/bearers/2")
        assert r.status_code == 200

    def test_reattach_after_detach(self, client):
        attach(client, 5)
        client.delete("/ues/5")
        r = attach(client, 5)
        assert r.status_code == 200

    def test_restart_traffic_after_stop(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        stop_traffic(client, 1, 9)
        r = start_traffic(client, 1, 9)
        assert r.status_code == 200

    def test_stats_after_reset_are_empty(self, client):
        attach(client, 1)
        start_traffic(client, 1, 9)
        client.post("/reset")
        body = client.get("/ues/stats").json()
        assert body["ue_count"] == 0
        assert body["total_tx_bps"] == 0


# 13. Routing edge cases

class TestRoutingEdgeCases:
    def test_post_ues_ue_id_string_returns_422(self, client):
        r = client.post("/ues", json={"ue_id": "abc"})
        assert r.status_code == 422

    def test_get_ues_stats_resolved_before_ue_id_path(self, client):
        r = client.get("/ues/stats")
        assert r.status_code == 200
        assert "scope" in r.json()

    def test_wrong_http_method_post_on_ue_detail_returns_405(self, client):
        r = client.post("/ues/1")
        assert r.status_code == 405

    def test_bearer_id_zero_in_path_returns_400_or_422(self, client):
        attach(client, 1)
        r = client.delete("/ues/1/bearers/0")
        assert r.status_code in (400, 422)

    def test_unknown_route_returns_404(self, client):
        r = client.get("/nonexistent")
        assert r.status_code == 404