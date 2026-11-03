import json

from common.error_codes import ErrorCode


def _is_event_stream(content_type: str) -> bool:
    return "text/event-stream" in content_type


def parse_sse_events(raw: str) -> list[dict]:
    """把 text/event-stream 文本拆成结构化事件，方便断言。"""
    events = []
    for block in raw.split("\n\n"):
        if not block.strip():
            continue
        event = {"event": None, "id": None, "retry": None, "data": "", "comments": []}
        data_lines = []
        for line in block.splitlines():
            if line.startswith(":"):
                event["comments"].append(line[1:].strip())
            elif line.startswith("event:"):
                event["event"] = line.split(":", 1)[1].strip()
            elif line.startswith("id:"):
                event["id"] = line.split(":", 1)[1].strip()
            elif line.startswith("retry:"):
                event["retry"] = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data_lines.append(line.split(":", 1)[1].lstrip())
        event["data"] = "\n".join(data_lines)
        if event["data"]:
            try:
                event["json"] = json.loads(event["data"])
            except json.JSONDecodeError:
                event["json"] = None
        else:
            event["json"] = None
        events.append(event)
    return events


async def read_sse_body(response) -> str:
    chunks = []
    async for chunk in response.aiter_text():
        chunks.append(chunk)
    return "".join(chunks)


async def test_sse_overview_uses_unified_response(client):
    response = await client.get("/api/v1/sse/")

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == 0
    assert body["data"]["protocol"] == "Server-Sent Events"
    assert body["data"]["content_type"] == "text/event-stream"
    assert "heartbeat" in body["data"]["endpoints"]
    assert "progress" in body["data"]["endpoints"]


async def test_heartbeat_stream_sends_typed_events(client):
    async with client.stream(
        "GET",
        "/api/v1/sse/heartbeat",
        params={"ticks": 3, "interval_ms": 10},
    ) as response:
        assert response.status_code == 200
        assert _is_event_stream(response.headers["content-type"])
        raw = await read_sse_body(response)

    events = parse_sse_events(raw)
    named = [item["event"] for item in events if item["event"]]
    assert named[0] == "ready"
    assert named.count("heartbeat") == 3
    assert named[-1] == "done"

    heartbeat_payloads = [
        item["json"] for item in events if item["event"] == "heartbeat"
    ]
    assert [item["tick"] for item in heartbeat_payloads] == [1, 2, 3]
    assert events[1]["retry"] == "3000"


async def test_heartbeat_resumes_from_last_event_id(client):
    async with client.stream(
        "GET",
        "/api/v1/sse/heartbeat",
        params={"ticks": 5, "interval_ms": 10},
        headers={"Last-Event-ID": "3"},
    ) as response:
        assert _is_event_stream(response.headers["content-type"])
        raw = await read_sse_body(response)

    ticks = [
        item["json"]["tick"]
        for item in parse_sse_events(raw)
        if item["event"] == "heartbeat"
    ]
    assert ticks == [4, 5]


async def test_progress_stream_reaches_completion(client):
    async with client.stream(
        "GET",
        "/api/v1/sse/progress",
        params={"steps": 4, "interval_ms": 10},
    ) as response:
        assert response.status_code == 200
        assert _is_event_stream(response.headers["content-type"])
        raw = await read_sse_body(response)

    events = parse_sse_events(raw)
    named = [item["event"] for item in events if item["event"]]
    assert named[0] == "ready"
    assert named.count("progress") == 4
    assert named[-1] == "done"

    percents = [
        item["json"]["percent"]
        for item in events
        if item["event"] == "progress"
    ]
    assert percents[0] > 0
    assert percents[-1] == 100
    assert events[-1]["json"]["status"] == "success"


async def test_channel_demo_stream_emits_messages_without_redis(client):
    async with client.stream(
        "GET",
        "/api/v1/sse/channel/demo",
        params={"timeout_ms": 80, "demo": True},
    ) as response:
        assert response.status_code == 200
        assert _is_event_stream(response.headers["content-type"])
        raw = await read_sse_body(response)

    events = parse_sse_events(raw)
    named = [item["event"] for item in events if item["event"]]
    assert "ready" in named
    messages = [item["json"]["message"] for item in events if item["event"] == "message"]
    assert messages == ["demo-1", "demo-2"]
    assert named[-1] == "done"


async def test_channel_publish_returns_unified_response(client):
    response = await client.post(
        "/api/v1/sse/channel/news",
        json={"message": "hello-sse", "extra": {"from": "test"}},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "消息已发布"
    assert body["data"]["channel"] == "news"
    assert body["data"]["delivered"] == 0
    assert "redis_published" in body["data"]


async def test_memory_event_hub_delivers_to_subscriber():
    from api.v1.sse import MemoryEventHub

    hub = MemoryEventHub()
    queue = hub.subscribe("live1")
    delivered = await hub.publish("live1", {"message": "hello-sse"})

    assert delivered == 1
    assert queue.get_nowait()["message"] == "hello-sse"
    hub.unsubscribe("live1", queue)


async def test_channel_rejects_invalid_name(client):
    response = await client.post(
        "/api/v1/sse/channel/invalid name",
        json={"message": "nope"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == ErrorCode.PARAMS_INVALID.code
