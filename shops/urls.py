from django.urls import path
from . import views

app_name = 'shops'

urlpatterns = [
    path('', views.customer_menu_view, name='customer_menu'),
    path('dashboard/', views.owner_dashboard_view, name='owner_dashboard'),
    path('dish/<int:dish_id>/toggle-available/', views.toggle_dish_availability_view, name='toggle_dish_availability'),
    path('dish/<int:dish_id>/edit/', views.edit_dish_view, name='edit_dish'),
    path('dish/<int:dish_id>/delete/', views.delete_dish_view, name='delete_dish'),
]