from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from .models import User


class RoleSignupForm(UserCreationForm):
    phone_number = forms.CharField(max_length=20, required=True)
    shop_name = forms.CharField(max_length=120, required=False)
    shop_address = forms.CharField(max_length=255, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def __init__(self, *args, role=None, **kwargs):
        self.role = role
        super().__init__(*args, **kwargs)
        if role != User.Role.SHOP_OWNER:
            self.fields.pop('shop_name', None)
            self.fields.pop('shop_address', None)
        else:
            self.fields['shop_name'].required = True
            self.fields['shop_address'].required = True

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = self.role
        if self.role in [User.Role.SHOP_OWNER, User.Role.RIDER]:
            user.approval_status = User.ApprovalStatus.PENDING
        if commit:
            user.save()
        return user


class StaffCreateForm(UserCreationForm):
    phone_number = forms.CharField(max_length=20, required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'phone_number', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.role = User.Role.MODERATOR
        user.approval_status = User.ApprovalStatus.APPROVED
        if commit:
            user.save()
        return user


class RoleLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Password'}))