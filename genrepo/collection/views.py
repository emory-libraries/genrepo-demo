from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response
from django.template import RequestContext

from eulcore.django.fedora.server import Repository
from eulcore.django.http import HttpResponseSeeOtherRedirect

from genrepo.collection.forms import CollectionDCEditForm
from genrepo.collection.models import CollectionObject

def create(request):
    """View to create a new
    :class:`~genrepo.collection.models.CollectionObject`.

    On GET, display the form.
    On POST, create a new Collection if the form is valid.
    """
    # on GET, instantiate a new form with no data
    if request.method == 'GET':
        form = CollectionDCEditForm()

    # on POST, create a new collection object, update DC from form
    # data (if valid), and save
    elif request.method == 'POST':
        repo = Repository()
        obj = repo.get_object(type=CollectionObject)
        form = CollectionDCEditForm(request.POST, instance=obj.dc.content)
        if form.is_valid():
            form.update_instance()
            obj.save()
            messages.success(request,
            	'Successfully created new collection <b>%s</b>' % obj.pid)
#            	'Successfully created new collection <a href="%s">%s</a>' % \
#                 (reverse('collections:edit', args=[obj.pid]), obj.pid))
            
            return HttpResponseSeeOtherRedirect(reverse('site-index'))

        # TODO: handle fedora errors
            
        # if form is not valid, fall through and re-render the form with errors
    return render_to_response('collection/edit.html', {'form': form},
            context_instance=RequestContext(request))
