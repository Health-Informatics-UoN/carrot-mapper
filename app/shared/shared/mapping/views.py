import datetime
import json
import os
import random
import string

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordChangeDoneView
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import BadHeaderError, send_mail
from django.db.models.query_utils import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.debug import sensitive_post_parameters
from django.views.generic import ListView
from django.views.generic.edit import FormView, UpdateView
from shared.mapping.models import (
    DataDictionary,
    Dataset,
    MappingRule,
    ScanReport,
    ScanReportAssertion,
    ScanReportField,
    ScanReportTable,
)
from shared.services.azurequeue import add_message
from shared.services.rules_export import (
    get_mapping_rules_as_csv,
    get_mapping_rules_json,
    make_dag,
)

from .forms import ScanReportAssertionForm, ScanReportForm
from .permissions import has_editorship, has_viewership, is_admin


from shared_code import storage_router

storage_parser = storage_router.StorageService()


@login_required
def home(request):
    return render(request, "mapping/home.html", {})


@login_required
def update_scanreport_table_page(request, sr, pk):
    try:
        sr_table = ScanReportTable.objects.get(id=pk)
        can_edit = bool(
            (
                sr_table.scan_report.author.id == request.user.id
                or sr_table.scan_report.editors.filter(id=request.user.id).exists()
                or sr_table.scan_report.parent_dataset.editors.filter(
                    id=request.user.id
                ).exists()
                or sr_table.scan_report.parent_dataset.admins.filter(
                    id=request.user.id
                ).exists()
            )
        )
        # Set the page context
        context = {"can_edit": can_edit, "pk": pk}
        if (
            has_viewership(sr_table, request)
            or has_editorship(sr_table, request)
            or is_admin(sr_table, request)
        ):
            return render(request, "mapping/scanreporttable_form.html", context=context)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@method_decorator(login_required, name="dispatch")
class ScanReportListView(ListView):
    model = ScanReport

    def get_queryset(self):
        # No data is passed to the view, it is all API fetched.
        return ScanReport.objects.none()


@method_decorator(login_required, name="dispatch")
class StructuralMappingTableListView(ListView):
    model = MappingRule
    template_name = "mapping/mappingrulesscanreport_list.html"

    def post(self, request, *args, **kwargs):
        try:
            body = json.loads(request.body.decode("utf-8"))
        except ValueError:
            body = {}
        if (
            request.POST.get("download_rules") is not None
            or body.get("download_rules") is not None
        ):
            return self._download_json()
        elif (
            request.POST.get("download_rules_as_csv") is not None
            or body.get("download_rules_as_csv") is not None
        ):
            return self._download_csv()
        elif request.POST.get("get_svg") is not None or body.get("get_svg") is not None:
            qs = self.get_queryset()
            output = get_mapping_rules_json(qs)

            # use make dag svg image
            svg = make_dag(output["cdm"])
            return HttpResponse(svg, content_type="image/svg+xml")
        else:
            messages.error(request, "not working right now!")
            return redirect(request.path)

    def _download_csv(self):
        qs = self.get_queryset()
        scan_report = qs[0].scan_report
        return_type = "csv"
        fname = f"{scan_report.parent_dataset.data_partner.name}_{scan_report.dataset}_structural_mapping.{return_type}"
        _buffer = get_mapping_rules_as_csv(qs)

        response = HttpResponse(_buffer, content_type="text/csv")
        response["Content-Disposition"] = f'attachment; filename="{fname}"'
        return response

    def _download_json(self):
        qs = self.get_queryset()
        output = get_mapping_rules_json(qs)
        scan_report = qs[0].scan_report
        return_type = "json"
        fname = f"{scan_report.parent_dataset.data_partner.name}_{scan_report.dataset}_structural_mapping.{return_type}"

        response = HttpResponse(
            json.dumps(output, indent=6), content_type="application/json"
        )
        response["Content-Disposition"] = f'attachment; filename="{fname}"'
        return response

    def get_queryset(self):
        qs = super().get_queryset()
        search_term = self.kwargs.get("pk")

        if search_term is not None:
            qs = qs.filter(scan_report__id=search_term).order_by(
                "concept",
                "omop_field__table",
                "omop_field__field",
                "source_table__name",
                "source_field__name",
            )

        return qs


def modify_filename(filename, dt, rand):
    split_filename = os.path.splitext(str(filename))
    return f"{split_filename[0]}_{dt}_{rand}{split_filename[1]}"


@method_decorator(login_required, name="dispatch")
class ScanReportFormView(FormView):
    form_class = ScanReportForm
    template_name = "mapping/upload_scan_report.html"
    success_url = reverse_lazy("scan-report-list")

    def form_invalid(self, form):
        storage = messages.get_messages(self.request)
        for message in storage:
            response = JsonResponse(
                {
                    "status_code": 422,
                    "form-errors": form.errors,
                    "ok": False,
                    "statusText": str(message),
                }
            )
            response.status_code = 422
            return response
        response = JsonResponse(
            {
                "status_code": 422,
                "form-errors": form.errors,
                "ok": False,
                "statusText": "Could not process input.",
            }
        )
        response.status_code = 422
        return response

    def form_valid(self, form):
        # Check user has admin/editor rights on Scan Report parent dataset
        parent_dataset = form.cleaned_data["parent_dataset"]
        if not (
            has_editorship(parent_dataset, self.request)
            or is_admin(parent_dataset, self.request)
        ):
            messages.warning(
                self.request,
                "You do not have editor or administrator permissions on this Dataset.",
            )
            return self.form_invalid(form)

        # Create random alphanumeric to link scan report to data dictionary
        # Create datetime stamp for scan report and data dictionary upload time
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        dt = "{:%Y%m%d-%H%M%S}".format(datetime.datetime.now())
        print(dt, rand)
        # Create an entry in ScanReport for the uploaded Scan Report
        scan_report = ScanReport.objects.create(
            dataset=form.cleaned_data["dataset"],
            parent_dataset=parent_dataset,
            name=modify_filename(form.cleaned_data.get("scan_report_file"), dt, rand),
            visibility=form.cleaned_data["visibility"],
        )

        scan_report.author = self.request.user
        scan_report.save()

        # Add viewers to the scan report if specified
        if sr_viewers := form.cleaned_data.get("viewers"):
            scan_report.viewers.add(*sr_viewers)

        # Add editors to the scan report if specified
        if sr_editors := form.cleaned_data.get("editors"):
            scan_report.editors.add(*sr_editors)

        print("FILE >>> ", str(form.cleaned_data.get("scan_report_file")))
        print("STRING TEST >>>> ", scan_report.name)

        # Spreadsheet_content_type
        spreadsheet_content_type = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        # If there's no data dictionary supplied, only upload the scan report
        # Set data_dictionary_blob in Azure message to None
        if form.cleaned_data.get("data_dictionary_file") is None:
            azure_dict = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": "None",
            }

            storage_parser.upload_blob(
                blob_name=scan_report.name,
                container="scan-reports",
                file=form.cleaned_data.get("scan_report_file"),
                content_type=spreadsheet_content_type,
                use_read_method=False,
            )
            # setting content settings for downloading later
        # Else upload the scan report and the data dictionary
        else:
            data_dictionary = DataDictionary.objects.create(
                name=f"{os.path.splitext(str(form.cleaned_data.get('data_dictionary_file')))[0]}"
                f"_{dt}{rand}.csv"
            )
            data_dictionary.save()
            scan_report.data_dictionary = data_dictionary
            scan_report.save()

            azure_dict = {
                "scan_report_id": scan_report.id,
                "scan_report_blob": scan_report.name,
                "data_dictionary_blob": data_dictionary.name,
            }

            storage_parser.upload_form_from_data_dictionary_to_containers(
                form_1=form.cleaned_data.get("scan_report_file").open(),
                form_2=form.cleaned_data.get("data_dictionary_file").open(),
                container_1="scan-reports",
                container_2="data-dictionaries",
                blob_1=scan_report.name,
                blob_2=data_dictionary.name,
            )

        # send to the upload queue
        add_message(os.environ.get("WORKERS_UPLOAD_NAME"), azure_dict)

        return super().form_valid(form)


@method_decorator(login_required, name="dispatch")
class ScanReportAssertionView(ListView):
    model = ScanReportAssertion

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        x = ScanReport.objects.get(pk=self.kwargs.get("pk"))
        context.update({"scan_report": x})
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


@login_required
def dataset_list_page(request):
    return render(request, "mapping/dataset_list.html")


@login_required
def dataset_admin_page(request, pk):
    args = {}
    try:
        ds = Dataset.objects.get(id=pk)
        args["is_admin"] = ds.admins.filter(id=request.user.id).exists()

        if (
            has_viewership(ds, request)
            or has_editorship(ds, request)
            or is_admin(ds, request)
        ):
            return render(request, "mapping/admin_dataset_form.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def dataset_content_page(request, pk):
    args = {}
    try:
        ds = Dataset.objects.get(id=pk)
        args["is_admin"] = ds.admins.filter(id=request.user.id).exists()

        if (
            has_viewership(ds, request)
            or has_editorship(ds, request)
            or is_admin(ds, request)
        ):
            return render(request, "mapping/datasets_content.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def scanreport_admin_page(request, pk):
    args = {}
    try:
        sr = ScanReport.objects.get(id=pk)
        _is_admin = (
            sr.author.id == request.user.id
            or sr.parent_dataset.admins.filter(id=request.user.id).exists()
        )
        args["is_admin"] = _is_admin

        if (
            has_viewership(sr, request)
            or has_editorship(sr, request)
            or is_admin(sr, request)
        ):
            return render(request, "mapping/admin_scanreport_form.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def scanreport_table_list_page(request, pk):
    args = {}

    try:
        scan_report = ScanReport.objects.get(id=pk)

        args["can_edit"] = has_editorship(scan_report, request) or is_admin(
            scan_report, request
        )

        if (
            has_viewership(scan_report, request)
            or has_editorship(scan_report, request)
            or is_admin(scan_report, request)
        ):
            return render(request, "mapping/scanreporttable_list.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def scanreport_fields_list_page(request, sr, pk):
    args = {}
    try:
        scan_report_table = ScanReportTable.objects.select_related("scan_report").get(
            id=pk, scan_report__id=sr
        )

        args["pk"] = pk
        args["can_edit"] = has_editorship(scan_report_table, request) or is_admin(
            scan_report_table, request
        )
        if (
            has_viewership(scan_report_table, request)
            or has_editorship(scan_report_table, request)
            or is_admin(scan_report_table, request)
        ):
            return render(request, "mapping/scanreportfield_list.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def scanreport_values_list_page(request, sr, tbl, pk):
    args = {}

    try:
        scan_report_field = ScanReportField.objects.select_related(
            "scan_report_table", "scan_report_table__scan_report"
        ).get(id=pk, scan_report_table=tbl, scan_report_table__scan_report=sr)

        args["pk"] = pk
        args["can_edit"] = has_editorship(scan_report_field, request) or is_admin(
            scan_report_field, request
        )

        if (
            has_viewership(scan_report_field, request)
            or has_editorship(scan_report_field, request)
            or is_admin(scan_report_field, request)
        ):
            return render(request, "mapping/scanreportvalue_list.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")


@login_required
def update_scanreport_field_page(request, sr, tbl, pk):
    args = {"pk": pk}
    try:
        scan_report_field = ScanReportField.objects.select_related(
            "scan_report_table", "scan_report_table__scan_report"
        ).get(id=pk, scan_report_table=tbl, scan_report_table__scan_report=sr)

        args["can_edit"] = has_editorship(scan_report_field, request) or is_admin(
            scan_report_field, request
        )

        if (
            has_viewership(scan_report_field, request)
            or has_editorship(scan_report_field, request)
            or is_admin(scan_report_field, request)
        ):
            return render(request, "mapping/scanreportfield_form.html", args)
        else:
            return render(request, "mapping/error_404.html")
    except ObjectDoesNotExist:
        return render(request, "mapping/error_404.html")
