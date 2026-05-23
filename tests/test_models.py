import pytest
from pydantic import ValidationError

from epc.models import (
    AddBearerRequest,
    AggregatedStatsResponse,
    AttachResponse,
    AttachUERequest,
    BearerAddResponse,
    BearerConfig,
    BearerDeleteResponse,
    DetachResponse,
    StartTrafficRequest,
    ThroughputStats,
    TrafficStartResponse,
    TrafficStatsResponse,
    TrafficStopResponse,
    UEDisplayResponse,
    UEListResponse,
    UEState,
)

class TestBearerConfig:
    def test_valid_bearer(self):
        b = BearerConfig(bearer_id=1)
        assert b.bearer_id == 1
        assert b.active is False
        assert b.protocol is None

    def test_bearer_id_max(self):
        b = BearerConfig(bearer_id=9)
        assert b.bearer_id == 9

    def test_bearer_id_too_low(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=0)

    def test_bearer_id_too_high(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=10)

    def test_valid_protocol_tcp(self):
        b = BearerConfig(bearer_id=1, protocol="tcp")
        assert b.protocol == "tcp"

    def test_valid_protocol_udp(self):
        b = BearerConfig(bearer_id=1, protocol="udp")
        assert b.protocol == "udp"

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            BearerConfig(bearer_id=1, protocol="ftp")

class TestUEState:
    def test_valid_ue(self):
        ue = UEState(ue_id=1)
        assert ue.ue_id == 1
        assert ue.bearers == {}
        assert ue.stats == {}

    def test_ue_id_max(self):
        ue = UEState(ue_id=100)
        assert ue.ue_id == 100

    def test_ue_id_zero_valid(self):
        ue = UEState(ue_id=0)
        assert ue.ue_id == 0

    def test_ue_id_too_low(self):
        with pytest.raises(ValidationError):
            UEState(ue_id=-1)

    def test_ue_id_too_high(self):
        with pytest.raises(ValidationError):
            UEState(ue_id=101)

    def test_bearers_default_none_becomes_dict(self):
        ue = UEState(ue_id=1, bearers=None)
        assert ue.bearers == {}

    def test_stats_default_none_becomes_dict(self):
        ue = UEState(ue_id=1, stats=None)
        assert ue.stats == {}

class TestAttachUERequest:
    def test_valid(self):
        r = AttachUERequest(ue_id=50)
        assert r.ue_id == 50

    def test_ue_id_zero_valid(self):
        r = AttachUERequest(ue_id=0)
        assert r.ue_id == 0

    def test_ue_id_too_low(self):
        with pytest.raises(ValidationError):
            AttachUERequest(ue_id=-1)

    def test_ue_id_too_high(self):
        with pytest.raises(ValidationError):
            AttachUERequest(ue_id=101)

class TestAddBearerRequest:
    def test_valid(self):
        r = AddBearerRequest(bearer_id=5)
        assert r.bearer_id == 5

    def test_bearer_id_too_low(self):
        with pytest.raises(ValidationError):
            AddBearerRequest(bearer_id=0)

    def test_bearer_id_too_high(self):
        with pytest.raises(ValidationError):
            AddBearerRequest(bearer_id=10)

class TestStartTrafficRequest:
    def test_mbps(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=2.0)
        assert r.target_bps() == 2_000_000

    def test_kbps(self):
        r = StartTrafficRequest(protocol="udp", kbps=500.0)
        assert r.target_bps() == 500_000

    def test_bps(self):
        r = StartTrafficRequest(protocol="tcp", bps=1234.0)
        assert r.target_bps() == 1234

    def test_no_throughput_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp")

    def test_two_throughputs_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=1.0, kbps=500.0)

    def test_all_throughputs_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=1.0, kbps=500.0, bps=100.0)

    def test_invalid_protocol(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="icmp", Mbps=1.0)

    def test_protocol_tcp_valid(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=1.0)
        assert r.protocol == "tcp"

    def test_protocol_udp_valid(self):
        r = StartTrafficRequest(protocol="udp", Mbps=1.0)
        assert r.protocol == "udp"

    def test_mbps_fractional(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=0.5)
        assert r.target_bps() == 500_000

    def test_bps_zero(self):
        r = StartTrafficRequest(protocol="tcp", bps=0.0)
        assert r.target_bps() == 0

    def test_mbps_max_valid(self):
        r = StartTrafficRequest(protocol="tcp", Mbps=100.0)
        assert r.target_bps() == 100_000_000

    def test_mbps_over_limit_raises(self):
        with pytest.raises(ValidationError):
            StartTrafficRequest(protocol="tcp", Mbps=101.0)

class TestThroughputStats:
    def test_defaults(self):
        s = ThroughputStats(bearer_id=1, ue_id=1)
        assert s.bytes_tx == 0
        assert s.bytes_rx == 0
        assert s.start_ts is None
        assert s.last_update_ts is None
        assert s.protocol is None
        assert s.target_bps is None

    def test_set_all_fields(self):
        s = ThroughputStats(
            bearer_id=2,
            ue_id=5,
            bytes_tx=1000,
            bytes_rx=2000,
            start_ts=1000.0,
            last_update_ts=1010.0,
            protocol="tcp",
            target_bps=1_000_000,
        )
        assert s.bearer_id == 2
        assert s.ue_id == 5
        assert s.bytes_tx == 1000
        assert s.bytes_rx == 2000
        assert s.start_ts == 1000.0
        assert s.last_update_ts == 1010.0
        assert s.protocol == "tcp"
        assert s.target_bps == 1_000_000

    def test_bytes_accumulate(self):
        s = ThroughputStats(bearer_id=1, ue_id=1, bytes_tx=500, bytes_rx=300)
        s.bytes_tx += 100
        s.bytes_rx += 200
        assert s.bytes_tx == 600
        assert s.bytes_rx == 500

class TestResponseModels:
    def test_attach_response(self):
        r = AttachResponse(status="attached", ue_id=1)
        assert r.status == "attached"
        assert r.ue_id == 1

    def test_detach_response(self):
        r = DetachResponse(status="detached", ue_id=1)
        assert r.status == "detached"
        assert r.ue_id == 1

    def test_bearer_add_response(self):
        r = BearerAddResponse(status="added", ue_id=1, bearer_id=2)
        assert r.status == "added"
        assert r.bearer_id == 2

    def test_bearer_delete_response(self):
        r = BearerDeleteResponse(status="deleted", ue_id=1, bearer_id=2)
        assert r.status == "deleted"
        assert r.bearer_id == 2

    def test_traffic_start_response(self):
        r = TrafficStartResponse(status="started", ue_id=1, bearer_id=2, target_bps=1_000_000)
        assert r.target_bps == 1_000_000

    def test_traffic_stop_response(self):
        r = TrafficStopResponse(status="stopped", ue_id=1, bearer_id=2)
        assert r.status == "stopped"

    def test_traffic_stats_response_defaults(self):
        r = TrafficStatsResponse(ue_id=1, bearer_id=2, tx_bps=100, rx_bps=200, duration=5.0)
        assert r.protocol is None
        assert r.target_bps is None

    def test_traffic_stats_response_full(self):
        r = TrafficStatsResponse(
            ue_id=1, bearer_id=2,
            protocol="udp", target_bps=500_000,
            tx_bps=480_000, rx_bps=490_000,
            duration=10.0,
        )
        assert r.protocol == "udp"
        assert r.duration == 10.0

    def test_ue_list_response(self):
        r = UEListResponse(ues=[1, 2, 3])
        assert r.ues == [1, 2, 3]

    def test_ue_list_response_empty(self):
        r = UEListResponse(ues=[])
        assert r.ues == []

    def test_ue_display_response_inherits_ue_state(self):
        r = UEDisplayResponse(ue_id=5)
        assert r.ue_id == 5
        assert r.bearers == {}
        assert r.stats == {}

    def test_aggregated_stats_response_no_details(self):
        r = AggregatedStatsResponse(
            scope="all", ue_count=3, bearer_count=5,
            total_tx_bps=1000, total_rx_bps=2000,
        )
        assert r.scope == "all"
        assert r.details is None

    def test_aggregated_stats_response_with_details(self):
        r = AggregatedStatsResponse(
            scope="ue:1", ue_count=1, bearer_count=2,
            total_tx_bps=500, total_rx_bps=600,
            details={"1": {"tx_bps": 500, "rx_bps": 600}},
        )
        assert r.scope == "ue:1"
        assert r.details is not None
        assert "1" in r.details
