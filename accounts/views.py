from django.contrib import messages
from django.contrib.auth import login, logout, views as auth_views
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from shops.models import Shop
from .forms import JosConnectRegistrationForm
from .models import User

ROLE_SLUG_MAP = {
    'customer': User.Role.CUSTOMER,
    'shop': User.Role.SHOP_OWNER,
    'shop_owner': User.Role.SHOP_OWNER,
    'rider': User.Role.RIDER,
    'dispatch_rider': User.Role.RIDER,
}


def signup_choice_view(request):
    return render(request, 'accounts/signup_choice.html')


def role_signup_view(request, role):
    normalized = ROLE_SLUG_MAP.get((role or '').strip().lower())
    if not normalized:
        return redirect('accounts:signup_choice')
    query = f"?role={normalized.lower()}"
    return redirect(f"{reverse('accounts:register')}{query}")


def register_view(request):
    raw_role = request.GET.get('role', '').strip().lower()
    selected_role = ROLE_SLUG_MAP.get(raw_role) or raw_role.upper()
    initial = {}
    if selected_role in [User.Role.CUSTOMER, User.Role.SHOP_OWNER, User.Role.RIDER]:
        initial['role'] = selected_role

    if request.method == 'POST':
        form = JosConnectRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            if user.role == User.Role.SHOP_OWNER:
                Shop.objects.get_or_create(
                    owner=user,
                    defaults={
                        'name': (form.cleaned_data.get('shop_name') or '').strip(),
                        'address': (form.cleaned_data.get('shop_address') or '').strip(),
                    },
                )
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')

            if user.requires_in_person_verification:
                messages.info(
                    request,
                    'Registration and ID submitted! Our staff will call your submitted phone number '
                    'for in-person validation before approving your account.',
                )
            else:
                messages.success(request, 'Account created with live photo verification!')

            return redirect('accounts:role_redirect')
    else:
        form = JosConnectRegistrationForm(initial=initial)

    return render(request, 'accounts/register.html', {'form': form, 'selected_role': initial.get('role', '')})


@login_required
def role_redirect_view(request):
    user = request.user
    role = getattr(user, 'role', None)

    if getattr(user, 'is_superuser', False) or role in [User.Role.ADMIN, User.Role.MODERATOR] or getattr(user, 'is_staff', False):
        return redirect('orders:admin_dashboard')
    if role == User.Role.SHOP_OWNER:
        return redirect('shops:owner_dashboard')
    if role == User.Role.RIDER:
        return redirect('orders:rider_dashboard')
    return redirect('shops:customer_menu')


@login_required
def account_profile_view(request):
    return render(request, 'accounts/account_profile.html', {
        'profile_user': request.user,
    })


class JosConnectPasswordResetView(auth_views.PasswordResetView):
    template_name = 'accounts/password_reset_form.html'
    email_template_name = 'accounts/password_reset_email.html'
    subject_template_name = 'accounts/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class JosConnectPasswordResetDoneView(auth_views.PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class JosConnectPasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class JosConnectPasswordResetCompleteView(auth_views.PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'


class JosConnectPasswordChangeView(auth_views.PasswordChangeView):
    template_name = 'accounts/password_change_form.html'
    success_url = reverse_lazy('accounts:account_profile')

    def form_valid(self, form):
        messages.success(self.request, 'Your password has been updated.')
        return super().form_valid(form)

def logout_view(request):
    logout(request)
    return redirect('accounts:login')