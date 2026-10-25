import hashlib
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

load_dotenv()

llm = ChatGoogleGenerativeAI(model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"), temperature=0)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vectorstore = Chroma(
    collection_name="scholarships",
    embedding_function=embeddings,
    persist_directory=os.getenv("CHROMA_DIR", "./chroma_db"),
)


def doc_id(url: str) -> str:
    return hashlib.sha1(url.strip().lower().encode()).hexdigest()


@lru_cache(maxsize=1)
def tavily():
    from tavily import TavilyClient
    return TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


@lru_cache(maxsize=1)
def firestore_db():
    """Returns a Firestore client, or None if credentials aren't configured."""
    try:
        from google.cloud import firestore
        return firestore.Client()
    except Exception as e:  # no creds -> run without persistence
        print(f"[firestore disabled: {e.__class__.__name__}]")
        return None


def load_profile(user_id: str) -> dict:
    db = firestore_db()
    if not db or not user_id:
        return {}
    snap = db.collection("profiles").document(user_id).get()
    return snap.to_dict() or {} if snap.exists else {}


def save_profile(user_id: str, profile: dict) -> None:
    db = firestore_db()
    if db and user_id:
        db.collection("profiles").document(user_id).set(profile, merge=True)


def save_scholarships(items: list[dict]) -> None:
    db = firestore_db()
    if not db:
        return
    batch = db.batch()
    for s in items:
        batch.set(db.collection("scholarships").document(doc_id(s["url"])), s, merge=True)
    batch.commit()
