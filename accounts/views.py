from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from shops.models import Shop
from .forms import RoleLoginForm, RoleSignupForm
from .models import User

ROLE_MAP = {
    'customer': User.Role.CUSTOMER,
    'shop': User.Role.SHOP_OWNER,
    'rider': User.Role.RIDER,
}


def signup_choice_view(request):
    return render(request, 'accounts/signup_choice.html')


def role_signup_view(request, role_slug):
    role_value = ROLE_MAP.get(role_slug.lower())
    if not role_value:
        messages.error(request, 'Invalid account type selected.')
        return redirect('accounts:signup_choice')

    if request.method == 'POST':
        form = RoleSignupForm(request.POST, role=role_value)
        if form.is_valid():
            user = form.save()
            if role_value == User.Role.SHOP_OWNER:
                Shop.objects.create(
                    owner=user,
                    name=form.cleaned_data['shop_name'],
                    address=form.cleaned_data['shop_address'],
                )
            login(request, user)
            if role_value in [User.Role.SHOP_OWNER, User.Role.RIDER]:
                messages.info(request, 'Registration submitted! Awaiting approval.')
            else:
                messages.success(request, 'Welcome to JosConnect!')
            return redirect('accounts:role_redirect')
    else:
        form = RoleSignupForm(role=role_value)

    return render(request, 'accounts/signup.html', {
        'form': form,
        'role_slug': role_slug.lower(),
        'role_label': User.Role(role_value).label,
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('accounts:role_redirect')
    if request.method == 'POST':
        form = RoleLoginForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('accounts:role_redirect')
    else:
        form = RoleLoginForm(request)
    return render(request, 'accounts/login.html', {'form': form})


@login_required
def logout_view(request):
    logout(request)
    messages.info(request, 'You have signed out.')
    return redirect('accounts:login')


@login_required
def role_redirect_view(request):
    user = request.user
    if user.has_management_access:
        return redirect('orders:admin_dashboard')
    if user.role == User.Role.SHOP_OWNER:
        return redirect('shops:owner_dashboard')
    if user.role == User.Role.RIDER:
        return redirect('orders:rider_dashboard')
    return redirect('shops:customer_menu')