import argparse
from graph import build_graph


def main():
    ap = argparse.ArgumentParser(description="Anveshan AI / Scholarship Sahaya")
    ap.add_argument("query", nargs="?", help="Describe yourself, e.g. 'B.E CSE student from Karnataka, OBC, income 3 lakh'")
    ap.add_argument("--user", default="demo-user", help="User id (for saved profile in Firestore)")
    args = ap.parse_args()

    app = build_graph()
    query = args.query or input("Tell me about yourself and what you're looking for: ")
    out = app.invoke({"user_id": args.user, "query": query})
    print("\n" + out["answer"])


if __name__ == "__main__":
    main()
