from django.urls import path

from . import views

urlpatterns = [
    path("health", views.health, name="health"),
    path("route", views.route, name="route"),
    path("algorithms", views.algorithms, name="algorithms"),
    path("geocode", views.geocode_view, name="geocode"),
]
