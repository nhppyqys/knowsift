# Layered knowledge document mode

Use this mode after an external Agent, user, connector, search system, or ingestion pipeline has collected multiple source items. The output is not a summary of what appeared most often. It is a certificate-backed map of what may be reused as knowledge and what must retain a weaker status.

## 1. Define the research boundary

Record:

- the question the document must answer;
- the intended audience and desired depth;
- which platforms, dates, languages, source types, and retrieved items are in scope;
- whether the user wants a map of the collected content or a broader evidence review.

Do not silently change “review these videos” into “establish world truth.” If the collected material cannot support the stronger goal, report the gap and request or retrieve stronger evidence only when separately authorized.

## 2. Build and validate a source bundle

Follow `source-bundle.schema.json`. A source's medium and epistemic role are different:

- `medium` answers whether it is a video, paper, article, document, dataset, or other carrier;
- `source_type` answers what evidentiary role it can play in this document.

Examples:

- a YouTube interview can be `VIDEO` + `EXPERT_INTERPRETATION`;
- a Bilibili personal story can be `VIDEO` + `ANECDOTE`;
- a recorded product launch can be `VIDEO` + `OFFICIAL_DOCUMENTATION` for what was announced;
- a peer-reviewed paper can be `PAPER` + `RESEARCH`;
- a promotional tutorial can be `VIDEO` + `MARKETING`.

Use stable source IDs and preserve transcript timestamps or locators when available. Validate the bundle:

```bash
python3 scripts/validate_source_bundle.py path/to/source-bundle.json
```

## 3. Extract and group claims

Extract only independently checkable assertions. Keep recommendations, causal claims, predictions, definitions, measurements, personal reports, and opinions distinct.

Group semantically equivalent claims before compiling, but preserve every source link. Count repeated sources only as repeated attestation; do not turn frequency into truth or confidence.

For each group, ask:

1. Is this a world claim, a source report, a recommendation, or an interpretation?
2. Which evidence directly entails, contradicts, partially supports, or fails to address it?
3. What population, version, time, setting, dose, or condition is actually supported?
4. Are multiple sources independent, or are they repeating the same upstream source?

## 4. Compile the right claim type

### World or domain claim

Compile the substantive claim against evidence appropriate for its domain and operator. A popular creator's statement is not appropriate evidence merely because it is clear or repeated.

### Viewpoint, recommendation, or anecdote

Compile an `OBSERVE` attestation such as:

```text
讲师甲主张成年人不应该背单词。
学习者乙自述自己在三个月内达到流利。
```

The certificate establishes what the source stated, not that the underlying advice or result is universally true.

### Compound claim

When evidence supports only part, create evidence-linked `supported_components`. The document may contain only those exact component records.

## 5. Build the document plan

Follow `knowledge-document-input.schema.json`. Each record references one generated certificate and one layer:

| Layer | Required certificate | Meaning |
|---|---|---|
| `SUPPORTED_KNOWLEDGE` | `ADMIT` | Supported claim from a knowledge-capable source |
| `CONDITIONAL_KNOWLEDGE` | `ADMIT_SCOPED` | Supported only with the complete canonical scope |
| `SUPPORTED_COMPONENT` | `ADMIT_COMPONENTS_ONLY` | Only one exact certified component |
| `PRACTICE_OR_VIEWPOINT` | admitted `OBSERVE` | What a practitioner, expert, or person reports or believes |
| `DISPUTED_OR_UNRESOLVED` | `HOLD` | Conflict, missing evidence, or unresolved protocol |
| `REJECTED` | `REJECT` | Claim excluded by decisive contradiction or failure |

`explanation`, `conditions`, and `limitations` are reader-facing compiler notes, not new evidence. Do not add factual content that is absent from the cited certificate and sources.

## 6. Render and inspect

Render Markdown:

```bash
python3 scripts/build_knowledge_document.py \
  path/to/knowledge-document.json \
  --output path/to/knowledge-document.md
```

Inspect the final document for:

- an answerable question and explicit source boundary;
- knowledge sections containing only compatible admitted certificates;
- viewpoints phrased as source reports, not world truth;
- conflicts and unresolved questions remaining visible;
- every substantive record pointing to its certificate and source IDs;
- no unsupported complete claim leaking from a component-only certificate.

## 7. When to stop

Stop and report an evidence gap when the source set supports only a content map, not a professional knowledge conclusion. A useful result may say “these creators agree” while refusing to say “this is established.” Do not manufacture certainty to make the document feel complete.
