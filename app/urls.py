from django.conf.urls.static import static
from django.conf import settings
from django.urls import path, include
from django.contrib import admin
from django.views.generic import RedirectView, TemplateView

import config

admin.site.site_title = f"{config.PROJECT_NAME} Admin"
admin.site.site_header = f"{config.PROJECT_NAME} Administration"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url='/static/favicon.ico')),
    path('ads.txt', TemplateView.as_view(template_name='ads.txt', content_type='text/plain')),
    path('api/accounts/', include('accounts.urls')),
    path('ipns/', include('finances.urls.payment')),
    path('animate/', include('animator.urls')),
    path('', include('core.urls')),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
