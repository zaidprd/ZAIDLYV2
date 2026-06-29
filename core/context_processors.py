"""Global context processors — kept minimal."""
APP_VERSION = "0.1.0"


def app_meta(request):
    return {'APP_VERSION': APP_VERSION}
