# Validation

Validation date: 2026-08-22

## Automated tests

The complete suite passes on both supported runtimes:

| Runtime | Tests | Result |
|---|---:|---|
| Python 3.9.6 | 83 | Pass |
| Python 3.14.6 | 83 | Pass |

Run it with:

```bash
python3 -m unittest discover -s tests -v
```

The suite covers:

- malformed and unknown input failing closed;
- exact source-text and quote anchors;
- semantic support, contradiction, partial support, and conflict;
- source authority and provenance cycles;
- scope, version, legal, causal, statistical, predictive, and other protocol routing;
- component-only admission without leaking the broader claim;
- independent second-reviewer agreement, disagreement, self-review, invented quotes, and policy escalation;
- reviewer-route detection reporting an installed-but-unrunnable CLI as unavailable;
- source-bundle structure and path containment;
- certificate-to-document layer compatibility;
- `HOLD` claims being blocked from knowledge sections;
- arbitrary text being blocked from reusing an unrelated `HOLD` certificate;
- the complete learning-English demo and byte-for-byte Markdown regeneration;
- the 17-source short-drama benchmark, all 27 certificates, exact 17 / 5 / 3 / 2 layer boundaries, and byte-for-byte Markdown regeneration.

## Schema checks

The shipped source bundles, document plans, and demo certificates validate against their JSON Schemas.

## End-to-end demo result

The fictional five-source demo compiles into:

| Layer | Records |
|---|---:|
| Supported knowledge | 1 |
| Practitioner/viewpoint/anecdote | 3 |
| Disputed or unresolved | 2 |

The research result retains its study scope. Two creator statements and one learner story remain attestations. A conflicting absolute recommendation and an unsupported marketing promise cannot enter the knowledge section.

## Real-world benchmark result

The short-drama benchmark compiles 17 captured sources into 27 independently certified claims:

| Layer | Records |
|---|---:|
| Supported knowledge | 17 |
| Practitioner/viewpoint/anecdote | 5 |
| Disputed or unresolved | 3 |
| Rejected | 2 |

Creator earnings claims remain anecdotes or unresolved marketing claims. Platform thresholds, monetization rules, rights requirements, regulatory boundaries, and a distributor's public submission terms enter the knowledge layer only within their declared scope.

## What this validation proves

It proves that, given a structured claim, evidence links, and semantic reviews, the runtime deterministically enforces its admission and document-layer rules.

It does not prove that an upstream Agent extracted every relevant claim, classified every source correctly, or judged semantic relations correctly. Those steps still require a capable host Agent, appropriate sources, and human review for high-stakes work.
