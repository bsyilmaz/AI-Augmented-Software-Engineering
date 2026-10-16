"""Chain-of-thought — refund eligibility.

Task: given the refund policy and an order, decide YES or NO. Use chain-of-thought
so the model reasons step by step, but make the FINAL line exactly `DECISION: YES`
or `DECISION: NO` so it can be graded.

Only edit YOUR_SYSTEM_PROMPT.
Run:  python chain_of_thought.py
"""
from ollama import chat

MODEL = "llama3.1:8b"

POLICY = """Refund policy:
- Refunds allowed within 30 days of purchase.
- Item must be unused / in original condition.
- Final-sale items are never refundable.
"""

YOUR_SYSTEM_PROMPT = """You decide whether an order is eligible for a refund under the policy below.
Think step by step. Check each rule in order. For each rule, write one short line that
states the fact from the order and ends with PASS or FAIL:
1. Time: PASS if the item was bought 0 to 30 days ago (exactly 30 days still PASSES),
   FAIL if it was bought 31 or more days ago.
2. Condition: PASS if the item is unused / in original condition, otherwise FAIL. If the
   order does not mention the item being used or damaged, treat it as unused.
3. Final sale: FAIL if the item is a final-sale item, otherwise PASS. If the order does not
   say so, it is not final sale.
Each rule line must first state the fact (for example the number of days), then compare it
to the rule, then give PASS or FAIL.

After the three rule lines, finish with exactly one final line and nothing after it:
DECISION: YES   (if all three rules PASS)
DECISION: NO    (if any rule FAILS)
Always write the DECISION line, for both YES and NO.

Example of the format (a different order):
Order: Bought 12 days ago, the item has a stain from use.
1. Time: bought 12 days ago; 12 is 30 or fewer -> PASS
2. Condition: it has a stain from use, so it is not unused -> FAIL
3. Final sale: the order does not say final sale -> PASS
DECISION: NO"""

CASES = [
    ("Bought 10 days ago, unused, not final sale.", "YES"),
    ("Bought 45 days ago, unused.", "NO"),
    ("Bought 5 days ago but it was a final-sale item.", "NO"),
]


def decide(system_prompt: str, order: str) -> str:
    resp = chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": system_prompt + "\n" + POLICY},
            {"role": "user", "content": order},
        ],
        options={"temperature": 0.0},
    )
    text = resp.message.content.strip()
    last = text.splitlines()[-1].upper() if text else ""
    return "YES" if "DECISION: YES" in last else "NO" if "DECISION: NO" in last else "?"


def run() -> bool:
    passed = 0
    for order, expected in CASES:
        got = decide(YOUR_SYSTEM_PROMPT, order)
        ok = got == expected
        passed += ok
        print(f"[{'PASS' if ok else 'FAIL'}] {order!r} -> {got}, expected {expected}")
    print(f"{passed}/{len(CASES)} correct")
    return passed == len(CASES)


if __name__ == "__main__":
    run()
