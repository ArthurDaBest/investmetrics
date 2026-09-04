from django import forms


class LearnerLoginForm(forms.Form):
    identifier = forms.CharField(
        label="Email or username",
        max_length=254,
        widget=forms.TextInput(attrs={
            "autocomplete": "username",
            "placeholder": "Email or username",
        }),
    )
    password = forms.CharField(
        label="Password",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "autocomplete": "current-password",
            "placeholder": "Password",
        }),
    )
