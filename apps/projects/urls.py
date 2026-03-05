from django.urls import path

from . import views

app_name = "projects"

urlpatterns = [
    path("", views.project_list, name="list"),
    path("create/", views.project_create, name="create"),
    path("<uuid:pk>/edit/", views.project_update, name="update"),
    path("<uuid:pk>/archive/", views.project_archive, name="archive"),
    path("<uuid:pk>/unarchive/", views.project_unarchive, name="unarchive"),
]
