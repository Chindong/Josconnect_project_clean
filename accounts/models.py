from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        SHOP_OWNER = 'SHOP_OWNER', 'Shop Owner'
        RIDER = 'RIDER', 'Dispatch Rider'
        MODERATOR = 'MODERATOR', 'Moderator'
        ADMIN = 'ADMIN', 'Admin'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending In-Person Validation'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    class ManagedSection(models.TextChoices):
        ALL = 'ALL', 'All Users'
        CUSTOMERS = 'CUSTOMERS', 'Customers'
        SHOP_OWNERS = 'SHOP_OWNERS', 'Shop Owners'
        RIDERS = 'RIDERS', 'Dispatch Riders'
        STAFF = 'STAFF', 'Staff Accounts'

    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=25)
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    approval_status = models.CharField(
        max_length=25,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
    )
    managed_user_section = models.CharField(
        max_length=20,
        choices=ManagedSection.choices,
        default=ManagedSection.ALL,
        blank=True,
    )

    # Live photo captured during registration for ALL users
    live_photo = models.ImageField(upload_to='verification/live_photos/', blank=True, null=True)

    # ID submission for Shop Owners & Dispatch Riders prior to in-person call/validation
    id_reference = models.CharField(max_length=100, blank=True)
    id_document = models.FileField(upload_to='verification/id_documents/', blank=True, null=True)
    in_person_verified_at = models.DateTimeField(null=True, blank=True)

    @property
    def has_management_access(self):
        return bool(
            self.is_superuser
            or self.role in [self.Role.ADMIN, self.Role.MODERATOR]
            or self.is_staff
        )

    @property
    def is_project_owner(self):
        return bool(self.is_superuser or self.role == self.Role.ADMIN)

    @property
    def requires_in_person_verification(self):
        return self.role in [self.Role.SHOP_OWNER, self.Role.RIDER]

    @property
    def is_verified_for_operations(self):
        if not self.requires_in_person_verification:
            return True
        return self.approval_status == self.ApprovalStatus.APPROVED