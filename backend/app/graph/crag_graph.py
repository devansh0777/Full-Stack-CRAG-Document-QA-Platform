import json
from typing import Any, Literal, TypedDict

from langgraph.graph import END, StateGraph

from app.services.llm_service import get_llm
from app.services.search_service import fetch_web_context, retrieve_document_chunks, search_web


class CRAGState(TypedDict, total=False):
    db: Any
    user_id: int
    question: str
    document_ids: list[int] | None
    retrieved_chunks: list[dict[str, Any]]
    retrieval_grade: Literal["correct", "ambiguous", "incorrect"]
    rewritten_question: str
    web_results: list[dict[str, Any]]
    answer: str
    citations: list[dict[str, Any]]
    debug: dict[str, Any]


def _safe_json(content: str, default: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return default


def build_crag_graph():
    workflow = StateGraph(CRAGState)

    def retrieve(state: CRAGState) -> CRAGState:
        db = state["db"]
        chunks = retrieve_document_chunks(
            db=db,
            user_id=state["user_id"],
            question=state["question"],
            document_ids=state.get("document_ids"),
        )
        debug = state.get("debug", {})
        debug["retrieved_chunk_count"] = len(chunks)
        return {"retrieved_chunks": chunks, "debug": debug}

    def grade(state: CRAGState) -> CRAGState:
        llm = get_llm()
        chunk_context = "\n\n".join(chunk["content"] for chunk in state.get("retrieved_chunks", []))
        prompt = f"""
You are grading document retrieval for a QA system.
Return JSON with keys:
- grade: one of correct, ambiguous, incorrect
- rationale: short string

Question:
{state["question"]}

Retrieved context:
{chunk_context[:6000]}
"""
        result = llm.invoke(prompt)
        parsed = _safe_json(result.content, {"grade": "incorrect", "rationale": "Fallback classification"})
        debug = state.get("debug", {})
        debug["grading_rationale"] = parsed.get("rationale")
        return {"retrieval_grade": parsed.get("grade", "incorrect"), "debug": debug}

    def rewrite(state: CRAGState) -> CRAGState:
        llm = get_llm()
        prompt = f"""
Rewrite the question for improved document retrieval.
Return JSON with key "question".

Original question:
{state["question"]}
"""
        result = llm.invoke(prompt)
        parsed = _safe_json(result.content, {"question": state["question"]})
        rewritten = parsed.get("question", state["question"])
        db = state["db"]
        chunks = retrieve_document_chunks(
            db=db,
            user_id=state["user_id"],
            question=rewritten,
            document_ids=state.get("document_ids"),
        )
        debug = state.get("debug", {})
        debug["rewritten_question"] = rewritten
        debug["rewrite_chunk_count"] = len(chunks)
        return {"rewritten_question": rewritten, "retrieved_chunks": chunks, "debug": debug}

    def regrade_after_rewrite(state: CRAGState) -> CRAGState:
        llm = get_llm()
        chunk_context = "\n\n".join(chunk["content"] for chunk in state.get("retrieved_chunks", []))
        prompt = f"""
You are grading rewritten retrieval for a QA system.
Return JSON with keys:
- grade: one of correct, ambiguous, incorrect
- rationale: short string

Original question:
{state["question"]}

Rewritten question:
{state.get("rewritten_question", state["question"])}

Retrieved context:
{chunk_context[:6000]}
"""
        result = llm.invoke(prompt)
        parsed = _safe_json(result.content, {"grade": "incorrect", "rationale": "Fallback classification"})
        debug = state.get("debug", {})
        debug["rewrite_grading_rationale"] = parsed.get("rationale")
        return {"retrieval_grade": parsed.get("grade", "incorrect"), "debug": debug}

    def search(state: CRAGState) -> CRAGState:
        web_results = search_web(state.get("rewritten_question") or state["question"])
        web_context = fetch_web_context(web_results)
        return {"web_results": web_context}

    def answer(state: CRAGState) -> CRAGState:
        llm = get_llm()
        doc_citations = [
            {
                "source_type": "document",
                "title": item["document_name"],
                "snippet": item["content"][:280],
                "document_id": item["document_id"],
                "document_name": item["document_name"],
                "page_number": item.get("page_number"),
                "url": None,
            }
            for item in state.get("retrieved_chunks", [])
        ]
        web_citations = [
            {
                "source_type": "web",
                "title": item["title"],
                "snippet": item["snippet"] or item["content"][:280],
                "url": item["url"],
                "document_id": None,
                "document_name": None,
                "page_number": None,
            }
            for item in state.get("web_results", [])
        ]
        doc_context = "\n\n".join(
            f"[{item['document_name']}] {item['content']}" for item in state.get("retrieved_chunks", [])
        )
        web_context = "\n\n".join(
            f"[{item['title']}] ({item['url']}) {item['content']}" for item in state.get("web_results", [])
        )
        prompt = f"""
You are answering user questions in a CRAG system.
Prefer document evidence if sufficient. If document evidence is weak, use web context carefully.
If the answer is not supported, say that clearly.

Question:
{state["question"]}

Decision:
{state.get("retrieval_grade", "incorrect")}

Document context:
{doc_context[:8000]}

Web context:
{web_context[:8000]}
"""
        result = llm.invoke(prompt)
        citations = doc_citations
        if state.get("retrieval_grade") in {"incorrect", "ambiguous"}:
            citations = doc_citations + web_citations
        return {"answer": result.content, "citations": citations}

    def route_grade(state: CRAGState) -> str:
        return state.get("retrieval_grade", "incorrect")

    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade", grade)
    workflow.add_node("rewrite", rewrite)
    workflow.add_node("regrade_after_rewrite", regrade_after_rewrite)
    workflow.add_node("search", search)
    workflow.add_node("generate_answer", answer)

    workflow.set_entry_point("retrieve")
    workflow.add_edge("retrieve", "grade")
    workflow.add_conditional_edges(
        "grade",
        route_grade,
        {
            "correct": "generate_answer",
            "ambiguous": "rewrite",
            "incorrect": "search",
        },
    )
    workflow.add_edge("rewrite", "regrade_after_rewrite")
    workflow.add_conditional_edges(
        "regrade_after_rewrite",
        route_grade,
        {
            "correct": "generate_answer",
            "ambiguous": "search",
            "incorrect": "search",
        },
    )
    workflow.add_edge("search", "generate_answer")
    workflow.add_edge("generate_answer", END)
    return workflow.compile()


crag_graph = build_crag_graph()
