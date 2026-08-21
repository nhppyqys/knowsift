# Protocols

`protocol-registry.json` is the routing source of truth. The runtime rejects an unregistered route or a registered protocol without an implemented validator.

## Base protocols

- `FORMAL_PROOF`: requires an external checker or explicit proof-audit artifact, method, and passing result.
- `DEFINITION`: requires an entailing source that actually states the definition.
- `FACTUAL_RECORD`: requires traceable evidence and an accepted semantic relation.
- `LEGAL_AUTHORITY`: requires jurisdiction, authority type, citation, effective date/version, and an operative evidence reference. Verified exceptions narrow absolute formulations.
- `STATISTICAL_INFERENCE`: requires an effect or comparison measure, finite estimate, uncertainty or sample size, and a declared comparison.
- `CAUSAL_INFERENCE`: requires a recognized design plus evidence-linked treatment of every design assumption. Structural completeness alone is not causal proof.
- `PREDICTIVE_VALIDATION`: requires an out-of-sample evaluation, metric, baseline, and evaluation scope.
- `PRESCRIPTIVE_DECISION`: requires an objective, alternatives, constraints, tradeoffs, and evidence references. Evidence cannot choose user values.
- `CONDITIONAL_PHENOMENON`: requires an operational outcome and evidence-linked observed conditions.
- `SOURCE_ATTESTATION`: characterizes what a source states; it does not promote the statement to world truth.
- `SCOPE_BOUNDARY`: compares claimed and verified scope and safely narrows mismatches.

## Augmenting protocols

- `GENERALIZATION`: routed for `ALL`, `MOST`, and `GENERALLY`. Without an evidence-linked transport basis, the runtime removes the unsupported generalization and returns a scoped result.
- `VERSIONED_TECHNICAL_SPEC`: routed by version-sensitive domains and requires a declared version linked to matching evidence. Version checks may accept appropriately classified `PARTIAL` evidence so an evidence-linked component can be admitted, but partial support never admits the complete claim.
- `EVIDENCE_SYNTHESIS`: routed when `protocol_inputs.evidence_synthesis` is present. Each study record must link a unique study and evidence ID; two or more compatible scalar effects and positive variances may then be recomputed with fixed-effect or DerSimonian-Laird random-effects models. Effect-measure compatibility, study dependence, and model choice require named methods or rationales rather than bare booleans. Specialized synthesis types hold for a dedicated method.
- `HISTORICAL_SOURCE_CRITICISM`: routed for the history domain and records event/source distance, source type, and provenance independence without turning those features into a truth score.
- `PRACTITIONER_HEURISTIC`: routed when explicitly requested. It requires context, limits, and evidence-linked observations and can only pass as scoped.

## Causal designs

Supported designs and their mandatory assumptions are stored in `causal-designs.json`: RCT, DID, IV, RDD, and OBSERVATIONAL. Every assumption must have a non-empty method or rationale and at least one known evidence ID. Missing or merely asserted assumptions hold the claim.

## Protocol result states

- `PASS`: complete deterministic and traceability checks.
- `PASS_SCOPED`: safe only after deterministic narrowing.
- `HOLD`: incomplete, unclassified, or unresolved.
- `FAIL`: decisive contradiction or impossible condition.
