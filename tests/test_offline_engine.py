from app.offline_engine import run_offline
from app.schemas import AnalyzeRequest, Material


def test_run_offline_generates_appeal():
    req = AnalyzeRequest(
        case_title="测试案例",
        goal="退还差价",
        materials=[Material(name="聊天", content="4月23日商家答应发特快，实际发了标快，额外支付23元。")],
    )
    data = run_offline(req)
    assert data["mode"] == "offline"
    assert len(data["short_appeal_150"]) <= 150
    assert data["timeline"]
    assert "测试案例" in data["summary"]
