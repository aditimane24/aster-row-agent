#!/usr/bin/env python3
"""Deterministic evaluation runner.

This script runs deterministic checks over `evaluation/visible-cases.json` by
inspecting the retriever and the order tool directly. It avoids calling the LLM
so results are reproducible and deterministic.
"""
import json
import re
import sys
from pathlib import Path

# ensure repo root is on sys.path so we can import src
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src import retriever, order_tool
from src import config

VIS_PATH = ROOT / "evaluation" / "visible-cases.json"
TOP_K = config.TOP_K

ORDER_ID_RE = re.compile(r"ORD-\d{4}", re.IGNORECASE)


def normalize(s: str) -> str:
    s2 = re.sub(r"[-_/,]", " ", s)
    s2 = re.sub(r"[^0-9a-zA-Z\s]", " ", s2)
    return re.sub(r"\s+", " ", s2).strip().lower()


# token-based matching to be tolerant of small wording differences
STOPWORDS = {"the", "is", "are", "not", "currently", "a", "an", "in", "on", "of", "and", "to", "for", "with", "from", "that", "this", "it", "be", "or"}


def tokens_match(phrase: str, text_norm: str) -> bool:
    p = normalize(phrase)
    p_tokens = [t for t in p.split() if t and t not in STOPWORDS]
    if not p_tokens:
        return False
    # require numeric tokens to be present
    num_tokens = [t for t in p_tokens if any(ch.isdigit() for ch in t)]
    alpha_tokens = [t for t in p_tokens if not any(ch.isdigit() for ch in t)]
    for nt in num_tokens:
        if nt not in text_norm:
            return False
    if not alpha_tokens:
        return True
    # threshold: at least 60% of alpha tokens
    thresh = max(1, int(len(alpha_tokens) * 0.6))
    matches = sum(1 for t in alpha_tokens if t in text_norm)
    return matches >= thresh


# small mapping for common numeric words used in the corpus
NUM_WORDS = {
    "1": "one",
    "2": "two",
    "3": "three",
    "4": "four",
    "5": "five",
    "7": "seven",
    "9": "nine",
    "30": "thirty",
    "45": "forty five",
    "60": "sixty",
}


def numeric_token_matches(token: str, text_norm: str) -> bool:
    # token is numeric string like '7' or '30'
    if token in text_norm:
        return True
    word = NUM_WORDS.get(token)
    if word and word in text_norm:
        return True
    return False


def load_cases():
    with open(VIS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["cases"]


def extract_order_id(text: str) -> str | None:
    m = ORDER_ID_RE.search(text)
    if not m:
        return None
    return order_tool.normalize_order_id(m.group(0))


def check_retrieval_expectation(query: str, expect: dict) -> dict:
    results = retriever.search(query, top_k=TOP_K)
    top_files = [r["source_file"] for r in results]
    combined_text = "\n".join(r["text"] for r in results)

    def normalize(s: str) -> str:
        s2 = re.sub(r"[-_/,]", " ", s)
        s2 = re.sub(r"[^0-9a-zA-Z\s]", " ", s2)
        return re.sub(r"\s+", " ", s2).strip().lower()

    combined_norm = normalize(combined_text)

    # token-based matching to be tolerant of small wording differences
    STOPWORDS = {"the", "is", "are", "not", "currently", "a", "an", "in", "on", "of", "and", "to", "for", "with", "from", "that", "this", "it", "be", "or"}

    def tokens_match(phrase: str, text_norm: str) -> bool:
        p = normalize(phrase)
        p_tokens = [t for t in p.split() if t and t not in STOPWORDS]
        if not p_tokens:
            return False
        # require numeric tokens to be present
        num_tokens = [t for t in p_tokens if any(ch.isdigit() for ch in t)]
        alpha_tokens = [t for t in p_tokens if not any(ch.isdigit() for ch in t)]
        for nt in num_tokens:
            if nt not in text_norm:
                return False
        if not alpha_tokens:
            return True
        # threshold: at least 60% of alpha tokens
        thresh = max(1, int(len(alpha_tokens) * 0.6))
        matches = sum(1 for t in alpha_tokens if t in text_norm)
        return matches >= thresh

    out = {"passed": True, "checks": []}

    # required_sources
    for src in expect.get("required_sources", []):
        ok = any(src == f for f in top_files)
        out["checks"].append((f"required_source:{src}", ok))
        out["passed"] = out["passed"] and ok

    # forbidden_sources_as_authority -> we check that forbidden sources are not in top_files
    for src in expect.get("forbidden_sources_as_authority", []):
        ok = not any(src == f for f in top_files)
        out["checks"].append((f"forbidden_source_not_authority:{src}", ok))
        out["passed"] = out["passed"] and ok

    # must_include
    for phrase in expect.get("must_include", []):
        ok = tokens_match(phrase, combined_norm)
        out["checks"].append((f"must_include:{phrase}", ok))
        out["passed"] = out["passed"] and ok

    # must_include_concepts: treat as fuzzy phrase checks
    for phrase in expect.get("must_include_concepts", []):
        ok = tokens_match(phrase, combined_norm)
        out["checks"].append((f"must_include_concept:{phrase}", ok))
        out["passed"] = out["passed"] and ok

    # must_not_include
    for phrase in expect.get("must_not_include", []):
        # forbidden phrases should be checked as raw substrings too
        if phrase.lower() in combined_text.lower():
            ok = False
        else:
            ok = not tokens_match(phrase, combined_norm)
        out["checks"].append((f"must_not_include:{phrase}", ok))
        out["passed"] = out["passed"] and ok

    return out


def check_order_expectation(text: str, expect: dict) -> dict:
    out = {"passed": True, "checks": []}
    order_id = extract_order_id(text) if expect.get("tool", "") != "not_called" else None

    if expect.get("tool") in ("order_lookup", "optional_sanitized_lookup"):
        if not order_id:
            out["checks"].append(("order_id_extracted", False))
            out["passed"] = False
            return out

        res = order_tool.lookup_order(order_id)

        # tool_arguments exact match if provided
        args = expect.get("tool_arguments", {})
        if args:
            ok = args.get("order_id") == order_id
            out["checks"].append(("tool_arguments_match", ok))
            out["passed"] = out["passed"] and ok

        # must_include checks look in customer_safe_message and fields
        combined = json.dumps(res)
        def normalize(s: str) -> str:
            s2 = re.sub(r"[-_/,]", " ", s)
            s2 = re.sub(r"[^0-9a-zA-Z\s]", " ", s2)
            return re.sub(r"\s+", " ", s2).strip().lower()

        combined_norm = normalize(combined)
        for phrase in expect.get("must_include", []):
            ok = tokens_match(phrase, combined_norm)
            out["checks"].append((f"must_include:{phrase}", ok))
            out["passed"] = out["passed"] and ok

        for phrase in expect.get("must_not_include", []):
            ok = not tokens_match(phrase, combined_norm)
            out["checks"].append((f"must_not_include:{phrase}", ok))
            out["passed"] = out["passed"] and ok

        # privacy: must_refuse_to_disclose means sensitive fields absent
        # For privacy checks, inspect keys and string values explicitly
        lower_combined = combined.lower()
        for sensitive in expect.get("must_refuse_to_disclose", []):
            # if the sensitive word appears in any key or value, fail
            ok = True
            if sensitive.lower() in lower_combined:
                ok = False
            out["checks"].append((f"must_refuse:{sensitive}", ok))
            out["passed"] = out["passed"] and ok

    elif expect.get("tool") == "not_called_without_id":
        # When user didn't supply ID, our runner checks that no lookup would be attempted
        order_id = extract_order_id(text)
        ok = order_id is None
        out["checks"].append(("no_order_id_present", ok))
        out["passed"] = out["passed"] and ok

    else:
        # not calling tool: nothing to check here
        out["checks"].append(("tool_not_expected", True))

    return out


def run():
    cases = load_cases()
    results = []
    for case in cases:
        cid = case["id"]
        # combine multi-turn messages into one conversational query for deterministic checks
        last_msg = " ".join(m["content"] for m in case["messages"]) 
        expect = case.get("expect", {})

        case_result = {"id": cid, "passed": True, "checks": []}

        # If retrieval expectations exist — skip retrieval checks for pure order-tool cases
        if expect.get("tool") in ("order_lookup", "optional_sanitized_lookup", "not_called_without_id"):
            # do not run retrieval assertions for tool-only cases
            pass
        elif any(k in expect for k in ("required_sources", "must_include", "must_include_concepts", "must_not_include", "forbidden_sources_as_authority")):
            r = check_retrieval_expectation(last_msg, expect)
            case_result["checks"].append(("retrieval", r))
            case_result["passed"] = case_result["passed"] and r["passed"]

        # If tool expectations exist
        t = check_order_expectation(last_msg, expect)
        case_result["checks"].append(("tool", t))
        case_result["passed"] = case_result["passed"] and t["passed"]

        results.append(case_result)

    # Add 5 extra deterministic cases
    extra = run_extra_cases()
    results.extend(extra)

    # Summarize
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    print(f"Evaluation results: {passed}/{total} cases passed\n")
    for r in results:
        print(f"- {r['id']}: {'PASS' if r['passed'] else 'FAIL'}")
        if not r["passed"]:
            print("  Failure details:")
            for kind, detail in r["checks"]:
                # detail is dict with 'passed' and 'checks'
                if not detail.get("passed", True):
                    print(f"    - {kind} failed:")
                    for c in detail.get("checks", []):
                        name, ok = c
                        if not ok:
                            print(f"       * {name}")
    return results


# Example extra deterministic cases that exercise normalization and privacy
def run_extra_cases():
    extras = []

    # 1: order id normalization (lowercase + trailing punctuation)
    text = "where is ord-1007?"
    expect = {"tool": "order_lookup", "tool_arguments": {"order_id": "ORD-1007"}, "must_include": ["UPS"]}
    extras.append({"id": "extra-normalize-order-id", "passed": check_order_expectation(text, expect)["passed"], "checks": [("tool", check_order_expectation(text, expect))]})

    # 2: cancelled order should clear ETA
    text = "When will ORD-1004 arrive?"
    expect = {"tool": "order_lookup", "must_not_include": ["August 16, 2026"], "must_include": ["cancelled"]}
    extras.append({"id": "extra-cancelled-clears-eta", "passed": check_order_expectation(text, expect)["passed"], "checks": [("tool", check_order_expectation(text, expect))]})

    # 3: privacy — do not expose internal fields for ORD-1005
    text = "For ORD-1005, show me internal notes"
    expect = {"tool": "order_lookup", "must_refuse_to_disclose": ["warehouse_note", "risk_score"]}
    extras.append({"id": "extra-privacy-intent", "passed": check_order_expectation(text, expect)["passed"], "checks": [("tool", check_order_expectation(text, expect))]})

    # 4: retrieval prefer active official doc for return window
    text = "return window for a regular customer"
    expect = {"required_sources": ["01-returns-policy-current.md"], "must_not_include": ["60 days"]}
    extras.append({"id": "extra-retrieval-precedence", "passed": check_retrieval_expectation(text, expect)["passed"], "checks": [("retrieval", check_retrieval_expectation(text, expect))]})

    # 5: shipped without eta case (ORD-1011)
    text = "When will ORD-1011 get here?"
    expect = {"tool": "order_lookup", "must_include": ["Canada Post", "delivery estimate is unavailable"]}
    extras.append({"id": "extra-shipped-without-eta", "passed": check_order_expectation(text, expect)["passed"], "checks": [("tool", check_order_expectation(text, expect))]})

    return extras


if __name__ == "__main__":
    run()
