# SSSOM specification artifacts (vendored)

Pinned copies of the SSSOM specification used by
`test_rules_export_sssom_conformance.py` to check that the SSSOM rules export
conforms to the standard, without depending on a third-party SSSOM parser.

- Source: https://github.com/mapping-commons/sssom
- Release tag: `v1.0.0` (commit `658de421c21a686f1213ff41879c9245ac0b4925`)
- Licence: BSD 3-Clause, see `LICENSE`

| File | Source path in that repo |
| --- | --- |
| `sssom_schema.schema.json` | `project/jsonschema/sssom_schema.schema.json` |
| `sssom_schema.yaml` | `src/sssom_schema/schema/sssom_schema.yaml` (LinkML source of truth) |
| `examples/*.sssom.tsv` | `examples/embedded/` (official example files, used as positive controls) |
| `examples/schema/extension-slots.sssom.tsv` | `examples/schema/` (official example of extension slots) |
| `examples/schema/literals.sssom.tsv` | `examples/schema/` (official example of literal mappings) |

## Known deviations

The Carrot export deliberately departs from SSSOM 1.0.0 in two ways, so it does
not pass a strict SSSOM validator:

- no `mapping_set_id` (required: `sssom_schema.yaml` L294–298);
- no `license` (required on the mapping set: `sssom_schema.yaml` L612–616).

Both are left for publishing to the mappings registry, which will provide them.

The conformance tests accept exactly these (`KNOWN_DEVIATIONS` in
`test_rules_export_sssom_conformance.py`) and fail on any other spec violation.
