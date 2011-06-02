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

import magic
from rdflib import URIRef

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import Http404, HttpResponse
from django.shortcuts import render

from eulcommon.djangoextras.auth.decorators import permission_required_with_403
from eulcommon.djangoextras.http import HttpResponseSeeOtherRedirect
from eulfedora.models import DigitalObjectSaveFailure
from eulfedora.rdfns import relsext
from eulfedora.server import Repository
from eulfedora.views import raw_datastream
from eulfedora.util import RequestFailed, PermissionDenied

from genrepo.file.forms import IngestForm, DublinCoreEditForm
from genrepo.file.models import FileObject, ImageObject, object_type_from_mimetype, init_by_cmodel

@permission_required_with_403('file.add_file')
def ingest_form(request):
    """Display or process the file ingest form. On GET, display the form. On
    valid POST, reposit the submitted file in a new digital object.
    """
    if request.method == 'POST':
        form = IngestForm(request.POST, request.FILES)
        if form.is_valid():
            # use mime magic to determine type of object to create
            m = magic.Magic(mime=True)
            mimetype = m.from_file(request.FILES['file'].temporary_file_path())
            objtype = object_type_from_mimetype(mimetype)
            # initialize a connection to the repository and create a new object
            repo = Repository(request=request)
            fobj = repo.get_object(type=objtype)
            # set file mimetype in dc:format
            # TODO: file checksum?
            st = (fobj.uriref, relsext.isMemberOfCollection, 
                  URIRef(form.cleaned_data['collection']))
            fobj.rels_ext.content.add(st)
            fobj.master.content = request.FILES['file']
            # pre-populate the object label and dc:title with the uploaded filename
            fobj.label = fobj.dc.content.title = request.FILES['file'].name
            # also use the original filename as the file datastream label
            fobj.master.label = request.FILES['file'].name
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
    # init the object as the appropriate type
    obj = init_by_cmodel(pid, request)

    # on GET, instantiate the form with existing object data (if any)
    if request.method == 'GET':
        # enable_oai should pre-selected if object already has an oai id
        initial_data = {'enable_oai': bool(obj.oai_id),
                        'file_name': obj.master.label}
        form = DublinCoreEditForm(instance=obj.dc.content, initial=initial_data)

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        form = DublinCoreEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            # also use dc:title as object label
            obj.label = obj.dc.content.title
            # update master datastream label (required, should always be set)
            obj.master.label = form.cleaned_data['file_name']
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

# FIXME: These feel like they want to be somewhere else. models? templates?
EXTRA_ENV = {
    'seadragon_baseurl': getattr(settings, 'DJATOKA_SEADRAGON_BASEURL', ''),
    'jplayer_baseurl': getattr(settings, 'JPLAYER_BASEURL', ''),
    'jplayer_skin_baseurl': getattr(settings, 'JPLAYER_SKIN_BASEURL', ''),
}

def view_metadata(request, pid):
    # init the appropriate type (image, file) according to the cmodel
    obj = init_by_cmodel(pid, request)
    # if the object doesn't exist or user doesn't have sufficient
    # permissions to know that it exists, 404
    if not obj.exists:
        raise Http404 

    template = getattr(obj, 'view_template', 'file/view.html')
    env = EXTRA_ENV.copy()
    env.update(obj=obj)
    return render(request, template, env)

def preview(request, pid):
    # image preview of an object
    # currently only supported for image objects
    obj = init_by_cmodel(pid, request)
    return HttpResponse(obj.get_preview_image(), mimetype='image/jpeg')
    # TODO: error handling, unit tests...

def image_dzi(request, pid):
    # DZI xml image information  required by SeaDragon for deepzom
    # should be one of the image cmodels
    img = init_by_cmodel(pid, request=request)
    return HttpResponse(img.deepzoom_info().serialize(pretty=True), mimetype='text/xml')
    # TODO: error handling, unit tests...

def image_region(request, pid):
    # expose djatoka getRegion method for use in seadragon deep zoom functionality
    img = init_by_cmodel(pid, request)
    # convert svc.param format used by djatoka to param format used by fedora disseminator
    params = dict((k.replace('svc.', ''),v) for k,v in request.GET.iteritems())
    return HttpResponse(img.get_region(params), mimetype='image/jpeg')
    # TODO: error handling, unit tests...

def download_file(request, pid):
    '''Download the master file datastream associated with a
    :class:`~genrepo.file.models.FileObject`'''
    repo = Repository(request=request)
    obj = init_by_cmodel(pid, request)
    # use original or edited filename as download filename
    extra_headers = {
        'Content-Disposition': "attachment; filename=%s" % obj.master.label
    } 
    # use generic raw datastream view from eulcore
    # - use the datastream id and digital object type returned by cmodel init
    return raw_datastream(request, pid, obj.master.id, type=obj.__class__,
                          repo=repo, headers=extra_headers)
