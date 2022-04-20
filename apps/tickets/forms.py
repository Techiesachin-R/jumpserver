from django import forms
from django.utils.translation import ugettext_lazy as _


class ApproveCheckPasswordForm(forms.Form):
    username = forms.CharField(
        label=_('Username'), max_length=100,
        widget=forms.TextInput(attrs={
            'placeholder': _("Username"),
            'autofocus': 'autofocus'
        })
    )
    password = forms.CharField(
        label=_('Password'), widget=forms.PasswordInput,
        max_length=1024, strip=False
    )
