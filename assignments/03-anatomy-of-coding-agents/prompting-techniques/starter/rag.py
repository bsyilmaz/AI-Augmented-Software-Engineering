"""RAG — policy-grounded answers.

Task: answer a customer question using ONLY the retrieved help-center text. If the
answer isn't in the docs, the model must say it doesn't know (don't hallucinate).

Fill in YOUR_SYSTEM_PROMPT and YOUR_RETRIEVER.
Run:  python rag.py
"""
import os

from ollama import chat

MODEL = "llama3.1:8b"
DATA = os.path.join(os.path.dirname(__file__), "data", "help_center.txt")


def load_chunks() -> list[str]:
    with open(DATA, encoding="utf-8") as f:
        # one chunk per non-empty line
        return [line.strip() for line in f if line.strip()]


STOPWORDS = {
    "a", "an", "and", "are", "can", "do", "does", "for", "have", "how", "i", "if", "in", "is",
    "it", "long", "my", "of", "on", "or", "s", "the", "to", "what", "whats", "when", "where",
    "which", "who", "why", "with", "you", "your",
}


def _words(text: str) -> set[str]:
    cleaned = "".join(ch if ch.isalnum() else " " for ch in text.lower().replace("'", ""))
    return {w for w in cleaned.split() if w not in STOPWORDS}


def _related(a: str, b: str) -> bool:
    # Crude stemming: "ship" ~ "shipping", "internationally" ~ "international".
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 4 and long_.startswith(short)


def YOUR_RETRIEVER(question: str, chunks: list[str]) -> list[str]:
    q_words = _words(question)
    scored = []
    for chunk in chunks:
        overlap = sum(any(_related(q, c) for c in _words(chunk)) for q in q_words)
        if overlap:
            scored.append((overlap, chunk))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    return [chunk for _, chunk in scored[:3]]


YOUR_SYSTEM_PROMPT = """You are a support assistant for an online store.
Answer the customer's question using ONLY the text under "Context". Do not use outside
knowledge, and do not guess.
- If the context answers the question, reply in one or two sentences and keep the key facts
  (numbers, time limits) exactly as written in the context.
- If the context is empty or does not contain the answer, reply exactly:
  "I don't know. I can only answer questions covered by our help center."
"""

CASES = [
    ("How long do I have to return an item?", ["30 days"]),
    ("Do you ship internationally?", ["international"]),
    ("What's your CEO's home address?", ["don't know", "do not know", "not sure", "cannot"]),
]


def answer(question: str) -> str:
    context = "\n".join(YOUR_RETRIEVER(question, load_chunks()))
    resp = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": YOUR_SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"},
        ],
        options={"temperature": 0.0},
    )
    return resp.message.content.strip().lower()


def run() -> bool:
    passed = 0
    for question, needles in CASES:
        got = answer(question)
        ok = any(n.lower() in got for n in needles)
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {question!r} -> {got[:80]!r}")
    print(f"{passed}/{len(CASES)} correct")
    return passed == len(CASES)


if __name__ == "__main__":
    run()
