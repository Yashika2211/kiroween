import asyncio

from necromancer.events import EventBus


async def test_replay_then_live_then_close() -> None:
    bus = EventBus()
    await bus.publish("j", "log", {"message": "one"})
    received: list[str] = []

    async def consume() -> None:
        async for event in bus.subscribe("j"):
            received.append(event.data["message"])

    task = asyncio.create_task(consume())
    await asyncio.sleep(0)
    await bus.publish("j", "log", {"message": "two"})
    await asyncio.sleep(0)
    bus.close("j")
    await asyncio.wait_for(task, 1)
    assert received == ["one", "two"]


async def test_resume_after_sequence_number() -> None:
    bus = EventBus()
    for i in range(5):
        await bus.publish("j", "log", {"i": i})
    bus.close("j")
    seen = [e.data["i"] async for e in bus.subscribe("j", after=3)]
    assert seen == [3, 4]


async def test_jobs_are_isolated() -> None:
    bus = EventBus()
    await bus.publish("a", "log", {})
    await bus.publish("b", "log", {})
    assert [e.job_id for e in bus.history("a")] == ["a"]
    assert bus.history("a")[0].seq == 1 and bus.history("b")[0].seq == 1
