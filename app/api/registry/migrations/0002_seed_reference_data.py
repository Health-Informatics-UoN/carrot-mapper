from django.db import migrations

ORIGINS = [
    (
        "CARROT_DIRECT_PUBLISH",
        "Carrot direct publish",
        "Published directly from a Carrot Mapper scan report.",
    ),
    ("SSSOM_UPLOAD", "SSSOM upload", "Imported from an uploaded SSSOM file."),
]

STATUSES = [
    ("DRAFT", "Draft", "Not yet publicly visible."),
    ("PUBLISHED", "Published", "Publicly visible, searchable and downloadable."),
    ("WITHDRAWN", "Withdrawn", "Previously published, no longer recommended for use."),
]

# (predicate_id, label, description, is_recommended)
PREDICATES = [
    (
        "skos:exactMatch",
        "exact match",
        "The subject and object can be used interchangeably.",
        True,
    ),
    (
        "skos:closeMatch",
        "close match",
        "The subject and object are similar enough to be used interchangeably in some contexts.",
        True,
    ),
    ("skos:broadMatch", "broad match", "The object is broader than the subject.", True),
    (
        "skos:narrowMatch",
        "narrow match",
        "The object is narrower than the subject.",
        True,
    ),
    (
        "skos:relatedMatch",
        "related match",
        "The subject and object are associated in some unspecified way.",
        True,
    ),
    (
        "owl:equivalentClass",
        "equivalent class",
        "The subject and object classes are logically equivalent.",
        False,
    ),
    (
        "owl:sameAs",
        "same as",
        "The subject and object individuals are the same.",
        False,
    ),
    (
        "rdfs:subClassOf",
        "subclass of",
        "The subject class is a subclass of the object class.",
        False,
    ),
    (
        "oboInOwl:hasDbXref",
        "has database cross reference",
        "Weak cross-reference between subject and object.",
        False,
    ),
]

JUSTIFICATIONS = [
    (
        "semapv:ManualMappingCuration",
        "manual mapping curation",
        "Mapping established by a human curator.",
    ),
    (
        "semapv:LexicalMatching",
        "lexical matching",
        "Mapping established by comparing lexical features such as labels.",
    ),
    (
        "semapv:LexicalSimilarityThresholdMatching",
        "lexical similarity threshold matching",
        "Mapping established when lexical similarity exceeds a threshold.",
    ),
    (
        "semapv:SemanticSimilarityThresholdMatching",
        "semantic similarity threshold matching",
        "Mapping established when semantic similarity exceeds a threshold.",
    ),
    (
        "semapv:LogicalReasoning",
        "logical reasoning",
        "Mapping inferred by a logical reasoner.",
    ),
    (
        "semapv:CompositeMatching",
        "composite matching",
        "Mapping established using a combination of approaches.",
    ),
    (
        "semapv:MappingChaining",
        "mapping chaining",
        "Mapping inferred by chaining other mappings.",
    ),
    (
        "semapv:MappingReview",
        "mapping review",
        "Mapping reviewed and confirmed by a reviewer.",
    ),
    (
        "semapv:UnspecifiedMatching",
        "unspecified matching",
        "The matching process is unknown or unspecified.",
    ),
]


def seed(apps, schema_editor):
    Origin = apps.get_model("registry", "Origin")
    Status = apps.get_model("registry", "Status")
    Predicate = apps.get_model("registry", "Predicate")
    MappingJustification = apps.get_model("registry", "MappingJustification")

    for id_, label, desc in ORIGINS:
        Origin.objects.update_or_create(
            id=id_, defaults={"label": label, "description": desc}
        )
    for id_, label, desc in STATUSES:
        Status.objects.update_or_create(
            id=id_, defaults={"label": label, "description": desc}
        )
    for pid, label, desc, rec in PREDICATES:
        Predicate.objects.update_or_create(
            predicate_id=pid,
            defaults={"label": label, "description": desc, "is_recommended": rec},
        )
    for jid, label, desc in JUSTIFICATIONS:
        MappingJustification.objects.update_or_create(
            justification_id=jid, defaults={"label": label, "description": desc}
        )


def unseed(apps, schema_editor):
    apps.get_model("registry", "Origin").objects.filter(
        id__in=[o[0] for o in ORIGINS]
    ).delete()
    apps.get_model("registry", "Status").objects.filter(
        id__in=[s[0] for s in STATUSES]
    ).delete()
    apps.get_model("registry", "Predicate").objects.filter(
        predicate_id__in=[p[0] for p in PREDICATES]
    ).delete()
    apps.get_model("registry", "MappingJustification").objects.filter(
        justification_id__in=[j[0] for j in JUSTIFICATIONS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("registry", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
