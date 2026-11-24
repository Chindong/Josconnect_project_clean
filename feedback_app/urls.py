from django.urls import path
from . import views

app_name = 'feedback_app'

urlpatterns = [
    path('', views.submit_feedback_view, name='submit_feedback'),
]