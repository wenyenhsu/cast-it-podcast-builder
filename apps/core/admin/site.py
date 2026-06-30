"""Django Admin site customization."""

from django.contrib import admin


def patch_admin_site(site: admin.AdminSite) -> None:
    """Configure branding for the default Django admin."""
    site.site_header = "Cast It Administration"
    site.site_title = "Cast It Admin"
    site.index_title = "Site administration"
