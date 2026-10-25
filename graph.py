import json
from langgraph.graph import END, START, StateGraph

from schemas import AnveshanState, MatchList, Profile, ScholarshipList
from services import (
    doc_id, llm, load_profile, save_profile, save_scholarships, tavily, vectorstore,
)

MIN_LOCAL_HITS = 5


# ---------- helpers ----------
def profile_summary(p: dict) -> str:
    return ", ".join(f"{k}: {v}" for k, v in p.items() if v not in (None, ""))


def to_text(s: dict) -> str:
    return (f"{s['name']} | {s.get('provider', '')}\n"
            f"Eligibility: {s.get('eligibility', '')}\n"
            f"Benefits: {s.get('benefits', '')}\nDeadline: {s.get('deadline', '')}")


# ---------- nodes ----------
def parse_profile(state: AnveshanState) -> dict:
    """Extract profile from the query and merge with any saved profile."""
    saved = load_profile(state.get("user_id", ""))
    extractor = llm.with_structured_output(Profile)
    new = extractor.invoke(
        "Extract the student's profile from this message. Leave unknown fields null.\n\n"
        f"Message: {state['query']}"
    ).model_dump()
    merged = {**saved, **{k: v for k, v in new.items() if v is not None}}
    save_profile(state.get("user_id", ""), merged)
    return {"profile": merged}


def retrieve(state: AnveshanState) -> dict:
    """Semantic search over scholarships already stored in ChromaDB."""
    q = f"{profile_summary(state['profile'])}. {state['query']}"
    docs = vectorstore.similarity_search(q, k=8)
    return {"candidates": [{**d.metadata, "text": d.page_content} for d in docs]}


def route_after_retrieve(state: AnveshanState) -> str:
    return "web_search" if len(state["candidates"]) < MIN_LOCAL_HITS else "rank"


def web_search(state: AnveshanState) -> dict:
    """Pull fresh scholarships via Tavily, structure them with Gemini, and ingest."""
    p = state["profile"]
    query = (f"scholarships India {p.get('education_level', '')} {p.get('course', '')} "
             f"{p.get('category', '')} {p.get('state', '')} eligibility last date")
    results = tavily().search(query=query, search_depth="advanced", max_results=6)["results"]
    context = "\n\n".join(f"URL: {r['url']}\n{r['content']}" for r in results)

    extracted = llm.with_structured_output(ScholarshipList).invoke(
        "From the web results below, extract real Indian scholarship schemes. "
        "Use the exact source URL for each. Do not invent details; use empty strings if unknown.\n\n"
        + context
    ).scholarships
    new = [s.model_dump() for s in extracted if s.url]

    if new:
        vectorstore.add_texts(
            texts=[to_text(s) for s in new],
            metadatas=new,
            ids=[doc_id(s["url"]) for s in new],
        )
        save_scholarships(new)

    seen = {c.get("url") for c in state["candidates"]}
    merged = state["candidates"] + [{**s, "text": to_text(s)} for s in new if s["url"] not in seen]
    return {"candidates": merged}


def rank(state: AnveshanState) -> dict:
    """Score each candidate against the student's profile."""
    slim = [{k: c.get(k, "") for k in ("name", "url", "eligibility", "benefits", "deadline")}
            for c in state["candidates"]]
    result = llm.with_structured_output(MatchList).invoke(
        "You are a scholarship eligibility checker for Indian students.\n"
        "For each scholarship, judge fit for this student using ONLY the stated eligibility. "
        "Mark eligible='maybe' when criteria are unclear. List documents typically needed.\n\n"
        f"Student: {json.dumps(state['profile'])}\n\nScholarships: {json.dumps(slim)}"
    )
    ranked = [m.model_dump() for m in result.matches if m.eligible != "no"]
    ranked.sort(key=lambda m: m["fit_score"], reverse=True)
    return {"ranked": ranked[:8]}


def respond(state: AnveshanState) -> dict:
    if not state["ranked"]:
        return {"answer": "I couldn't find a confident match. Try adding your course, state, category, and family income."}
    lines = [f"Profile used: {profile_summary(state['profile'])}\n"]
    for i, m in enumerate(state["ranked"], 1):
        lines.append(
            f"{i}. {m['name']}  (fit {m['fit_score']}/100, eligible: {m['eligible']})\n"
            f"   Why: {m['reason']}\n"
            f"   Deadline: {m['deadline'] or 'check official site'}\n"
            f"   Documents: {', '.join(m['documents_needed']) or 'see official site'}\n"
            f"   Apply: {m['url']}\n"
        )
    lines.append("Always confirm eligibility and deadlines on the official portal before applying.")
    return {"answer": "\n".join(lines)}


# ---------- graph ----------
def build_graph():
    g = StateGraph(AnveshanState)
    g.add_node("parse_profile", parse_profile)
    g.add_node("retrieve", retrieve)
    g.add_node("web_search", web_search)
    g.add_node("rank", rank)
    g.add_node("respond", respond)

    g.add_edge(START, "parse_profile")
    g.add_edge("parse_profile", "retrieve")
    g.add_conditional_edges("retrieve", route_after_retrieve, {"web_search": "web_search", "rank": "rank"})
    g.add_edge("web_search", "rank")
    g.add_edge("rank", "respond")
    g.add_edge("respond", END)
    return g.compile()
