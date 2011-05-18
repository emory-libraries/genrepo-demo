from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse

from eulfedora.views import login_and_store_credentials_in_session

urlpatterns = patterns('',
    url(r'^login/$', 'eulfedora.views.login_and_store_credentials_in_session',
        {'template_name': 'accounts/login.html'}, name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout',
        {'next_page': reverse('site-index')}, name='logout'),
)

