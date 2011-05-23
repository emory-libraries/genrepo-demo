# file genrepo/collection/views.py
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

from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from django.template import RequestContext

from eulfedora.server import Repository
from eulfedora.models import DigitalObjectSaveFailure
from eulcommon.djangoextras.auth.decorators import permission_required_with_403
from eulcommon.djangoextras.http import HttpResponseSeeOtherRedirect
from eulfedora.util import RequestFailed, PermissionDenied

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject
from genrepo.util import accessible

@permission_required_with_403('collection.add_collection')
def create_collection(request):
    '''Create a new :class:`~genrepo.collection.models.CollectionObject`.
    
    On GET, displays the form. On POST, creates a collection if the
    form is valid.
    '''
    return _create_or_edit_collection(request)

@permission_required_with_403('collection.change_collection')
def edit_collection(request, pid):
    '''Edit an existing
    :class:`~genrepo.collection.models.CollectionObject` identified by
    pid.

    On GET, displays the edit form.  On POST, updates the collection
    if the form is valid.
    '''
    return _create_or_edit_collection(request, pid)

def _create_or_edit_collection(request, pid=None):
    """View to create a new
    :class:`~genrepo.collection.models.CollectionObject` or update an
    existing one.

    On GET, display the form.  When valid form data is POSTed, creates
    a new collection (if pid is None) or updates an existing
    collection.
    """
    # status code will be 200 unless something goes wrong
    status_code = 200
    repo = Repository(request=request)
    # get the object (if pid is not None), or create a new instance
    obj = repo.get_object(pid, type=CollectionObject)
   
    # on GET, instantiate the form with existing object data (if any)
    if request.method == 'GET':
        form = CollectionDCEditForm(instance=obj.dc.content)

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        form = CollectionDCEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            try:
                if obj.exists:
                    action = 'updated'
                    save_msg = 'updated via genrepo'
                else:
                    action = 'created new'
                    save_msg = 'ingested via genrepo'

                # save message must be specified in order for Fedora
                # to generate & store an ingest audit trail event
                result = obj.save(save_msg)
                messages.success(request,
            		'Successfully %s collection <a href="%s"><b>%s</b></a>' % \
                         (action, reverse('collection:edit', args=[obj.pid]), obj.pid))

		# maybe redirect to collection view page when we have one
                # - and maybe return a 201 Created status code
                return HttpResponseSeeOtherRedirect(reverse('site-index'))
            except (DigitalObjectSaveFailure, RequestFailed) as rf:
                # do we need a different error message for DigitalObjectSaveFailure?
                if isinstance(rf, PermissionDenied):
                    msg = 'You don\'t have permission to create a collection in the repository.'
                else:
                    msg = 'There was an error communicating with the repository.'
                messages.error(request,
                               msg + ' Please contact a site administrator.')

                # pass the fedora error code (if any) back in the http response
                if hasattr(rf, 'code'):
                    status_code = getattr(rf, 'code')

    # if form is not valid, fall through and re-render the form with errors
    return render(request, 'collection/edit.html', {'form': form, 'obj': obj},
                  status=status_code)

def view_collection(request, pid):
    '''view an existing
    :class:`~genrepo.collection.models.CollectionObject` identified by
    pid.
    '''
    repo = Repository(request=request)
    obj = repo.get_object(pid, type=CollectionObject)
    # if the object does not exist or the current user doesn't have
    # permission to see that it exists, 404
    if not obj.exists:
        raise Http404
    return render(request, 'collection/view.html', {'obj': obj})

def list_collections(request):
    '''list all collections in repository returns list of
    :class:`~genrepo.collection.models.CollectionObject`
    '''
    colls = CollectionObject.all()
    colls = list(accessible(colls))
    colls.sort(key=lambda coll: coll.label.upper()) # sort based on label

    return render(request, 'collection/list.html', {'colls': colls})
