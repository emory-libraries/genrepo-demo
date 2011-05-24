# file genrepo/file/views.py
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
from django.core.urlresolvers import reverse
from django.http import Http404
from django.shortcuts import render
from rdflib import URIRef

from eulcommon.djangoextras.auth.decorators import permission_required_with_403
from eulcommon.djangoextras.http import HttpResponseSeeOtherRedirect
from eulfedora.models import DigitalObjectSaveFailure
from eulfedora.rdfns import relsext
from eulfedora.server import Repository
from eulfedora.views import raw_datastream
from eulfedora.util import RequestFailed, PermissionDenied

from genrepo.file.forms import IngestForm, DublinCoreEditForm
from genrepo.file.models import FileObject

@permission_required_with_403('file.add_file')
def ingest_form(request):
    """Display or process the file ingest form. On GET, display the form. On
    valid POST, reposit the submitted file in a new digital object.
    """
    if request.method == 'POST':
        form = IngestForm(request.POST, request.FILES)
        if form.is_valid():
            # TODO: set label/dc:title based on filename;
            # set file mimetype in dc:format
            # TODO: file checksum?
            repo = Repository(request=request)
            fobj = repo.get_object(type=FileObject)
            st = (fobj.uriref, relsext.isMemberOfCollection, 
                  URIRef(form.cleaned_data['collection']))
            fobj.rels_ext.content.add(st)
            fobj.master.content = request.FILES['file']
            # pre-populate the object label and dc:title with the uploaded filename
            fobj.label = fobj.dc.content.title = request.FILES['file'].name
            fobj.save('ingesting user content')

            messages.success(request, 'Successfully ingested <a href="%s"><b>%s</b></a>' % \
                             (reverse('file:view', args=[fobj.pid]), fobj.pid))
            return HttpResponseSeeOtherRedirect(reverse('site-index'))
    else:
        initial_data = {}
        # if collection is specified in url parameters, pre-select the
        # requested collection on the form via initial data
        if 'collection' in request.GET:
            initial_data['collection'] = request.GET['collection']
        form = IngestForm(initial=initial_data)
    return render(request, 'file/ingest.html', {'form': form})

@permission_required_with_403('file.change_file')
def edit_metadata(request, pid):
    """View to edit the metadata for an existing
    :class:`~genrepo.file.models.FileObject` .

    On GET, display the form.  When valid form data is POSTed, updates
    thes object.
    """
    # response status should be 200 unless something goes wrong
    status_code = 200
    repo = Repository(request=request)
    # get the object (if pid is not None), or create a new instance
    obj = repo.get_object(pid, type=FileObject)
   
    # on GET, instantiate the form with existing object data (if any)
    if request.method == 'GET':
        form = DublinCoreEditForm(instance=obj.dc.content)

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        form = DublinCoreEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            # set or remove oai itemID based on form selection
            if 'enable_oai' in form.cleaned_data:
                enable_oai = form.cleaned_data['enable_oai']
                # FIXME: with ARKs we use ARK for the OAI id; what should we do without?
                if enable_oai:
                    obj.oai_id = 'oai:%s' % obj.uri
                else:
                    obj.oai_id = None
            try:
                result = obj.save('updated metadata')
                messages.success(request,
            		'Successfully updated <a href="%s"><b>%s</b></a>' % \
                         (reverse('file:view', args=[obj.pid]), obj.pid))

		# maybe redirect to file view page when we have one
                return HttpResponseSeeOtherRedirect(reverse('site-index'))
            except (DigitalObjectSaveFailure, RequestFailed) as rf:
                # do we need a different error message for DigitalObjectSaveFailure?
                if isinstance(rf, PermissionDenied):
                    msg = 'You don\'t have permission to modify this object in the repository.'
                else:
                    msg = 'There was an error communicating with the repository.'
                messages.error(request,
                               msg + ' Please contact a site administrator.')

                # pass the fedora error code (if any) back in the http response
                if hasattr(rf, 'code'):
                    status_code = getattr(rf, 'code')

    # if form is not valid, fall through and re-render the form with errors
    return render(request, 'file/edit.html', {'form': form, 'obj': obj},
                  status=status_code)

def view_metadata(request, pid):
    repo = Repository(request=request)
    obj = repo.get_object(pid, type=FileObject)
    # if the object doesn't exist or user doesn't have sufficient
    # permissions to know that it exists, 404
    if not obj.exists:
        raise Http404
    return render(request, 'file/view.html', {'obj': obj})


def download_file(request, pid):
    '''Download the master file datastream associated with a
    :class:`~genrepo.file.models.FileObject`'''
    repo = Repository(request=request)
    # FIXME: what should the default download filename be?
    extra_headers = {
        'Content-Disposition': "attachment; filename=%s" % (pid)
    } 
    # use generic raw datastream view from eulcore
    return raw_datastream(request, pid, FileObject.master.id, type=FileObject,
                          repo=repo, headers=extra_headers)
