from django.conf.urls.defaults import patterns, url


urlpatterns = patterns('genrepo.collection.views',
    url(r'^new/$', 'create', name='new'),
)
