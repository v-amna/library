from datetime import timedelta
from django import forms
from django.forms import ModelForm
from django.utils import timezone

from config import settings
from .models import Profile, Borrow


class BorrowForm(ModelForm):
    class Meta:
        model = Borrow
        fields = "__all__"
        widgets = {
            'status': forms.RadioSelect,
            'notes': forms.Textarea(attrs={'rows': 3})
        }

    def __init__(self, *args, **kwargs):
        instance = kwargs.get('instance')
        # TODO: Add default value for return date
        initial = {}

        # If borrow is open status add, issue_from and return_date
        # for ease of use
        if instance and instance.status == Borrow.Status.open:
            initial = {
                'issued_from': timezone.now(),
                'return_date': timezone.now() + timedelta(days=settings.DEFAULT_BOOK_BORROW_DURATION)
            }

        super().__init__(*args, **kwargs, initial=initial)


class CustomSignupForm(forms.Form):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    address = forms.CharField(required=False, max_length=255)
    phone_number = forms.CharField(required=False, max_length=20)

    def signup(self, request, user):
        # user = super().save(request)
        Profile.objects.update_or_create(
            user=user,
            defaults={
                "date_of_birth": self.cleaned_data.get("date_of_birth"),
                "address": self.cleaned_data.get("address", ""),
                "phone_number": self.cleaned_data.get("phone_number", ""),
            },
        )
        return user
