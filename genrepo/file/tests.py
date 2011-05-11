import os
from mock import Mock, patch
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client
from rdflib import URIRef

from eulcore.django.test import TestCase as EulcoreTestCase
from eulcore.django.fedora import Repository
from eulcore.fedora.rdfns import relsext
from eulcore.fedora.util import RequestFailed, PermissionDenied
from eulcore.xmlmap.dc import DublinCore

from genrepo.file.forms import IngestForm, DublinCoreEditForm
from genrepo.file.models import FileObject
from genrepo.collection.tests import ADMIN_CREDENTIALS, NONADMIN_CREDENTIALS

class FileViewsTest(EulcoreTestCase):
    fixtures =  ['users']   # re-using collection users fixture & credentials

    repo_admin = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                            password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))

    ingest_fname = os.path.join(settings.BASE_DIR, 'file', 'fixtures', 'hello.txt')

    ingest_url = reverse('file:ingest')

    def setUp(self):
        self.client = Client()

        # create a file object to edit
        self.obj = self.repo_admin.get_object(type=FileObject)
        self.obj.dc.content.title =  self.obj.label = 'Test file object'
        self.obj.dc.content.date =  '2011'
        self.obj.save()
        self.edit_url = reverse('file:edit', kwargs={'pid': self.obj.pid})

        self.pids = [self.obj.pid]

    def tearDown(self):
        for pid in self.pids:
            self.repo_admin.purge_object(pid)

    # ingest

    def test_get_ingest_form(self):
        # not logged in - should redirect to login page
        response = self.client.get(self.ingest_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected, 'Expected %s but returned %s for %s as AnonymousUser'
                             % (expected, code, self.ingest_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(self.ingest_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as logged in non-repo editor'
                         % (expected, code, self.ingest_url))

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        # on GET, form should be displayed
        response = self.client.get(self.ingest_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.context['form'], IngestForm))

        # collection URI passed in via GET should be pre-selected
        collections = IngestForm().fields['collection'].choices
        collection_tuple = collections[1] # 0 is blank. 1 is the first non-blank one
        collection_uri = collection_tuple[0]
        response = self.client.get(self.ingest_url, {'collection': collection_uri})
        self.assertEqual(collection_uri, response.context['form'].initial['collection'],
                         'collection URI specified in GET url parameter should be set as initial value')


    def test_incomplete_ingest_form(self):
        # not logged in - should redirect to login page
        response = self.client.post(self.ingest_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as AnonymousUser'
                         % (expected, code, self.ingest_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.post(self.ingest_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as logged in non-repo editor'
                         % (expected, code, self.ingest_url))

        # log in as repository editor for normal behavior
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)


        # on POST with incomplete data, should be rejected
        response = self.client.post(self.ingest_url, {
                'collection': 'info:fedora/example:42',
            })
        self.assertTrue(isinstance(response.context['form'], IngestForm))
        self.assertContains(response, 'This field is required')

    def test_correct_ingest_form(self):
        # log in as repository editor for normal behavior
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        # first find a valid collection
        collections = IngestForm().fields['collection'].choices
        collection_tuple = collections[1] # 0 is blank. 1 is the first non-blank one
        collection_uri = collection_tuple[0]

        # log in
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # on POST, ingest object
        with open(self.ingest_fname) as ingest_f:
            response = self.client.post(self.ingest_url, {
                'collection': collection_uri,
                'file': ingest_f,
            }, follow=True)
        self.assertEqual(len(response.redirect_chain), 1)
        self.assertEqual(response.redirect_chain[0][1], 303)
        self.assertEqual(response.status_code, 200)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully ingested' in messages[0])
        pid = re.search('<b>(.*)</b>', messages[0]).group(1)
        self.pids.append(pid)

        # inspect the ingested object
        new_obj = self.repo_admin.get_object(pid, type=FileObject)
        self.assertTrue(new_obj.has_requisite_content_models)
        statement = (new_obj.uriref, relsext.isMemberOfCollection, URIRef(collection_uri))
        self.assertTrue(statement in new_obj.rels_ext.content,
                        msg='RELS-EXT should have collection statement')
        self.assertEqual('hello.txt', new_obj.label,
                         msg='filename should be set as preliminary object label')
        self.assertEqual('hello.txt', new_obj.dc.content.title,
                         msg='filename should be set as preliminary dc:title')
        with open(self.ingest_fname) as ingest_f:
            self.assertEqual(new_obj.master.content.read(), ingest_f.read())


    # edit metadata

    def test_get_edit_form(self):
        # not logged in - should redirect to login page
        response = self.client.get(self.edit_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as AnonymousUser'
                         % (expected, code, self.edit_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.get(self.edit_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as logged in non-repo editor'
                         % (expected, code, self.edit_url))

        # log in as repository editor 
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        # on GET, form should be displayed with object data pre-populated
        response = self.client.get(self.edit_url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(isinstance(response.context['form'], DublinCoreEditForm))
        self.assertContains(response, self.obj.label,
                            msg_prefix='edit form should include object label')
        self.assertContains(response, self.obj.dc.content.date,
                            msg_prefix='edit form should include DC content such as date')

    def test_edit_invalid_form(self):
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        # POST invalid data (missing required title field)
        response = self.client.post(self.edit_url, {'creator': 'genrepo'})
        self.assertTrue(isinstance(response.context['form'], DublinCoreEditForm))
        self.assertContains(response, 'This field is required')

    def test_edit_valid_form(self):
        # not logged in - should redirect to login page
        response = self.client.post(self.edit_url)
        code = response.status_code
        expected = 302
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as AnonymousUser'
                         % (expected, code, self.edit_url))

        # logged in as user without required permissions - should 403
        self.client.login(**NONADMIN_CREDENTIALS)
        response = self.client.post(self.edit_url)
        code = response.status_code
        expected = 403
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for POST %s as logged in non-repo editor'
                         % (expected, code, self.edit_url))

        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)

        # valid form
        new_data = {'title': 'updated file object', 'description': 'test content', 'creator': 'eul'}
        response = self.client.post(self.edit_url, new_data, follow=True)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully updated' in messages[0])

        # inspect the updated object
        updated_obj = self.repo_admin.get_object(self.obj.pid, type=FileObject)
        self.assertEqual(new_data['title'], updated_obj.label,
                         msg='posted title should be set as object label')
        self.assertEqual(new_data['title'], updated_obj.dc.content.title,
                         msg='posted title should be set as dc:title')
        self.assertEqual(new_data['description'], updated_obj.dc.content.description,
                         msg='posted description should be set as dc:description')
        self.assertEqual(new_data['creator'], updated_obj.dc.content.creator,
                         msg='posted creator should be set as dc:creator')

    def test_edit_save_errors(self):
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        data = {'title': 'foo', 'description': 'bar', 'creator': 'baz'}
        # simulate fedora errors with mock objects
	mockrepo = Mock(spec=Repository, name='MockRepository')
        # this actually mocks the class, so return same mock when class is instantiated
        mockrepo.return_value = mockrepo
        # create a Mock object, but use a DublinCore instance for xmlobjectform to inspect
        testobj = Mock()
        testobj.dc.content = DublinCore()
        # Create a RequestFailed exception to simulate Fedora error 
        # - eulcore.fedora exceptions are initialized from httplib response,
        #   which can't be instantiated directly; create a mock response
        err_resp = Mock()
        err_resp.status = 500
        err_resp.reason = 'error'
        err_resp.read.return_value = 'error message'
        # generate Fedora error on object save
        testobj.save.side_effect = RequestFailed(err_resp)
        mockrepo.get_object.return_value = testobj

        # 500 error / request failed
	with patch('genrepo.file.views.Repository', new=mockrepo):
            response = self.client.post(self.edit_url, data, follow=True)
            expected, code = 500, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 500 error)'
                % (expected, code, self.edit_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_('error communicating with the repository' in messages[0])

        # update the mock object to generate a permission denied error
        err_resp.status = 401
        err_resp.reason = 'unauthorized'
        err_resp.read.return_value = 'denied'
        # generate Fedora error on object save
        testobj.save.side_effect = PermissionDenied(err_resp)
        
        # 401 error -  permission denied
	with patch('genrepo.file.views.Repository', new=mockrepo):
            response = self.client.post(self.edit_url, data, follow=True)
            expected, code = 401, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 401 error)'
                % (expected, code, self.edit_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_("You don't have permission to modify this object"
                         in messages[0])

