from django.contrib.auth import views as auth_views
from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_choice_view, name='signup_choice'),
    path('signup/<str:role>/', views.role_signup_view, name='role_signup'),
    path('role-redirect/', views.role_redirect_view, name='role_redirect'),
    path('login/', auth_views.LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.account_profile_view, name='account_profile'),

    # Reset password from user dashboard (authenticated)
    path('password/reset-from-dashboard/', views.JosConnectPasswordChangeView.as_view(), name='dashboard_password_reset'),

    # Forgot password flow (login / signup / register pages)
    path('password-reset/', views.JosConnectPasswordResetView.as_view(), name='password_reset'),
    path('password-reset/done/', views.JosConnectPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.JosConnectPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', views.JosConnectPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]