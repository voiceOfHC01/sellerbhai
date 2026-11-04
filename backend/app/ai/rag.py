import math
from typing import List, Dict, Any, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.schema import Product, ProductVariant, KBDocument, KBChunk
from app.ai.providers import get_embedding_provider

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2 or len(v1) != len(v2):
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a, b in zip(v1, v2)))
    norm_b = math.sqrt(sum(b * b for a, b in zip(v1, v2)))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

async def reindex_all_knowledge(db: AsyncSession) -> Dict[str, Any]:
    """
    Chunks all active catalog products, variants, FAQs, and policies,
    embeds them, and saves to kb_chunks table.
    """
    embedding_provider = get_embedding_provider()

    # Clear existing chunks
    await db.execute(delete(KBChunk))
    await db.commit()

    chunk_entries = []

    # 1. Index Products & Variants
    res = await db.execute(
        select(Product).options(selectinload(Product.variants)).where(Product.is_active == True)
    )
    products = res.scalars().all()

    for p in products:
        variant_texts = []
        for v in p.variants:
            if v.is_active:
                details = f"SKU: {v.sku}, Title: {v.title}, Price: {v.price} BDT, Stock: {v.stock}"
                if v.color:
                    details += f", Color: {v.color}"
                if v.size:
                    details += f", Size: {v.size}"
                variant_texts.append(details)

        v_summary = "; ".join(variant_texts) if variant_texts else "No variants specified"
        alias_str = f"Aliases / Alternate Spellings: {p.aliases}\n" if p.aliases else ""
        chunk_text = (
            f"Product: {p.title}\n"
            f"{alias_str}"
            f"Category: {p.category or 'General'}\n"
            f"Base Price: {p.base_price} BDT\n"
            f"Description: {p.description or 'N/A'}\n"
            f"Available Variants: {v_summary}"
        )
        chunk_entries.append({
            "product_id": p.id,
            "document_id": None,
            "chunk_text": chunk_text,
            "metadata": {
                "type": "product",
                "title": p.title,
                "price": p.base_price,
                "category": p.category
            }
        })

    # 2. Index KB Documents (FAQs and Policies)
    res_kb = await db.execute(select(KBDocument).where(KBDocument.is_active == True))
    docs = res_kb.scalars().all()

    for d in docs:
        chunk_text = (
            f"Document Type: {d.doc_type.upper()}\n"
            f"Title: {d.title}\n"
            f"Content: {d.content}"
        )
        chunk_entries.append({
            "product_id": None,
            "document_id": d.id,
            "chunk_text": chunk_text,
            "metadata": {
                "type": d.doc_type,
                "title": d.title
            }
        })

    if not chunk_entries:
        return {"status": "success", "chunks_indexed": 0}

    # Generate Embeddings
    all_texts = [c["chunk_text"] for c in chunk_entries]
    embeddings = await embedding_provider.embed_texts(all_texts)

    # Save Chunks
    for item, emb in zip(chunk_entries, embeddings):
        chunk = KBChunk(
            product_id=item["product_id"],
            document_id=item["document_id"],
            chunk_text=item["chunk_text"],
            embedding=emb,
            chunk_metadata=item["metadata"]
        )
        db.add(chunk)

    await db.commit()
    return {"status": "success", "chunks_indexed": len(chunk_entries)}

async def retrieve_relevant_knowledge(db: AsyncSession, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
    """
    Hybrid semantic retrieval: vector similarity + lexical keyword boosting.
    """
    res = await db.execute(select(KBChunk))
    chunks = res.scalars().all()

    if not chunks:
        return []

    embedding_provider = get_embedding_provider()
    query_vector = await embedding_provider.embed_text(query)
    q_words = set(query.lower().split())

    # Phonetic & spelling variant expansions
    SYNONYM_GROUPS = [
        {"panjabi", "punjabi", "পাঞ্জাবি", "panzabi"},
        {"polo", "পোলো", "shirt", "শার্ট", "tshirt", "টি-শার্ট"},
        {"wallet", "ওয়ালেট", "মানিব্যাগ", "purse", "moneybag"},
        {"price", "দাম", "dam", "koto", "rate", "টাকা", "taka"},
        {"delivery", "ডেলিভারি", "charge", "fee", "dhaka", "ঢাকা"},
        {"size", "সাইজ", "color", "রং", "কালার"}
    ]
    expanded_words = set(q_words)
    for w in q_words:
        for group in SYNONYM_GROUPS:
            if w in group:
                expanded_words.update(group)

    scored_chunks = []
    for c in chunks:
        emb = c.embedding
        if isinstance(emb, str):
            import json
            try:
                emb = json.loads(emb)
            except Exception:
                emb = []

        # Vector score
        vec_score = cosine_similarity(query_vector, emb) if emb else 0.0

        # Lexical score with expanded tokens
        chunk_lower = c.chunk_text.lower()
        matched_words = sum(1 for w in expanded_words if len(w) > 2 and w in chunk_lower)
        lexical_boost = min(0.5, matched_words * 0.12)

        total_score = vec_score * 0.6 + lexical_boost

        scored_chunks.append({
            "id": c.id,
            "chunk_text": c.chunk_text,
            "score": round(total_score, 4),
            "metadata": c.chunk_metadata or {},
            "product_id": c.product_id,
            "document_id": c.document_id
        })

    scored_chunks.sort(key=lambda x: x["score"], reverse=True)
    return scored_chunks[:top_k]
