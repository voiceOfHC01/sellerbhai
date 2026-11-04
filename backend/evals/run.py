import asyncio
import os
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

# Ensure terminal outputs UTF-8 cleanly without cp1252 exceptions
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.database import Base
from app.models.schema import AdminUser, Product, ProductVariant, KBDocument, Setting, Thread, Message, Customer
from app.core.security import get_password_hash
from app.ai.rag import reindex_all_knowledge
from app.ai.engine import process_chat_message
from app.ai.prompts import PROMPT_VERSION
from evals.dataset import EVAL_CONVERSATIONS
from evals.rubric import evaluate_case_response

TEST_DB_URL = "sqlite+aiosqlite:///:memory:"

async def setup_eval_database():
    engine = create_async_engine(TEST_DB_URL, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        # Seed Settings
        session.add_all([
            Setting(key="store_name", value="SellerBhai Shop", description="Store Name"),
            Setting(key="brand_tone", value="Polite, respectful, concise Bangladeshi assistant", description="Brand Tone"),
            Setting(key="delivery_inside_dhaka", value="80", description="Dhaka delivery fee"),
            Setting(key="delivery_outside_dhaka", value="150", description="Outside Dhaka delivery fee"),
            Setting(key="price_format", value="symbol", description="Price display format"),
            Setting(key="fast_llm_model", value="gemini-1.5-flash", description="Fast model"),
            Setting(key="reply_llm_model", value="gemini-1.5-pro", description="Reply model")
        ])

        # Seed Products with aliases
        polo = Product(
            title="Premium Cotton Polo Shirt",
            description="100% combed cotton polo shirt. Soft, breathable, perfect for summer.",
            category="Men's Fashion",
            base_price=850.0,
            aliases="polo, পোলো, polo shirt, t-shirt, cotton polo",
            is_active=True
        )
        session.add(polo)
        await session.flush()

        session.add_all([
            ProductVariant(product_id=polo.id, sku="POLO-BLK-M", title="Black Polo M", price=850.0, stock=10, color="Black", size="M", is_active=True),
            ProductVariant(product_id=polo.id, sku="POLO-WHT-L", title="White Polo L", price=850.0, stock=5, color="White", size="L", is_active=True),
            ProductVariant(product_id=polo.id, sku="POLO-NVY-XL", title="Navy Polo XL", price=850.0, stock=0, color="Navy", size="XL", is_active=True)
        ])

        # Seed KB Policies
        session.add_all([
            KBDocument(
                doc_type="policy",
                title="Delivery Policy",
                content="ঢাকার ভেতরে ডেলিভারি চার্জ ৮০ টাকা, ঢাকার বাইরে ১৫০ টাকা। ক্যাশ অন ডেলিভারি প্রযোজ্য। ২-৩ দিনের মধ্যে ডেলিভারি সম্পন্ন হয়।",
                is_active=True
            ),
            KBDocument(
                doc_type="policy",
                title="Return and Exchange Policy",
                content="ডেলিভারির সময় পণ্য চেক করে নেবেন। কোনো ত্রুটি থাকলে ৩ দিনের মধ্যে ফ্রি এক্সচেঞ্জ সুবিধা রয়েছে।",
                is_active=True
            )
        ])

        await session.commit()
        await reindex_all_knowledge(session)

    return engine, session_factory

async def run_all_evaluations():
    print(f"\n=======================================================")
    print(f"  SellerBhai AI Customer Reply Quality Evaluation")
    print(f"  Prompt Version: {PROMPT_VERSION} | Total Cases: {len(EVAL_CONVERSATIONS)}")
    print(f"=======================================================\n")

    engine, session_factory = await setup_eval_database()
    results = []
    category_stats = {}

    start_eval_time = time.time()

    for idx, case in enumerate(EVAL_CONVERSATIONS, 1):
        cat = case["category"]
        if cat not in category_stats:
            category_stats[cat] = {"total": 0, "passed": 0, "failed": 0}
        category_stats[cat]["total"] += 1

        async with session_factory() as session:
            # Create a dedicated Customer and Thread for this evaluation
            customer = Customer(name="Eval Customer", phone="01700000000", channel="eval")
            session.add(customer)
            await session.flush()

            thread = Thread(customer_id=customer.id, channel="eval", status="active", metadata_json={})
            session.add(thread)
            await session.commit()
            await session.refresh(thread)

            last_output = {}
            for user_text in case["messages"]:
                last_output = await process_chat_message(
                    db=session,
                    customer_message=user_text,
                    thread_id=thread.id,
                    customer_name="Eval Customer"
                )

            # Evaluate the final reply
            actual_reply = last_output.get("reply", "")
            tool_calls = last_output.get("tool_calls", [])
            handover = last_output.get("handover_triggered", False)
            status = last_output.get("thread_status", "active")

            passed, violations = evaluate_case_response(
                case=case,
                actual_reply=actual_reply,
                tool_calls=tool_calls,
                handover_triggered=handover,
                thread_status=status
            )

            if passed:
                category_stats[cat]["passed"] += 1
                status_icon = "PASS"
            else:
                category_stats[cat]["failed"] += 1
                status_icon = "FAIL"

            results.append({
                "id": case["id"],
                "category": cat,
                "passed": passed,
                "violations": violations,
                "input_messages": case["messages"],
                "actual_reply": actual_reply,
                "handover_triggered": handover,
                "tool_calls": [tc.get("tool") for tc in tool_calls]
            })

            print(f"[{idx:02d}/{len(EVAL_CONVERSATIONS)}] {case['id']:<26} [{status_icon}]")
            if not passed:
                for v in violations:
                    print(f"     -> Violation: {v}")

    total_time = round(time.time() - start_eval_time, 2)
    total_cases = len(EVAL_CONVERSATIONS)
    total_passed = sum(c["passed"] for c in category_stats.values())
    overall_pass_rate = round((total_passed / total_cases) * 100, 1)

    # Print Summary Table
    print(f"\n=======================================================")
    print(f"               EVALUATION SUMMARY TABLE                ")
    print(f"=======================================================")
    print(f"{'Category':<24} | {'Total':<6} | {'Passed':<6} | {'Failed':<6} | {'Pass Rate':<8}")
    print(f"-------------------------+--------+--------+--------+----------")
    for cat, stats in sorted(category_stats.items()):
        rate = round((stats["passed"] / stats["total"]) * 100, 1)
        print(f"{cat:<24} | {stats['total']:<6} | {stats['passed']:<6} | {stats['failed']:<6} | {rate:>7}%")
    print(f"-------------------------+--------+--------+--------+----------")
    print(f"{'OVERALL TOTAL':<24} | {total_cases:<6} | {total_passed:<6} | {total_cases - total_passed:<6} | {overall_pass_rate:>7}%")
    print(f"Execution Time: {total_time}s\n")

    # Weakest Cases
    failed_cases = [r for r in results if not r["passed"]]
    print(f"--- Top Weakest / Failed Cases ({len(failed_cases)} total) ---")
    for idx, fc in enumerate(failed_cases[:5], 1):
        print(f"\n[{idx}] Case ID: {fc['id']} (Category: {fc['category']})")
        print(f"    User Message: {fc['input_messages']}")
        print(f"    AI Reply: {fc['actual_reply']}")
        print(f"    Violations: {fc['violations']}")

    # Save Results per prompt version
    evals_dir = os.path.dirname(os.path.abspath(__file__))
    res_path = os.path.join(evals_dir, f"results_{PROMPT_VERSION}.json")
    with open(res_path, "w", encoding="utf-8") as f:
        json.dump({
            "prompt_version": PROMPT_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_cases": total_cases,
            "total_passed": total_passed,
            "overall_pass_rate": overall_pass_rate,
            "category_stats": category_stats,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\nResults successfully saved to: {res_path}\n")

    await engine.dispose()
    return overall_pass_rate, category_stats, results

if __name__ == "__main__":
    asyncio.run(run_all_evaluations())
