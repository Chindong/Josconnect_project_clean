from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('add/<int:dish_id>/', views.add_to_cart_view, name='add_to_cart'),
    path('cart/', views.cart_checkout_view, name='cart_checkout'),
    path('my-orders/', views.my_orders_view, name='my_orders'),
    path('rider/', views.rider_dashboard_view, name='rider_dashboard'),
    path('rider/<int:order_id>/<str:action>/', views.rider_update_order_view, name='rider_update_order'),
    path('admin-panel/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin-panel/user/<int:user_id>/<str:decision>/', views.admin_approve_user_view, name='admin_approve_user'),
    path('admin-panel/user/<int:user_id>/delete/', views.admin_delete_user_view, name='admin_delete_user'),
    path('track/<int:order_id>/', views.track_order_view, name='track_order'),
    path('track/<int:order_id>/update-gps/', views.update_rider_location_view, name='update_rider_location'),
    path('track/<int:order_id>/status-json/', views.get_order_location_json_view, name='get_order_location_json'),
    path('admin-panel/active-map-json/', views.active_deliveries_json_view, name='active_deliveries_json'),
]