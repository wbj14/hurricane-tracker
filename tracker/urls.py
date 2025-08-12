from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("api/shelters/", views.shelter_list, name="shelter_list"),
    path("api/storms/", views.storms_api, name="storms_api"),
    path("api/storms.geojson", views.storms_geojson, name="storms_geojson"),
    path("api/nhc/current", views.nhc_current, name="nhc_current"),
]
