from django.contrib.auth.views import PasswordResetView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django import forms

class CustomPasswordResetView(PasswordResetView):
    """
    Custom view for handling password reset requests.
    This view extends the built-in PasswordResetView to provide
    a custom response format and handle form validation.
    """
    template_name: str = 'authn/password_reset_form.html'
    email_template_name: str = 'authn/password_reset_email.html'
    subject_template_name: str = 'authn/password_reset_subject.txt'
    success_url: str = reverse_lazy('password_reset_done')

    def form_valid(self, form: forms.Form) -> JsonResponse:
        """Handle valid form submission."""
        super().form_valid(form)
        return JsonResponse({'message': 'Password reset email sent successfully.'}, status=200)

    def form_invalid(self, form: forms.Form) -> JsonResponse:
        """Handle invalid form submission."""
        return JsonResponse({'errors': form.errors}, status=400)