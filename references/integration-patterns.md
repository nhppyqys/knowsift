# Product integration patterns

KnowSift owns the boundary between collected material and reusable knowledge. It can validate a collected source bundle, compile individual claims, and render a layered knowledge document. It does not own web search, video download, speech-to-text, OCR, vector retrieval, or long-term storage.

## External research Agent to knowledge document

1. Let the user's existing Agent, browser, connector, or ingestion system collect videos, articles, papers, and documents.
2. Preserve full text or transcripts, stable source IDs, titles, URLs, timestamps, capture dates, and the role each source can actually play.
3. Pass the collected items through `validate_source_bundle.py`.
4. Extract independently checkable claims. Compile world claims, source reports, recommendations, anecdotes, and conflicts separately.
5. Build a document plan that maps certificates to the compatible layer.
6. Render the final Markdown with `build_knowledge_document.py`.
7. Send unresolved claims back to the research Agent as targeted evidence gaps instead of broad new searches.

The resulting document is intentionally not a popularity summary. Ten videos repeating one unsupported claim remain repeated testimony; they do not become ten independent proofs.

## Certified knowledge base

1. Ingest documents into a source store with stable source IDs and immutable text snapshots. Record each item's `locator` and a `snapshot` of `{path, sha256}`, then run the compiler with `--locator required --snapshot required --snapshot-root <store>` so a mislabelled or un-captured source cannot enter the base at all.
2. Extract independently checkable claims and evidence anchors.
3. Compile each claim separately.
4. Store `ADMIT` and `ADMIT_SCOPED` certificates as usable knowledge.
5. For `ADMIT_COMPONENTS_ONLY`, store only `supported_components`; never store the original complete claim as admitted knowledge.
6. Route `HOLD` to evidence collection or human review and retain `REJECT` as conflict history.
7. Recompile affected claims when a source, regulation, model version, or policy changes.

## Agent memory firewall

Set `KNOWSIFT_ADVERSARIAL_POLICY=required` in the environment that runs the compiler. A memory an Agent proposes about itself is the case where a single self-assessed semantic review is least trustworthy, and the environment variable is the one place an upstream Agent cannot edit.

Before an Agent writes a durable factual or policy memory, compile the proposed memory against its source. Personal preferences and user-provided facts may be stored as explicitly scoped user context, but they must not be promoted to organization policy or world truth without appropriate evidence.

At retrieval time, prefer admitted certificates over raw documents. If no admitted claim answers the question, report the gap instead of silently falling back to an unsupported memory.

## Compliance and high-stakes review

Keep jurisdiction, effective date, population, version, exceptions, and source hierarchy in the Claim IR and evidence. A product layer should show a concise decisive result first and make the complete machine checks available as an audit view.

Human approval may authorize a decision or exception, but it must not rewrite a `HOLD` or `REJECT` certificate into evidentiary support. Record the approval as a separate decision artifact.

## Batch and change orchestration

Use the input digest and stable claim/source IDs to detect unchanged work. Maintain a reverse index from source IDs to claim IDs so a changed source invalidates and recompiles only affected claims.

Batch systems should track counts by admission state, review age, source version, and unresolved reason. Do not aggregate them into a universal confidence score.
