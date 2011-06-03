# file genrepo/urls.py
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

from django.conf import settings
from django.conf.urls.defaults import *
from django.contrib import admin

# auto discover models that should be available for db admin
admin.autodiscover()

urlpatterns = patterns('',
    # Example:
    # (r'^genrepo/', include('genrepo.foo.urls')),
    # site index
    url(r'^$', 'genrepo.accounts.views.index', name="site-index"),

    # login/logout
    url(r'^accounts/', include('genrepo.accounts.urls', namespace='accounts')),
    # collections
    url(r'^collections/', include('genrepo.collection.urls', namespace='collection')),
    # files
    url(r'^files/', include('genrepo.file.urls', namespace='file')),

    # enable django db-admin
    (r'^db-admin/', include(admin.site.urls)),
)


# serve out media in django runserver for development
# DISABLE THIS IN PRODUCTION
if settings.DEV_ENV:
    urlpatterns += patterns('',
        (r'^static/(?P<path>.*)$', 'django.views.static.serve', {
            'document_root': settings.MEDIA_ROOT,
            }),
    )

