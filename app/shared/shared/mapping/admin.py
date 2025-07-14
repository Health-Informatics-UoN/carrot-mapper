from django.contrib import admin
from shared.mapping.models import (
    DataDictionary,
    DataPartner,
    Dataset,
    MappingRule,
    OmopField,
    OmopTable,
    Project,
    ScanReport,
    ScanReportConcept,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
    MappingRecommendation,
)


class DataPartnerAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )


class ScanReportAdmin(admin.ModelAdmin):
    raw_id_fields = ("data_dictionary",)
    filter_horizontal = (
        "viewers",
        "editors",
    )
    list_display = (
        "id",
        "get_name",
        "get_parent_dataset",
    )

    def get_name(self, obj):
        return obj.dataset

    get_name.short_description = "Scan Report Name"

    def get_parent_dataset(self, obj):
        return "%s: %s" % (obj.parent_dataset.id, obj.parent_dataset.name)

    get_parent_dataset.short_description = "Parent Dataset"


class ScanReportTableAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "person_id",
        "date_event",
    )
    list_display = (
        "id",
        "get_name",
        "get_scan_report",
    )

    def get_name(self, obj):
        return obj.name

    get_name.short_description = "Name"

    def get_scan_report(self, obj):
        return "%s: %s" % (obj.scan_report.id, obj.scan_report.dataset)

    get_scan_report.short_description = "Scan Report"


class ScanReportFieldAdmin(admin.ModelAdmin):
    list_display = ("id", "get_name", "get_scan_report_table", "get_scan_report")

    def get_name(self, obj):
        return obj.name

    get_name.short_description = "Name"

    def get_scan_report_table(self, obj):
        return "%s: %s" % (obj.scan_report_table.id, obj.scan_report_table.name)

    get_scan_report_table.short_description = "Scan Report Table"

    def get_scan_report(self, obj):
        return "%s: %s" % (
            obj.scan_report_table.scan_report.id,
            obj.scan_report_table.scan_report.dataset,
        )

    get_scan_report.short_description = "Scan Report"


class ScanReportValueAdmin(admin.ModelAdmin):
    raw_id_fields = ("scan_report_field",)
    list_display = (
        "id",
        "get_name",
        "get_field",
    )

    def get_name(self, obj):
        return obj.value

    get_name.short_description = "Value"

    def get_field(self, obj):
        return "%s: %s" % (obj.scan_report_field.id, obj.scan_report_field.name)

    get_field.short_description = "Scan Report Field"


class MappingRuleAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "scan_report",
        "omop_field",
        "source_field",
        "concept",
    )
    list_display = (
        "id",
        "concept",
        "get_omop_field",
        "get_concept",
        "source_field",
    )

    def get_concept(self, obj):
        return "%s: %s" % (
            obj.concept.concept.concept_id,
            obj.concept.concept.concept_name,
        )

    get_concept.short_description = "OMOP Concept"

    def get_omop_field(self, obj):
        return "%s" % (obj.omop_field.field)

    get_omop_field.short_description = "OMOP Field"


class DataDictionaryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
    )


class OmopTableAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "table",
    )


class OmopFieldAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "field",
        "get_table",
    )

    def get_table(self, obj):
        return "%s: %s" % (obj.table.id, obj.table.table)

    get_table.short_description = "OMOP Table"


class ScanReportConceptAdmin(admin.ModelAdmin):
    raw_id_fields = (
        "concept",
        # "content_object",  # This is not in raw_id_fields because unit test throw
        # an error as content_object is a GenericForeignKey and not a ForeignKey or
        # ManyToMany. However, this does mean navigating to the ScanReportConcept
        # admin page will be very slow.
    )
    list_display = (
        "id",
        "concept",
        "object_id",
    )


class DatasetAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "viewers",
        "admins",
        "editors",
    )
    list_display = (
        "id",
        "name",
        "visibility",
    )


class ProjectAdmin(admin.ModelAdmin):
    filter_horizontal = (
        "datasets",
        "members",
    )
    list_display = (
        "name",
        "id",
    )


class MappingRecommendationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created_at",
        "get_content_object",
        "concept",
        "score",
        "tool_name",
        "tool_version",
    )
    raw_id_fields = ("concept",)

    def get_content_object(self, obj):
        return obj.content_object

    get_content_object.short_description = "Content Object"


admin.site.register(DataPartner, DataPartnerAdmin)
admin.site.register(ScanReport, ScanReportAdmin)
admin.site.register(ScanReportTable, ScanReportTableAdmin)
admin.site.register(ScanReportField, ScanReportFieldAdmin)
admin.site.register(ScanReportValue, ScanReportValueAdmin)
admin.site.register(OmopTable, OmopTableAdmin)
admin.site.register(OmopField, OmopFieldAdmin)
admin.site.register(MappingRule, MappingRuleAdmin)
admin.site.register(DataDictionary, DataDictionaryAdmin)
admin.site.register(ScanReportConcept, ScanReportConceptAdmin)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(Project, ProjectAdmin)
admin.site.register(MappingRecommendation, MappingRecommendationAdmin)
