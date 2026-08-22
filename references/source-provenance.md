# Source provenance

Two gates sit below the semantic layer. They do not ask whether a claim is true.
They ask whether a piece of evidence is what the upstream Agent says it is.

## The hole they close

Everything downstream of `source_kind` is mechanical: source authority, protocol
routing, admission. But `source_kind` itself was a string the upstream Agent
wrote about itself. Change one word and a course sales page becomes official
documentation:

```text
before   "source_kind": "marketing_copy"          -> HOLD
before   "source_kind": "official_documentation"  -> ADMIT
```

The evidence never changed. Only the label did. That is not a subtle flaw; it is
the load-bearing assumption of the whole runtime, held up by an LLM's honesty.

The same applies one level lower. Anchors were checked byte for byte against
`source_text` — but `source_text` was itself written by whoever did the capture.
A perfect anchor into a summary proves nothing about the page it summarises.

## Locator authority

Give evidence a `locator` and the runtime works out which roles that address can
legitimately play, then checks the declared `source_kind` against them.

```json
{
  "evidence_id": "E-SD-HOLD-001",
  "source_kind": "official_documentation",
  "locator": "https://www.bilibili.com/video/BV1n3Vz6LEVS/"
}
```

```text
LOCATOR_GATE:SOURCE_KIND_CONTRADICTED_BY_LOCATOR
  OFFICIAL not in ['MARKETING', 'USER']  (Bilibili uploaded video)
```

The path matters, not just the host. On one domain:

| Locator | Permits |
|---|---|
| `bilibili.com/blackboard/charge-privacy.html` | `OFFICIAL` — the platform's own rules |
| `bilibili.com/video/BV…` | `USER`, `MARKETING` — whatever an account uploaded |

Matching picks the single most specific rule: host suffix first, then the longest
matching path prefix. Subdomains inherit their parent's rule, `www.` is ignored.
A short demotion list then strips roles a path cannot support — a `/blog/` page
is editorial even on an official domain.

The 92 `source_kind` values in the domain registry map onto six classes:
`OFFICIAL`, `SCHOLARLY`, `GUIDANCE`, `USER`, `MARKETING`, `DATA`. A test fails if
a new kind is added to the domain registry without being classified here.

### Unknown hosts

`references/source-kinds.json` covers governments, platform help centres,
scholarly hosts, code hosts, and the large user-generated platforms. It is
deliberately small, and anything not in it is reported as **unverifiable**, never
as acceptable and never as a violation:

```text
optional  unverifiable passes, and the certificate records that it was unchecked
required  unverifiable is a HOLD, so you must add a rule or accept the gap
```

Add hosts you rely on. A rule you wrote is auditable; an LLM's assertion is not.

## Snapshot integrity

Give evidence a `snapshot` and the runtime hashes the captured file, compares it
to the declared digest, and checks that `source_text` appears literally inside
it.

```json
{
  "source_text": "The official record states: Widget supports signed exports.",
  "snapshot": {"path": "captures/record.txt", "sha256": "9f86d0…"}
}
```

Four things fail closed: a digest that does not match the file, a `source_text`
that is not inside the capture, a path that escapes the snapshot root, and a
capture that is not decodable UTF-8. The root comes from `--snapshot-root`,
`KNOWSIFT_SNAPSHOT_ROOT`, or the `snapshot_root` argument.

This is what stops someone quoting a passage that only exists in their notes.

## Policies

Both gates use the same three states and the same resolution rule as adversarial
review: the effective policy is the **strictest** of the payload field, the
environment variable, and the CLI flag.

| | payload | environment | flag |
|---|---|---|---|
| locator | `locator_policy` | `KNOWSIFT_LOCATOR_POLICY` | `--locator` |
| snapshot | `snapshot_policy` | `KNOWSIFT_SNAPSHOT_POLICY` | `--snapshot` |

Default is `optional`: supplied values are checked, absent ones are not
penalised, so existing inputs keep working unchanged.

```bash
python3 scripts/compile_claim.py claim.json \
  --locator required --snapshot required --snapshot-root ./captures
```

## What is still not proven

A locator rule says *who can speak* at an address. It says nothing about whether
they were right. An official page can be outdated, wrong, or later retracted, and
this gate will happily admit it.

A snapshot proves the quote came out of the bytes on disk. It does not prove
those bytes are what the server actually returned, or that the page still says
so today. Capture-time honesty still rests on whoever ran the capture.

So the regress is shortened, not removed. It used to end at "an LLM said this was
official". It now ends at "a rule I wrote says this host can be official, and a
file I captured contains this sentence". Both of those are things a person can
inspect, which is the whole difference.
