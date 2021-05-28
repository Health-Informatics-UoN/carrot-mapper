import ast
import json
import os
import time
from io import StringIO

import pandas as pd
import requests
from data.models import Concept
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordChangeDoneView
from django.contrib.contenttypes.models import ContentType
from django.core.mail import BadHeaderError, send_mail
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import CharField
from django.db.models import Value as V
from django.db.models.functions import Concat
from django.db.models.query_utils import Q
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views import generic
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import DetailView, ListView
from django.views.generic.edit import FormView, UpdateView

from .forms import (
    DictionarySelectForm,
    DocumentFileForm,
    DocumentForm,
    NLPForm,
    ScanReportAssertionForm,
    ScanReportFieldConceptForm,
    ScanReportForm,
    UserCreateForm, ScanReportValueConceptForm,
    ScanReportFieldForm,
)
from .models import (
    DataDictionary,
    Document,
    DocumentFile,
    NLPModel,
    OmopField,
    ScanReport,
    ScanReportAssertion,
    ScanReportField,
    ScanReportTable,
    ScanReportValue,
    StructuralMappingRule, ScanReportConcept,
)
from .services import process_scan_report
from .services_nlp import start_nlp
from .services_datadictionary import merge_external_dictionary

@login_required
def home(request):
    return render(request, "mapping/home.html", {})


@method_decorator(login_required, name="dispatch")
class ScanReportTableListView(ListView):
    model = ScanReportTable

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.request.GET.get("search", None)
        if search_term is not None and search_term != "":
            qs = qs.filter(scan_report__id=search_term).order_by("name")

        return qs

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        if len(self.get_queryset()) > 0:
            scan_report = self.get_queryset()[0].scan_report
            scan_report_table = self.get_queryset()[0]
        else:
            scan_report = None
            scan_report_table = None

        context.update(
            {
                "scan_report": scan_report,
                "scan_report_table": scan_report_table,
            }
        )

        return context

@method_decorator(login_required, name="dispatch")
class ScanReportTableUpdateView(UpdateView):
    model = ScanReportTable
    fields = [
        "person_id",
        "birth_date",
        "measurement_date",
        "observation_date",
        "condition_date"
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        #filter so the objects can only be associated to the current scanreport table
        scan_report_table = context['scanreporttable']
        qs = ScanReportField\
            .objects\
            .filter(scan_report_table=scan_report_table)\
            .order_by("name")

        for key in context['form'].fields.keys():
            context['form'].fields[key].queryset = qs

            def label_from_instance(obj):
                return obj.name
            
            context['form'].fields[key].label_from_instance = label_from_instance
        return context
    
    def get_success_url(self):
        return "{}?search={}".format(
            reverse("tables"), self.object.scan_report.id
        )

@method_decorator(login_required, name="dispatch")
class ScanReportFieldListView(ListView):
    model = ScanReportField
    fields = ["concept_id"]
    template_name="mapping/scanreportfield_list.html"
    factory_kwargs = {"can_delete": False, "extra": False}

    def get_queryset(self):
        qs = super().get_queryset().order_by("id")
        search_term = self.request.GET.get("search", None)
        if search_term is not None:
            qs = qs.filter(scan_report_table__id=search_term)
        return qs

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)
    
        if len(self.get_queryset()) > 0:
            scan_report = self.get_queryset()[0].scan_report_table.scan_report
            scan_report_table = self.get_queryset()[0].scan_report_table
            scan_report_field = self.get_queryset()[0]
        else:
            scan_report = None
            scan_report_table = None
            scan_report_field = None

        context.update(
            {
                "scan_report": scan_report,
                "scan_report_table": scan_report_table,
                "scan_report_field": scan_report_field,
            }
        )

        return context


@method_decorator(login_required, name="dispatch")
class ScanReportFieldUpdateView(UpdateView):
    model = ScanReportField
    form_class=ScanReportFieldForm
    template_name="mapping/scanreportfield_form.html"

    def get_success_url(self):
        return "{}?search={}".format(
            reverse("fields"), self.object.scan_report_table.id
        )


@method_decorator(login_required, name="dispatch")
class ScanReportStructuralMappingUpdateView(UpdateView):
    model = ScanReportField
    fields = ["mapping"]\

    def get_success_url(self):
        return "{}?search={}".format(
            reverse("fields"), self.object.scan_report_table.id
        )


@method_decorator(login_required, name="dispatch")
class ScanReportListView(ListView):
    model = ScanReport
    #order the scanreports now so the latest is first in the table
    ordering = ['-created_at']

    #handle and post methods
    #so far just handle a post when a button to click to hide/show a report
    def post(self, request, *args, **kwargs):
        #obtain the scanreport id from the buttont that is clicked
        _id = request.POST.get("scanreport_id")
        if _id is not None:
            #obtain the scan report based on this id
            report = ScanReport.objects.get(pk=_id)
            #switch hidden True -> False, or False -> True, if clicked
            report.hidden = not report.hidden
            #update the model
            report.save()
        #return to the same page        
        return redirect(request.META['HTTP_REFERER'])


    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        #add the current user to the context
        #this is needed so the hide/show buttons can be only turned on
        #by whoever created the report
        context['current_user'] = self.request.user
        context['filterset'] = self.filterset
        
        return context
        
    
    def get_queryset(self):
        search_term = self.request.GET.get("filter", None)
        qs = super().get_queryset()
        if search_term == "archived":
            qs = qs.filter(hidden=True)
            self.filterset="Archived"
        else:
            qs = qs.filter(hidden=False)
            self.filterset="Active"
        return qs


@method_decorator(login_required, name="dispatch")
class ScanReportValueListView(ListView):
    model = ScanReportValue
    template_name = "mapping/scanreportvalue_list.html"
    fields = ["conceptID"]
    factory_kwargs = {"can_delete": False, "extra": False}

    def get_queryset(self):
        search_term = self.request.GET.get("search", None)

        if search_term is not None:
            # qs = ScanReportValue.objects.select_related('concepts').filter(scan_report_field=search_term)
            qs = ScanReportValue.objects.filter(scan_report_field=search_term).order_by('value')
        else:
            qs = ScanReportValue.objects.all()

        return qs

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        if len(self.get_queryset()) > 0:
            # scan_report = self.get_queryset()[0].scan_report_table.scan_report
            # scan_report_table = self.get_queryset()[0].scan_report_table
            scan_report = self.get_queryset()[
                0
            ].scan_report_field.scan_report_table.scan_report
            scan_report_table = self.get_queryset()[
                0
            ].scan_report_field.scan_report_table
            scan_report_field = self.get_queryset()[0].scan_report_field
            scan_report_value = self.get_queryset()[0]
        else:
            scan_report = None
            scan_report_table = None
            scan_report_field = None
            scan_report_value = None

        context.update(
            {
                "scan_report": scan_report,
                "scan_report_table": scan_report_table,
                "scan_report_field": scan_report_field,
                "scan_report_value": scan_report_value,
            }
        )

        return context


@method_decorator(login_required, name="dispatch")
class StructuralMappingTableListView(ListView):
    model = StructuralMappingRule
    template_name = "mapping/mappingrulesscanreport_list.html"

    def get_queryset(self):
        scan_report = ScanReport.objects.get(pk=self.kwargs.get("pk"))

        qs = super().get_queryset()
        search_term = self.kwargs.get("pk")

        if search_term is not None:
            qs = qs.filter(scan_report__id=search_term).order_by(
                "omop_field__table",
                "omop_field__field",
                "source_table__name",
                "source_field__name",
            )

        return qs


@method_decorator(login_required, name="dispatch")
class ScanReportFormView(FormView):
    form_class = ScanReportForm
    template_name = "mapping/upload_scan_report.html"
    success_url = reverse_lazy("scan-report-list")

    def form_valid(self, form):
        # Create an entry in ScanReport for the uploaded Scan Report
        scan_report = ScanReport.objects.create(
            data_partner=form.cleaned_data["data_partner"],
            dataset=form.cleaned_data["dataset"],
            file=form.cleaned_data["scan_report_file"],
        )
        
        scan_report.author = self.request.user
        scan_report.save()
        process_scan_report_task.delay(scan_report.id)

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class ScanReportAssertionView(ListView):
    model = ScanReportAssertion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        x = ScanReport.objects.get(pk=self.kwargs.get("pk"))
        context.update(
            {
                "scan_report": x,
            }
        )
        return context

    def get_queryset(self):
        qs = super().get_queryset()

        qs = qs.filter(scan_report=self.kwargs["pk"])
        return qs


@method_decorator(login_required, name="dispatch")
class ScanReportAssertionFormView(FormView):
    model = ScanReportAssertion
    form_class = ScanReportAssertionForm
    template_name = "mapping/scanreportassertion_form.html"

    def form_valid(self, form):
        scan_report = ScanReport.objects.get(pk=self.kwargs.get("pk"))

        assertion = ScanReportAssertion.objects.create(
            negative_assertion=form.cleaned_data["negative_assertion"],
            scan_report=scan_report,
        )
        assertion.save()

        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        return reverse("scan-report-assertion", kwargs={"pk": self.kwargs["pk"]})


@method_decorator(login_required, name="dispatch")
class ScanReportAssertionsUpdateView(UpdateView):
    model = ScanReportAssertion
    fields = [
        "negative_assertion",
    ]

    def get_success_url(self, **kwargs):
        return reverse(
            "scan-report-assertion", kwargs={"pk": self.object.scan_report.id}
        )


@method_decorator(login_required, name="dispatch")
class DocumentFormView(FormView):
    form_class = DocumentForm
    template_name = "mapping/upload_document.html"
    success_url = reverse_lazy("document-list")

    def form_valid(self, form):
        document = Document.objects.create(
            data_partner=form.cleaned_data["data_partner"],
            document_type=form.cleaned_data["document_type"],
            description=form.cleaned_data["description"],
        )
        document.owner = self.request.user

        document.save()
        document_file = DocumentFile.objects.create(
            document_file=form.cleaned_data["document_file"], size=20, document=document
        )
        document_file.save()

        # This code will be required later to import a data dictionary into the DataDictionary model
        # filepath = document_file.document_file.path
        # import_data_dictionary_task.delay(filepath)

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class DocumentListView(ListView):
    model = Document

    def get_queryset(self):
        qs = super().get_queryset().order_by("data_partner")
        return qs


@method_decorator(login_required, name="dispatch")
class DocumentFileListView(ListView):
    model = DocumentFile

    def get_queryset(self):
        qs = super().get_queryset().order_by('-status','-created_at')
        search_term = self.kwargs.get("pk")
        if search_term is not None:
            qs = qs.filter(document__id=search_term)

        return qs
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        x = Document.objects.get(pk=self.kwargs.get("pk"))
        context.update(
            {
                "document": x,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class DocumentFileFormView(FormView):
    model = DocumentFile
    form_class = DocumentFileForm
    template_name = "mapping/upload_document_file.html"
    # success_url=reverse_lazy('document-list')

    def form_valid(self, form):
        document=Document.objects.get(pk=self.kwargs.get("pk"))
        document_file = DocumentFile.objects.create(
            document_file=form.cleaned_data["document_file"],
            size=20,
            document=document,
            
        )

        document_file.save()

        return super().form_valid(form)

    def get_success_url(self, **kwargs):
        self.object = self.kwargs.get("pk")
        return reverse("file-list", kwargs={"pk": self.object})
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        x = Document.objects.get(pk=self.kwargs.get("pk"))
        context.update(
            {
                "document": x,
            }
        )
        return context


@method_decorator(login_required, name="dispatch")
class DataDictionaryListView(ListView):
    model = DataDictionary
    ordering = ["-source_value"]

    def get_queryset(self):
        qs = super().get_queryset()

        # Create a concat field for NLP to work from
        # V is imported from models, used to comma separate other fields
        qs = qs.annotate(
            nlp_string=Concat(
                "source_value__scan_report_field__name",
                V(", "),
                "source_value__value",
                V(", "),
                "dictionary_field_description",
                V(", "),
                "dictionary_value_description",
                output_field=CharField(),
            )
        )

        search_term = self.request.GET.get("search", None)
        if search_term is not None:

            assertions = ScanReportAssertion.objects.filter(scan_report__id=search_term)
            neg_assertions = assertions.values_list("negative_assertion")

            # Grabs ScanReportFields where pass_from_source=True, makes list distinct
            qs_1 = (
                qs.filter(
                    source_value__scan_report_field__scan_report_table__scan_report__id=search_term
                )
                .filter(source_value__scan_report_field__pass_from_source=True)
                .filter(source_value__scan_report_field__is_patient_id=False)
                .filter(source_value__scan_report_field__is_date_event=False)
                .filter(source_value__scan_report_field__is_ignore=False)
                .exclude(source_value__value="List truncated...")
                .distinct("source_value__scan_report_field")
                .order_by("source_value__scan_report_field")
            )

            # Grabs everything but removes all where pass_from_source=False
            # Filters out negative assertions and 'List truncated...'
            qs_2 = (
                qs.filter(
                    source_value__scan_report_field__scan_report_table__scan_report__id=search_term
                )
                .filter(source_value__scan_report_field__pass_from_source=False)
                .filter(source_value__scan_report_field__is_patient_id=False)
                .filter(source_value__scan_report_field__is_date_event=False)
                .filter(source_value__scan_report_field__is_ignore=False)
                .exclude(source_value__value="List truncated...")
                .exclude(source_value__value__in=neg_assertions)
            )

            # Stick qs_1 and qs_2 together
            qs_total = qs_1.union(qs_2)

            # Create object to convert to JSON
            for_json = qs_total.values(
                "id",
                "source_value__value",
                "source_value__scan_report_field__name",
                "nlp_string",
            )

            serialized_q = json.dumps(list(for_json), cls=DjangoJSONEncoder, indent=6)

            # with open("/data/data.json", "w") as json_file:
            #    json.dump(list(for_json), json_file, cls=DjangoJSONEncoder, indent=6)

        return qs_total

    def get_context_data(self, **kwargs):

        # Call the base implementation first to get a context
        context = super().get_context_data(**kwargs)

        if len(self.get_queryset()) > 0:
            scan_report = self.get_queryset()[
                0
            ].source_value.scan_report_field.scan_report_table.scan_report
        else:
            scan_report = None

        context.update(
            {
                "scan_report": scan_report,
            }
        )

        return context


@method_decorator(login_required, name="dispatch")
class DataDictionaryUpdateView(UpdateView):
    model = DataDictionary
    fields = [
        "dictionary_table",
        "dictionary_field",
        "dictionary_field_description",
        "dictionary_value",
        "dictionary_value_description",
        "definition_fixed",
    ]

    def get_success_url(self):
        return "{}?search={}".format(
            reverse("data-dictionary"),
            self.object.source_value.scan_report_field.scan_report_table.scan_report.id,
        )


@method_decorator(login_required, name="dispatch")
class DictionarySelectFormView(FormView):

    form_class = DictionarySelectForm
    template_name = "mapping/mergedictionary.html"
    success_url = reverse_lazy("data-dictionary")

    def form_valid(self, form):

        # Adapt logic in services.py to merge data dictionary file into DataDictionary model
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class DocumentFileStatusUpdateView(UpdateView):
    model = DocumentFile
    # success_url=reverse_lazy('file-list')
    fields = ["status"]

    def get_success_url(self, **kwargs):
        return reverse("file-list", kwargs={"pk": self.object.document_id})


class SignUpView(generic.CreateView):
    form_class = UserCreateForm
    success_url = reverse_lazy("login")
    template_name = "registration/signup.html"


@method_decorator(login_required, name="dispatch")
class CCPasswordChangeView(FormView):
    form_class = PasswordChangeForm
    success_url = reverse_lazy("password_change_done")
    template_name = "registration/password_change_form.html"

    @method_decorator(sensitive_post_parameters())
    @method_decorator(csrf_protect)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class CCPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = "registration/password_change_done.html"

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


def password_reset_request(request):
    if request.method == "POST":
        password_reset_form = PasswordResetForm(request.POST)
        if password_reset_form.is_valid():
            data = password_reset_form.cleaned_data["email"]
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    subject = "Password Reset Requested"
                    email_template_name = "/registration/password_reset_email.txt"
                    c = {
                        "email": user.email,
                        "domain": "0.0.0.0:8000",
                        "site_name": "Website",
                        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
                        "user": user,
                        "token": default_token_generator.make_token(user),
                        "protocol": "http",
                    }
                    email = render_to_string(email_template_name, c)
                    try:
                        send_mail(
                            subject,
                            email,
                            "admin@example.com",
                            [user.email],
                            fail_silently=False,
                        )
                    except BadHeaderError:
                        return HttpResponse("Invalid header found.")
                    return redirect("/password_reset_done/")
    password_reset_form = PasswordResetForm()
    return render(
        request=request,
        template_name="/registration/password_reset.html",
        context={"password_reset_form": password_reset_form},
    )


def load_omop_fields(request):
    omop_table_id = request.GET.get("omop_table")
    omop_fields = OmopField.objects.filter(table_id=omop_table_id).order_by("field")
    return render(
        request,
        "mapping/omop_table_dropdown_list_options.html",
        {"omop_fields": omop_fields},
    )


def testusagi(request, scan_report_id):

    results = run_usagi(scan_report_id)
    print(results)
    context = {}

    return render(request, "mapping/index.html", context)


def merge_dictionary(request):

    # Grab the scan report ID
    search_term = request.GET.get("search", None)
    
    # This function is called from services_datadictionary.py
    merge_external_dictionary(request,scan_report_pk=search_term)

    return render(request, "mapping/mergedictionary.html")


@method_decorator(login_required, name="dispatch")
class NLPListView(ListView):
    model = NLPModel


@method_decorator(login_required, name="dispatch")
class NLPFormView(FormView):
    form_class = NLPForm
    template_name = "mapping/nlpmodel_form.html"
    success_url = reverse_lazy("nlp")

    def form_valid(self, form):

        # Create NLP model object on form submission
        # Very simple, just saves the user's string and a 
        # raw str() of the JSON returned from the NLP service
        NLPModel.objects.create(
            user_string=form.cleaned_data["user_string"],
            json_response="holding",
        )

        # Grab the newly-created model object to get the PK
        # Pass PK to Celery task which handles running the NLP code
        pk = NLPModel.objects.latest("id")
        nlp_single_string_task.delay(
            pk=pk.id, dict_string=form.cleaned_data["user_string"]
        )

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class NLPDetailView(DetailView):
    model = NLPModel
    template_name = "mapping/nlpmodel_detail.html"

    def get_context_data(self, **kwargs):
        query = NLPModel.objects.get(pk=self.kwargs.get("pk"))

        # Small check to return something sensible if NLP hasn't finished running
        if query.json_response == "holding":
            context = {"user_string": query.user_string, "results": "Waiting"}
            return context
        
        else:
            # Run method from services_nlp.py
            json_response = get_json_from_nlpmodel(json=ast.literal_eval(query.json_response))
            context = {"user_string": query.user_string, "results": json_response}
            return context

def run_nlp(request):

    search_term = request.GET.get("search", None)
    field = ScanReportField.objects.get(pk=search_term)
    start_nlp(search_term=search_term)
    
    return redirect("/values/?search={}".format(field.id))


@method_decorator(login_required, name="dispatch")
class NLPResultsListView(ListView):
    model = ScanReportConcept
    

def save_scan_report_value_concept(request):
    if request.method == "POST":
        form = ScanReportValueConceptForm(request.POST)
        if form.is_valid():

            scan_report_value = ScanReportValue.objects.get(
                pk=form.cleaned_data['scan_report_value_id']
            )

            try:
                concept = Concept.objects.get(
                    concept_id=form.cleaned_data['concept_id']
                )
            except Concept.DoesNotExist:
                messages.error(request,
                                 "Concept id {} does not exist in our database.".format(form.cleaned_data['concept_id']))
                return redirect("/values/?search={}".format(scan_report_value.scan_report_field.id))

            scan_report_concept = ScanReportConcept.objects.create(
                concept=concept,
                content_object=scan_report_value,
            )

            messages.success(request, "Concept {} - {} added successfully.".format(concept.concept_id, concept.concept_name))

            return redirect("/values/?search={}".format(scan_report_value.scan_report_field.id))


def delete_scan_report_value_concept(request):
    scan_report_field_id = request.GET.get('scan_report_field_id')
    scan_report_concept_id = request.GET.get('scan_report_concept_id')

    scan_report_concept = ScanReportConcept.objects.get(pk=scan_report_concept_id)

    concept_id = scan_report_concept.concept.concept_id
    concept_name = scan_report_concept.concept.concept_name

    scan_report_concept.delete()

    messages.success(request, "Concept {} - {} removed successfully.".format(concept_id, concept_name))

    return redirect("/values/?search={}".format(scan_report_field_id))


def save_scan_report_field_concept(request):
    if request.method == "POST":
        form = ScanReportFieldConceptForm(request.POST)
        if form.is_valid():
            
            scan_report_field = ScanReportField.objects.get(
                pk=form.cleaned_data['scan_report_field_id']
            )

            try:
                source_concept = Concept.objects.get(
                    concept_id=form.cleaned_data['concept_id']
                )
            except Concept.DoesNotExist:
                messages.error(request,
                                 "Concept id {} does not exist in our database.".format(form.cleaned_data['concept_id']))
                return redirect("/fields/?search={}".format(scan_report_field.scan_report_table.id))


            if source_concept.standard_concept != 'S':
                #look up the concept based on the source_concept
                #this will lookup in concept_relationship
                #and return a new concept (associated standard concept)
                concept = find_standard_concept(source_concept)
                #if we dont allow non-standard concepts
                if m_force_standard_concept:
                    #return an error if it's Non-Standard
                    #dont allowed the ScanReportConcept to be created
                    messages.error(request,
                                   "Concept {} ({}) is Non-Standard".format(source_concept.concept_id,
                                   source_concept.concept_name))
                    messages.error(request,
                                   "You could try {} ({}) ?".format(concept.concept_id,
                                   concept.concept_name))

                    return redirect("/values/?search={}".format(scan_report_value.scan_report_field.id))
            else:
                #otherwise, if this is a standard concept (source_concept.standard_concept=='S')
                #we are good and set concept == source_concept
                concept = source_concept
            
            scan_report_concept = ScanReportConcept.objects.create(
                concept=concept,
                content_object=scan_report_field,
            )

            if concept == source_concept:
                messages.success(request, "Concept {} - {} added successfully.".format(concept.concept_id, concept.concept_name))
            else:
                messages.warning(request,"Non-Standard Concept ID found")
                messages.success(request, "Source Concept {} - {} will be used as source_concept_id.".format(source_concept.concept_id, source_concept.concept_name))
                messages.success(request, "Concept {} - {} will be used as the concept_id".format(concept.concept_id, concept.concept_name))


            
            return redirect("/fields/?search={}".format(scan_report_field.scan_report_table.id))


def delete_scan_report_field_concept(request):
    
    scan_report_table_id=request.GET.get('scan_report_table_id')
    scan_report_concept_id = request.GET.get('scan_report_concept_id')

    scan_report_concept = ScanReportConcept.objects.get(pk=scan_report_concept_id)

    concept_id = scan_report_concept.concept.concept_id
    concept_name = scan_report_concept.concept.concept_name

    scan_report_concept.delete()

    messages.success(request, "Concept {} - {} removed successfully.".format(concept_id, concept_name))

    return redirect("/fields/?search={}".format(scan_report_table_id))
