# file genrepo/accounts/urls.py
# 
#   Copyright 2011 Emory University Libraries
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from django.conf.urls.defaults import patterns, url
from django.core.urlresolvers import reverse

from eulfedora.views import login_and_store_credentials_in_session

urlpatterns = patterns('',
    url(r'^login/$', 'eulfedora.views.login_and_store_credentials_in_session',
        {'template_name': 'accounts/login.html'}, name='login'),
    url(r'^logout/$', 'django.contrib.auth.views.logout',
        {'next_page': reverse('site-index')}, name='logout'),
)

