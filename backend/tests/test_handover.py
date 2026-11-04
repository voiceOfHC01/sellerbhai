import pytest
from app.ai.engine import process_chat_message
from app.ai.tools import execute_handover_to_human
from app.models.schema import Thread
from sqlalchemy import select

@pytest.mark.asyncio
async def test_handover_direct_tool_execution(test_db):
    async with test_db() as session:
        # Create a thread
        thread = Thread(customer_id=1, channel="web_test", status="active")
        session.add(thread)
        await session.commit()
        await session.refresh(thread)

        # Trigger handover tool
        res = await execute_handover_to_human(session, reason="Customer is angry", thread_id=thread.id)
        assert res["handover_triggered"] is True
        assert res["status"] == "human_takeover"

        # Verify thread status updated in DB
        t_res = await session.execute(select(Thread).where(Thread.id == thread.id))
        updated_thread = t_res.scalars().first()
        assert updated_thread.status == "human_takeover"
        assert updated_thread.handover_reason == "Customer is angry"

@pytest.mark.asyncio
async def test_handover_triggers_on_agent_request(test_db):
    async with test_db() as session:
        res = await process_chat_message(
            db=session,
            customer_message="I want to speak with a human agent or manager immediately.",
            customer_name="Test Customer"
        )
        assert res["handover_triggered"] is True
        assert res["thread_status"] == "human_takeover"
        assert len(res["tool_calls"]) > 0
        assert res["tool_calls"][0]["tool"] == "handover_to_human"
