from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        CUSTOMER = 'CUSTOMER', 'Customer'
        SHOP_OWNER = 'SHOP_OWNER', 'Shop Owner'
        RIDER = 'RIDER', 'Dispatch Rider'
        MODERATOR = 'MODERATOR', 'Operations Staff'
        ADMIN = 'ADMIN', 'Project Owner'

    class ApprovalStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending Approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone_number = models.CharField(max_length=20, blank=True)
    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.APPROVED,
    )

    def save(self, *args, **kwargs):
        if self.is_superuser or self.role in [self.Role.ADMIN, self.Role.MODERATOR, self.Role.CUSTOMER]:
            self.approval_status = self.ApprovalStatus.APPROVED
        elif not self.pk and self.role in [self.Role.SHOP_OWNER, self.Role.RIDER]:
            if not self.approval_status:
                self.approval_status = self.ApprovalStatus.PENDING
        super().save(*args, **kwargs)

    @property
    def is_project_owner(self):
        return self.is_superuser or self.role == self.Role.ADMIN

    @property
    def has_management_access(self):
        return self.is_superuser or self.role in [self.Role.ADMIN, self.Role.MODERATOR]