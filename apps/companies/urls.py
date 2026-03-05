from django.urls import path

from . import views

app_name = "companies"

urlpatterns = [
    path("register/", views.register_company, name="register"),
    path("settings/", views.company_settings, name="settings"),
    path("members/", views.members_list, name="members"),
    path("members/invite/", views.invite_member, name="invite"),
    path("invite/<uuid:token>/", views.accept_invite, name="accept-invite"),
    path("invite/<uuid:token>/revoke/", views.revoke_invite, name="revoke-invite"),
]
