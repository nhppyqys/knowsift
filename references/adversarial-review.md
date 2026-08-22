# Adversarial review

## What this gate is and is not

The first pass produces a `semantic_review`: someone read the evidence and said
how it relates to the claim. That someone is normally an LLM, and it is the
weakest joint in the whole pipeline. Everything downstream — protocols, scope,
source authority, document layers — is mechanical, but it all rests on one
model's reading of one passage.

Adversarial review adds a second reading by a different reviewer and compares
the two. The runtime never decides who is right. It only refuses to call a
contested reading knowledge.

```text
two reviewers agree      → the gate passes, nothing changes
two reviewers disagree   → HOLD, with both readings recorded
only one reviewer exists → PASS under `optional`, HOLD under `required`
```

`HOLD` here means unresolved, not false. Resolving it is research work: read the
passage yourself, collect the evidence the reviewers disagreed about, or narrow
the claim until both readings agree.

## Policy

| Policy | Meaning |
|---|---|
| `off` | Do not run the gate. The certificate records that it was skipped. |
| `optional` | Default. A supplied review is fully checked; an absent one is not penalised. |
| `required` | Every first-pass review must have an independent counterpart. |

The effective policy is the **strictest** of three sources, so an input can
never relax what the host requires:

1. `adversarial_policy` inside the payload
2. `KNOWSIFT_ADVERSARIAL_POLICY` in the environment
3. `--adversarial` on `compile_claim.py`

An org that wants the gate enforced sets the environment variable once. No
upstream Agent can write a payload that turns it off.

Note what `optional` still does: a **supplied** review is always checked, and a
disagreement always holds the claim. `optional` governs whether a missing review
is tolerated, not whether a present one can be ignored.

## What a review must contain

```json
{
  "claim_id": "SD-YT-001",
  "evidence_id": "E-SD-YT-001",
  "relation": "PARTIAL",
  "reviewer_id": "gpt-5-codex",
  "evidence_fragment": "1,000 subscribers plus 4,000 watch hours / 12 months",
  "strongest_counter_reading": "The page lists an application threshold, not a revenue guarantee.",
  "what_would_falsify": "A line on the same official page equating the threshold with income."
}
```

Four checks are mechanical and cannot be argued with:

- `evidence_fragment` must appear byte for byte in that evidence's `source_text`.
  A reviewer that paraphrases the source is discarded.
- `reviewer_id` must differ from the first pass's `reviewer_id`. A model cannot
  review itself. Under `required`, the first pass must declare its own
  `reviewer_id` so independence is checkable at all.
- `strongest_counter_reading` is required **even when the reviewer agrees**.
  Agreement that cannot articulate the opposing reading is not worth much.
- `what_would_falsify` must be present. This is the field a human can check
  without trusting either model, which makes it the most useful thing in the
  certificate when both models are wrong in the same direction.

Confidence numbers, probabilities, and reliability scores are rejected here for
the same reason they are rejected everywhere else in this runtime.

## Choosing a route

Run the detector first. It reports what this machine can actually do, not what
happens to be on `PATH`:

```bash
python3 scripts/adversarial_review.py detect
```

```bash
python3 scripts/adversarial_review.py detect --deep --model claude-sonnet-5
```

`--deep` makes a real call to each available backend. Use it when a backend is
listed as available but a review fails: CLI flags drift between releases, and
`references/reviewers.json` is editable data, not a guarantee.

### Route B — an external CLI

Strongest, because a different model family fails in different places than the
first reviewer.

```bash
python3 scripts/adversarial_review.py run claim.json --backend codex-cli --output reviews.json
python3 scripts/adversarial_review.py merge claim.json reviews.json \
  --first-pass-reviewer-id claude-opus-5 --policy required --output reviewed-claim.json
python3 scripts/compile_claim.py reviewed-claim.json --pretty
```

For any tool not in the registry — a local model, a private endpoint, another
harness — set one environment variable. The command reads the prompt on stdin
and prints JSON on stdout:

```bash
export KNOWSIFT_REVIEWER_CMD="my-model-cli --quiet"
python3 scripts/adversarial_review.py run claim.json --backend custom --model my-model-v2
```

### Route A — the host Agent's own subagent

No second CLI needed. The host runs the same prompt in an isolated subagent
under a different model:

```bash
python3 scripts/adversarial_review.py prompt claim.json
```

Give that output to the subagent verbatim, take back the JSON, then `merge` it
with `--reviewer-id` set to the model that actually ran.

This is weaker than route B: the same family shares training data and tends to
share blind spots. It is still much better than nothing, because the subagent
does not see the first pass's conclusion.

Host mechanics differ. Claude Code takes `context: fork` with `agent:` and
`model:` in skill frontmatter, or a Task-tool subagent. Codex uses custom agents
defined in TOML, with `agents.max_depth` capping nesting. Neither is portable,
which is why the contract lives in the payload rather than in any host's
subagent machinery.

### Manual

Always available, on any machine, with nothing installed:

```bash
python3 scripts/adversarial_review.py prompt claim.json
```

Paste it into any chat, paste the JSON back into a file, then `merge` it. Set
`--reviewer-id` to whatever actually answered.

## The limit worth stating plainly

Two models with overlapping training data fail in the same places. When both
agree, you have not learned that the reading is correct — you have learned that
two correlated readers did not catch each other. Cross-family review reduces the
correlation; it does not remove it.

That is why `what_would_falsify` is mandatory rather than nice to have. A
falsifier is checkable by a person without trusting any model, so it is the one
part of this gate that does not degrade when the models are correlated.
