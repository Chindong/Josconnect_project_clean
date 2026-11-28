import base64
import uuid
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.files.base import ContentFile
from .models import User


class JosConnectRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=25, required=True)
    role = forms.ChoiceField(
        choices=[
            (User.Role.CUSTOMER, 'Customer'),
            (User.Role.SHOP_OWNER, 'Shop Owner'),
            (User.Role.RIDER, 'Dispatch Rider'),
        ],
        required=True,
    )
    live_photo = forms.ImageField(required=False)
    captured_photo_data = forms.CharField(widget=forms.HiddenInput(), required=False)

    id_reference = forms.CharField(max_length=100, required=False)
    id_document = forms.FileField(required=False)

    # Optional shop fields when registering as SHOP_OWNER
    shop_name = forms.CharField(max_length=150, required=False)
    shop_address = forms.CharField(max_length=255, required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'email',
            'phone_number',
            'role',
            'live_photo',
            'id_reference',
            'id_document',
            'password1',
            'password2',
        )

    def _decode_captured_photo(self, data_url):
        if not data_url or ';base64,' not in data_url:
            return None
        header, b64_data = data_url.split(';base64,', 1)
        ext = 'jpg'
        if 'png' in header:
            ext = 'png'
        elif 'webp' in header:
            ext = 'webp'
        file_bytes = base64.b64decode(b64_data)
        return ContentFile(file_bytes, name=f"live_{uuid.uuid4().hex[:10]}.{ext}")

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        uploaded_photo = cleaned_data.get('live_photo')
        captured_data = cleaned_data.get('captured_photo_data')

        decoded_photo = self._decode_captured_photo(captured_data)
        final_photo = decoded_photo or uploaded_photo

        if not final_photo:
            self.add_error('live_photo', 'Please capture a live photo using your camera or upload a photo.')
        else:
            cleaned_data['resolved_live_photo'] = final_photo

        if role in [User.Role.SHOP_OWNER, User.Role.RIDER]:
            if not (cleaned_data.get('id_reference') or '').strip():
                self.add_error('id_reference', 'Please provide your ID number/reference before submitting.')
            if not cleaned_data.get('id_document'):
                self.add_error('id_document', 'Please upload a valid ID document for staff verification.')

        if role == User.Role.SHOP_OWNER:
            if not (cleaned_data.get('shop_name') or '').strip():
                self.add_error('shop_name', 'Shop name is required for Shop Owners.')
            if not (cleaned_data.get('shop_address') or '').strip():
                self.add_error('shop_address', 'Shop address is required for Shop Owners.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.phone_number = self.cleaned_data['phone_number'].strip()
        user.role = self.cleaned_data['role']
        user.live_photo = self.cleaned_data['resolved_live_photo']
        user.id_reference = (self.cleaned_data.get('id_reference') or '').strip()

        if self.cleaned_data.get('id_document'):
            user.id_document = self.cleaned_data['id_document']

        # Shop owners and riders stay PENDING until staff validates them in person
        if user.role in [User.Role.SHOP_OWNER, User.Role.RIDER]:
            user.approval_status = User.ApprovalStatus.PENDING
        else:
            user.approval_status = User.ApprovalStatus.APPROVED

        if commit:
            user.save()
        return user

class StaffCreateForm(UserCreationForm):
    email = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=25, required=True)
    managed_user_section = forms.ChoiceField(
        choices=[
            (User.ManagedSection.CUSTOMERS, 'Customers'),
            (User.ManagedSection.SHOP_OWNERS, 'Shop Owners'),
            (User.ManagedSection.RIDERS, 'Dispatch Riders'),
            (User.ManagedSection.ALL, 'All Users'),
        ],
        required=True,
        label='Assigned User Section',
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = (
            'username',
            'email',
            'phone_number',
            'managed_user_section',
            'password1',
            'password2',
        )

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].strip().lower()
        user.phone_number = self.cleaned_data['phone_number'].strip()
        user.role = User.Role.MODERATOR
        user.managed_user_section = self.cleaned_data['managed_user_section']
        user.approval_status = User.ApprovalStatus.APPROVED
        user.is_staff = True
        if commit:
            user.save()
        return user