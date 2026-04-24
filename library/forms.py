
from django import forms
from .models import Profile


class CustomSignupForm(forms.Form):
    date_of_birth = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={"type": "date"})
    )
    address = forms.CharField(required=False, max_length=255)
    phone_number = forms.CharField(required=False, max_length=20)

    def signup(self, request,user):
        #user = super().save(request)
        Profile.objects.update_or_create(
            user=user,
            defaults={
                "date_of_birth": self.cleaned_data.get("date_of_birth"),
                "address": self.cleaned_data.get("address", ""),
                "phone_number": self.cleaned_data.get("phone_number", ""),
            },
        )
        return user