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
- `independence` must be declared, and the runtime derives a ceiling from the two
  `reviewer_id` values. A tier may be under-claimed but never over-claimed.
- `strongest_counter_reading` is required **even when the reviewer agrees**.
  Agreement that cannot articulate the opposing reading is not worth much.
- `what_would_falsify` must be present. This is the field a human can check
  without trusting either model, which makes it the most useful thing in the
  certificate when both models are wrong in the same direction.

Confidence numbers, probabilities, and reliability scores are rejected here for
the same reason they are rejected everywhere else in this runtime.

## How independent is independent

There are four tiers, and a review has to name which one it is:

| Tier | What it means |
|---|---|
| `CROSS_FAMILY` | A different vendor's model. Different training data, different blind spots. |
| `SAME_FAMILY` | A different model from the same vendor. |
| `SAME_MODEL` | The same model, fresh context, never shown the first conclusion. |
| `SAME_CONTEXT` | The same model continuing the same conversation. Never accepted. |

**Yes, a model reviewing itself counts — as long as the context is fresh.** This
matters, because plenty of machines only have one model available. A second pass
that has not seen the first conclusion still catches real mistakes: a misread
quantifier, a scope that was silently widened, an entailment that does not hold.
What it cannot catch is anything the model gets wrong for reasons built into the
model, which is why it is the weakest admissible tier rather than a refused one.

`SAME_CONTEXT` is refused because a model asked to check what it just said is not
reviewing, it is agreeing.

### The claim is checked, not trusted

The runtime derives the strongest tier two reviewer ids could honestly support
and rejects anything above it:

```text
claude-opus-5   vs claude-opus-5              -> ceiling SAME_MODEL
claude-opus-5   vs claude-haiku-4-5           -> ceiling SAME_FAMILY
claude-opus-5   vs gpt-5-codex                -> ceiling CROSS_FAMILY
claude-opus-5   vs my-private-model           -> ceiling SAME_FAMILY   (unrecognised id)
```

An unrecognised model id caps at `SAME_FAMILY` rather than being taken at its
word. Add prefixes to `model_families` in `references/reviewers.json` for models
you use.

One field is not mechanically checkable: whether the context really was fresh.
Nothing in a JSON payload can prove that. It is the honest boundary of this gate,
and it is why `SAME_MODEL` is the floor rather than something to rely on.

### Setting a floor

```bash
python3 scripts/compile_claim.py claim.json --min-independence CROSS_FAMILY
```

Payload field `adversarial_min_independence`, environment variable
`KNOWSIFT_ADVERSARIAL_MIN_INDEPENDENCE`, and the flag resolve to the strictest.
Default floor is `SAME_MODEL`: everything except a model agreeing with itself.

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

### Nested calls and inherited credentials

A parent harness injects credentials scoped to its own session. A reviewer
spawned as a child process inherits them and then authenticates as the parent, or
fails outright — which looks exactly like the CLI being broken:

```text
inheriting the parent session's ANTHROPIC_*   -> 401 Invalid bearer token
with those keys removed                       -> works
```

Each backend names the variables to drop in `scrub_env`, so the child uses the
tool's own stored credentials. If a backend fails to authenticate only when
nested, that list is the first thing to extend.

### Route A — the host Agent's own subagent

No second CLI needed. The host runs the same prompt in an isolated subagent
under a different model:

```bash
python3 scripts/adversarial_review.py prompt claim.json
```

Give that output to the subagent verbatim, take back the JSON, then `merge` it
with `--reviewer-id` set to the model that actually ran.

Pass `--first-pass-reviewer-id` so the tier is derived rather than asserted. If
the subagent runs the same model as the first pass, that is `SAME_MODEL`, which
is admissible under the default floor and recorded as what it is.

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

The tiers exist so this degradation is visible instead of hidden. A certificate
records `weakest_independence`, so a reader can tell the difference between two
vendors agreeing and one model agreeing with itself twice.
