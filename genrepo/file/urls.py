# file genrepo/file/urls.py
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

from django.conf.urls.defaults import *

urlpatterns = patterns('genrepo.file.views',
    url(r'^ingest/$', 'ingest_form', name='ingest'),
    url(r'^(?P<pid>[^/]+)/$', 'view_metadata', name='view'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'edit_metadata', name='edit'),
    url(r'^(?P<pid>[^/]+)/master/$', 'download_file', name='download'),
    url(r'^(?P<pid>[^/]+)/preview/$', 'preview', name='preview'),
    url(r'^(?P<pid>[^/]+)/dzi/$', 'image_dzi', name='dzi'),
    url(r'^(?P<pid>[^/]+)/image-region/$', 'image_region', name='image-region'),
)
