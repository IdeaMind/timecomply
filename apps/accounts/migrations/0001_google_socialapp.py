"""
Data migration: create the Google OAuth2 SocialApp from environment variables.

GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set in the environment for
Railway deploys (and locally via .env). If they are missing the app entry is
still created so the site does not crash; the Google login button simply will
not work until credentials are configured.
"""

import os

from django.db import migrations


def create_google_app(apps, schema_editor):
    SocialApp = apps.get_model("socialaccount", "SocialApp")
    Site = apps.get_model("sites", "Site")

    site = Site.objects.get_or_create(
        id=1, defaults={"domain": "example.com", "name": "TimeComply"}
    )[0]

    # Avoid creating duplicates on repeated runs (e.g. test teardown/setup).
    app, created = SocialApp.objects.get_or_create(
        provider="google",
        defaults={
            "name": "Google",
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        },
    )
    if not created:
        # Update credentials if they have changed.
        app.client_id = os.environ.get("GOOGLE_CLIENT_ID", app.client_id)
        app.secret = os.environ.get("GOOGLE_CLIENT_SECRET", app.secret)
        app.save()

    app.sites.add(site)


def remove_google_app(apps, schema_editor):
    SocialApp = apps.get_model("socialaccount", "SocialApp")
    SocialApp.objects.filter(provider="google", name="Google").delete()


class Migration(migrations.Migration):
    dependencies = [
        ("socialaccount", "0006_alter_socialaccount_extra_data"),
        ("sites", "0002_alter_domain_unique"),
    ]

    operations = [
        migrations.RunPython(create_google_app, remove_google_app),
    ]
