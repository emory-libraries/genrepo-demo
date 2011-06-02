# file genrepo/collection/urls.py
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

from genrepo.collection.models import CollectionObject

urlpatterns = patterns('genrepo.collection.views',
    url(r'^$', 'list_collections', name='list'),
    url(r'^new/$', 'create_collection', name='new'),
    url(r'^(?P<pid>[^/]+)/edit/$', 'edit_collection', name='edit'),
    url(r'^(?P<pid>[^/]+)/$', 'view_collection', name='view'),
)

# use eulfedora view for raw datastream access
urlpatterns += patterns('eulfedora.views',
    url(r'^(?P<pid>[^/]+)/(?P<dsid>(DC|RELS-EXT))/$', 'raw_datastream',
        {'type': CollectionObject}, name='raw-ds'),
)
