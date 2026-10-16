# Week 3 Writeup: Prompting Techniques (Support-Desk Assistant)

- **Model:** `llama3.1:8b` running locally in Ollama 0.40.5 (Python client `ollama` 0.6.3), `temperature 0.0`
- **Machine:** macOS on Apple silicon, Python 3.12
- **Rule followed:** I only edited the `TODO` parts (the prompts, the tool schema descriptions, and
  the retriever in `rag.py`). The model, the cases, and the grading code are unchanged.

## Results

| Technique             | Empty prompt (starter)                  | Final prompt |
| --------------------- | --------------------------------------- | ------------ |
| `k_shot_prompting.py` | 0/4: long help-desk replies, no labels  | 4/4          |
| `chain_of_thought.py` | 0/3: no `DECISION:` line                 | 3/3          |
| `tool_calling.py`     | PASS, even with empty descriptions      | PASS         |
| `rag.py`              | 2/3, but only by luck (see below)       | 3/3          |

Each final file was run at least 4 times and passed every time.

## 1. K-shot prompting: ticket classification

**Final prompt:**

```text
You are a ticket router for an online store's support desk.
Classify each customer message into exactly one label:
billing, shipping, returns, technical, other

- billing: charges, payments, invoices, refunds of money already charged by mistake
- shipping: delivery status, tracking, delays, addresses
- returns: sending an item back, exchanges, return-for-refund requests
- technical: the website or app not working (errors, crashes, login problems)
- other: anything else

Reply with the label only: one lowercase word, no punctuation, no explanation.

Examples:
Message: I was billed for an order I cancelled.
Label: billing
Message: My tracking number hasn't updated in five days.
Label: shipping
Message: This jacket is too small, how do I return it?
Label: returns
Message: I get an error when I try to log in.
Label: technical
Message: Do you have a physical store in Boston?
Label: other
```

**Sample input/output:**

```text
Input:  My card was charged twice for order 4412.
Output: billing
```

Beyond the four graded cases, I also tried messages the examples do not cover, and all were
labelled correctly: "I was charged but never got a receipt email." → `billing`, "Can I swap these
jeans for a bigger size?" → `returns`, "Your website won't load on Safari." → `technical`, "Do
you sell gift cards?" → `other`.

**What I learned:** Label definitions, 5 examples, and a "reply with one word" instruction moved the model from long customer-service replies to a one-word label (0/4 → 4/4).

## 2. Chain-of-thought: refund eligibility

**Final prompt:**

```text
You decide whether an order is eligible for a refund under the policy below.
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
DECISION: NO
```

**Sample input/output:**

```text
Input:  Bought 5 days ago but it was a final-sale item.
Output:
1. Time: bought 5 days ago; 5 is 30 or fewer -> PASS
2. Condition: the order does not mention the item being used or damaged, so it is unused -> PASS
3. Final sale: the order says it is a final-sale item -> FAIL
DECISION: NO
```

**How the prompt got here.** The check passed on the first prompt, but reading the full reasoning
showed it was not trustworthy, so I kept iterating:

| Version | Change                                                       | Check | What the output showed                                                                 |
| ------- | ------------------------------------------------------------ | ----- | -------------------------------------------------------------------------------------- |
| v1      | Rules as yes/no questions, then `DECISION`                   | 3/3   | "Final sale: is it a final-sale item? YES" followed by `DECISION: NO`: right answer, confusing reasoning |
| v2      | Each rule ends in PASS/FAIL, plus an "Eligible" line          | 1/3   | Clear reasoning, but the model ended NO cases with "Not eligible" and dropped `DECISION` |
| v3      | Merged into a single required `DECISION` line                | 3/3   | Format fixed, but lines became bare labels: "Time: FAIL" for an item bought 5 days ago |
| v4      | Each line must state the fact first, plus a worked example   | 3/3   | Correct reasoning on every case except the boundary: "30 is not 30 or fewer -> FAIL"   |
| v5      | Explicit boundary: "exactly 30 days still PASSES"            | 3/3   | Correct on 29, 30, 31 days, used items, and final-sale items                            |

**What I learned:** A single required `DECISION` line fixed the format, but making the reasoning correct as well required having the model state the facts first and saying the "exactly 30 days still passes" boundary explicitly.

## 3. Tool calling: order lookup

**Final system prompt:**

```text
You are a support assistant for an online store.
When a customer asks about an order, first call get_order_status with the order number from
their message. Do not answer from memory or guess the status. After you get the result, reply
in one or two friendly sentences that state the status.
```

**Tool description:** Look up the current status of a customer's order (for example shipped, processing, or not found). Call this whenever the customer asks where an order is or what is happening with it. Never guess an order's status.

**`order_id` description:** The order number exactly as the customer wrote it, digits only, for example '4412'. Do not add '#' or the word 'order'.

**Sample input/output:**

```text
Input:      Hi, can you check on order 4412 for me?
Tool call:  get_order_status(order_id="4412") -> "shipped, arriving Friday"
Reply:      I've checked on your order 4412 for you. It's currently shipped and is expected to arrive on Friday.
```

The starter's check only verifies that the tool was called with `4412`, and that already passed with
empty descriptions: the function and parameter names were enough for this message. The descriptions
matter for what the check does not test, such as when to call the tool and what format the ID should
have. The reply above comes from sending the tool result back to the model, which the starter does
not do.

**What I learned:** Because the model made the right call even with empty descriptions, the prompt did not change the result in a measurable way; the descriptions I wrote mostly served as a safeguard for edge cases.

## 4. RAG: answers grounded in the help center

**Retriever:** keyword overlap. Both the question and each help-center line are lowercased and split
into words, common stopwords are dropped, and two words match when the shorter one (at least 4
letters) is a prefix of the longer one, so "ship" matches "shipping" and "internationally" matches
"international". The retriever returns up to 3 lines with the most matching words, or nothing at all.

**Final prompt:**

```text
You are a support assistant for an online store.
Answer the customer's question using ONLY the text under "Context". Do not use outside
knowledge, and do not guess.
- If the context answers the question, reply in one or two sentences and keep the key facts
  (numbers, time limits) exactly as written in the context.
- If the context is empty or does not contain the answer, reply exactly:
  "I don't know. I can only answer questions covered by our help center."
```

**Sample input/output:**

```text
Input:   Do you ship internationally?
Context: "Shipping: We offer international shipping to most countries; delivery takes 7-21 business days." (+2 more lines)
Output:  yes, we offer international shipping to most countries. delivery takes 7-21 business days.

Input:   What's your CEO's home address?
Context: (empty: no words match)
Output:  i don't know. i can only answer questions covered by our help center.
```

**Why the starter's 2/3 was misleading.** With the empty retriever, the model never saw the help
center. For "How long do I have to return an item?" it answered from general knowledge ("the return
policy varies depending on the store…") and still passed, because "30 days" appeared somewhere in
its long reply. It then failed the CEO question only because it wrote "can't" while the check looks
for "cannot". After the change, the answers quote the help center, and "Do you offer gift wrapping?"
(not in the help center) also gets "I don't know".

**What I learned:** Without context the model guessed from general knowledge; with the retriever and the "use only the Context" instruction it passed the facts on exactly and said "I don't know" for the question it could not answer (2/3 → 3/3).

## What I learned across all four

Across all four techniques, the model had no trouble with structured tasks once the shape of the output was clearly defined. It picked up the pattern from a few examples and classified correctly, made the right tool call even with empty descriptions, and kept to the requested format. Where it struggled were things it could not know on its own or would not do by itself. It got numeric boundaries like "does 30 days count" wrong, it guessed instead of saying it did not know when it lacked the information, and when two format instructions conflicted it dropped one of them (the `DECISION` line disappeared in CoT v2). So scaffolding removes ambiguity more than it gives the model a new ability: examples fix the shape of the output, the retriever fixes the information, and explicit rules fix the boundaries. Finally, a passing test does not mean correct reasoning: in CoT the test passed in three versions while the reasoning was wrong, and the tool calling test did not measure the quality of the prompt at all.
