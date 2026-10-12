from django.urls import include, path

urlpatterns = [
    path("api/", include("routing.urls")),
]

# The frontend always expects JSON, including for errors. Django only uses
# these handlers when DEBUG is off; in debug it shows its own pages.
handler404 = "routing.views.not_found"
handler500 = "routing.views.server_error"
