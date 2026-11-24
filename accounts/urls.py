from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup_choice_view, name='signup_choice'),
    path('signup/<str:role_slug>/', views.role_signup_view, name='role_signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('redirect/', views.role_redirect_view, name='role_redirect'),
]