# file genrepo/file/tests.py
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

import os
from mock import Mock, patch
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.test import Client, TestCase
from rdflib import URIRef

from eulfedora.server import Repository
from eulfedora.rdfns import relsext
from eulfedora.util import RequestFailed, PermissionDenied
from eulxml.xmlmap.dc import DublinCore

from genrepo.file.forms import IngestForm, DublinCoreEditForm
from genrepo.file.models import FileObject, ImageObject, \
     init_by_cmodel, object_type_from_mimetype
from genrepo.collection.tests import ADMIN_CREDENTIALS, NONADMIN_CREDENTIALS


class FileObjectTest(TestCase):

    def test_set_oai_id(self):
        repo = Repository()
        fileobj = repo.get_object(type=FileObject)
        oai_id = 'oai:ark:/25593/123'
        # set
        fileobj.oai_id = oai_id
        self.assert_('<oai:itemID>%s</oai:itemID>' % oai_id in
                     fileobj.rels_ext.content.serialize())
        # get
        self.assertEqual(oai_id, fileobj.oai_id)
        # del
        del fileobj.oai_id
        self.assert_('<oai:itemID>' not in fileobj.rels_ext.content.serialize())

        # set None - should be equivalent to delete
        fileobj.oai_id = None
        self.assert_('<oai:itemID>' not in fileobj.rels_ext.content.serialize())

class ModelUtilsTest(TestCase):
    # tests for utility methods declared in file.models

    repo_admin = None

    def setUp(self):
        # instantiate repo_admin the first time we run, after the test settings are in place
        if self.repo_admin is None:
            self.repo_admin = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                                         password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))
        self.pids = []

    def tearDown(self):
        for pid in self.pids:
            self.repo_admin.purge_object(pid)

    def test_object_type_from_mimetype(self):
        self.assertEqual(ImageObject, object_type_from_mimetype('image/jpeg'))
        self.assertEqual(ImageObject, object_type_from_mimetype('image/gif'))
        self.assertEqual(FileObject, object_type_from_mimetype('image/unsupported-img'))
        self.assertEqual(FileObject, object_type_from_mimetype('text/plain'))
        
    def test_init_by_cmodel(self):
        # create file and image objects to test initialization
        fileobj = self.repo_admin.get_object(type=FileObject)
        fileobj.save()
        imgobj = self.repo_admin.get_object(type=ImageObject)
        imgobj.save()
        self.pids.extend([fileobj.pid, imgobj.pid])
        # init a new object from file pid - should be a file object
        initobj = init_by_cmodel(fileobj.pid)
        self.assert_(isinstance(initobj, FileObject))
        # since ImageObject extends FileObject, confirm that we didn't get the wrong thing
        self.assert_(not isinstance(initobj, ImageObject))
        # image pid should be returned as an ImageObject
        initobj = init_by_cmodel(imgobj.pid)
        self.assert_(isinstance(initobj, ImageObject))
        



class FileViewsTest(TestCase):
    fixtures =  ['users']   # re-using collection users fixture & credentials

    # repository with test credentials for loading & removing test objects
    # DON'T instantiate this at load time, since Fedora Test settings are not yet switched
    repo_admin = None
    
    ingest_fname = os.path.join(settings.BASE_DIR, 'file', 'fixtures', 'hello.txt')
    ingest_md5sum = '746308829575e17c3331bbcb00c0898b'   # md5sum of hello.txt 
    image_fname = os.path.join(settings.BASE_DIR, 'file', 'fixtures', 'test.jpg')
    image_md5sum = 'ef7397e4bde82e558044458045bba96a'   # md5sum of test.jpeg
    
    ingest_url = reverse('file:ingest')

    # required django form management metadata for formsets on DC edit form
    edit_mgmt_data = {}
    for field in ['creator', 'contributor', 'coverage', 'relation', 'subject']:
        edit_mgmt_data['%s_list-MAX_NUM_FORMS' % field] = ''
        edit_mgmt_data['%s_list-INITIAL_FORMS' % field] = 0
        edit_mgmt_data['%s_list-TOTAL_FORMS' % field] = 0
    

    def setUp(self):
        # instantiate repo_admin the first time we run, after the test settings are in place
        if self.repo_admin is None:
            self.repo_admin = Repository(username=getattr(settings, 'FEDORA_TEST_USER', None),
                                         password=getattr(settings, 'FEDORA_TEST_PASSWORD', None))

        self.client = Client()

        # create a file object to edit
        with open(self.ingest_fname) as ingest_f:
            self.obj = self.repo_admin.get_object(type=FileObject)
            self.obj.dc.content.title =  self.obj.label = 'Test file object'
            self.obj.dc.content.date =  '2011'
            self.obj.master.content = ingest_f
            self.obj.master.label = 'hello-world.txt'
            self.obj.master.checksum = self.ingest_md5sum
            self.obj.save()
        self.edit_url = reverse('file:edit', kwargs={'pid': self.obj.pid})
        self.download_url = reverse('file:download', kwargs={'pid': self.obj.pid})
        self.view_url = reverse('file:view', kwargs={'pid': self.obj.pid})

        # create a image object for testing
        with open(self.image_fname) as ingest_f:
            self.imgobj = self.repo_admin.get_object(type=FileObject)
            self.imgobj.dc.content.title =  self.imgobj.label = 'Test file object'
            self.imgobj.master.content = ingest_f
            self.imgobj.master.label = 'test.jpg'
            self.imgobj.master.checksum = self.image_md5sum
            self.imgobj.save()

        self.pids = [self.obj.pid, self.imgobj.pid]

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
        self.assertEqual('hello.txt', new_obj.master.label,
                         msg='filename should be set as master datastream label')
        with open(self.ingest_fname) as ingest_f:
            self.assertEqual(new_obj.master.content.read(), ingest_f.read())
        # confirm that current site user appears in fedora audit trail
        xml, uri = new_obj.api.getObjectXML(pid)
        self.assert_('<audit:responsibility>%s</audit:responsibility>' % \
                     ADMIN_CREDENTIALS['username'] in xml)

        # supported image file should be ingested as ImageObject
        with open(self.image_fname) as ingest_f:
            response = self.client.post(self.ingest_url, {
                'collection': collection_uri,
                'file': ingest_f,
            }, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully ingested' in messages[0])
        pid = re.search('<b>(.*)</b>', messages[0]).group(1)
        self.pids.append(pid)
        
        # check that the object was ingested as an Image
        img_obj = self.repo_admin.get_object(pid, type=ImageObject)
        self.assertTrue(img_obj.has_requisite_content_models)


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
        # enable_oai should be false
        self.assertFalse(response.context['form']['enable_oai'].value())
        # master ds label should be set as filename
        self.assertEqual(self.obj.master.label, response.context['form']['file_name'].value(),
            'master datastream label should be pre-populated as filename in the form')

        # enable_oai set based on presence of oai id
        self.obj.oai_id = 'oai:foo'
        self.obj.save()
        response = self.client.get(self.edit_url)
        # enable_oai should be true
        self.assertTrue(response.context['form']['enable_oai'].value()) 

    def test_edit_invalid_form(self):
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        
        # POST invalid data (missing required title field)
        data = self.edit_mgmt_data.copy()
        data.update({'descrition': 'test'})
        response = self.client.post(self.edit_url, data)
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
        new_data = self.edit_mgmt_data.copy()
        subjects = ['test', 'repositories']
        new_data.update({'title': 'updated file object', 'description': 'test content',
                         'creator_list-TOTAL_FORMS': 1, 'creator_list-0-val': 'genrepo',
                         'subject_list-TOTAL_FORMS': 2, 'subject_list-0-val': subjects[0],
                         'subject_list-1-val': subjects[1],
                         'enable_oai': True,
                         'file_name': 'hello.txt'
                         })
        response = self.client.post(self.edit_url, new_data, follow=True)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully updated' in messages[0])

        # inspect the updated object
        updated_obj = self.repo_admin.get_object(self.obj.pid, type=FileObject)
        self.assertEqual(new_data['title'], updated_obj.label,
            msg='posted title should be set as object label; expected %s, got %s' % \
                         (new_data['title'], updated_obj.label))
        self.assertEqual(new_data['title'], updated_obj.dc.content.title,
            msg='posted title should be set as dc:title; expected %s, got %s' % \
                         (new_data['title'], updated_obj.dc.content.title))
        self.assertEqual(new_data['description'], updated_obj.dc.content.description,
            msg='posted description should be set as dc:description; expected %s, got %s' % \
                         (new_data['description'], updated_obj.dc.content.description))
        self.assertEqual(new_data['creator_list-0-val'], updated_obj.dc.content.creator,
            msg='posted creator should be set as dc:creator; expected %s, got %s' % \
                         (new_data['creator_list-0-val'], updated_obj.dc.content.creator))
        self.assertEqual(2, len(updated_obj.dc.content.subject_list),
            msg='expected 2 subjects after posting 2 subject_list values, got %d' % \
                         len(updated_obj.dc.content.subject_list))
        self.assertEqual(subjects, updated_obj.dc.content.subject_list)
        self.assertNotEqual(None, updated_obj.oai_id)
        self.assertEqual(new_data['file_name'], updated_obj.master.label,
            msg='posted file name should be set as master datastream label; expected %s, got %s' % \
                         (new_data['file_name'], updated_obj.master.label))


        # remove oai item id
        new_data.update({'enable_oai': False})
        response = self.client.post(self.edit_url, new_data, follow=True)
        messages = [ str(msg) for msg in response.context['messages'] ]
        self.assertTrue('Successfully updated' in messages[0])
        # inspect the updated object
        updated_obj = self.repo_admin.get_object(self.obj.pid, type=FileObject)
        self.assertEqual(None, updated_obj.oai_id)


    def test_edit_save_errors(self):
        self.client.post(settings.LOGIN_URL, ADMIN_CREDENTIALS)
        data = self.edit_mgmt_data.copy()
        data.update({'title': 'foo', 'description': 'bar', 'creator': 'baz', 'file_name': 'foo.txt'})
        # simulate fedora errors with mock objects
        testobj = Mock(spec=FileObject, name='MockDigitalObject')
        # django templates recognize this as a callable; set to return itself when called
        testobj.return_value = testobj
        # create a Mock object, but use a DublinCore instance for xmlobjectform to inspect
        testobj.dc.content = DublinCore()
        testobj.pid = 'pid:1'	# required for url generation 
        # Create a RequestFailed exception to simulate Fedora error 
        # - eulcore.fedora wrap around an httplib response
        err_resp = Mock()
        err_resp.status = 500
   	err_resp.read.return_value = 'error message'
        # generate Fedora error on object save
        testobj.save.side_effect = RequestFailed(err_resp)

        # 500 error / request failed
        # patch the repository class to return the mock object instead of a real one
	#with patch.object(Repository, 'get_object', new=Mock(return_value=testobj)):
        with patch('genrepo.file.views.init_by_cmodel', new=Mock(return_value=testobj)):            
            response = self.client.post(self.edit_url, data, follow=True)
            expected, code = 500, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 500 error)'
                % (expected, code, self.edit_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_('error communicating with the repository' in messages[0])

        # update the mock object to generate a permission denied error
        err_resp.status = 401
        err_resp.read.return_value = 'denied'
        # generate Fedora error on object save
        testobj.save.side_effect = PermissionDenied(err_resp)
        
        # 401 error -  permission denied
	#with patch.object(Repository, 'get_object', new=Mock(return_value=testobj)):            
        with patch('genrepo.file.views.init_by_cmodel', new=Mock(return_value=testobj)):
            response = self.client.post(self.edit_url, data, follow=True)
            expected, code = 401, response.status_code
            self.assertEqual(code, expected,
            	'Expected %s but returned %s for %s (Fedora 401 error)'
                % (expected, code, self.edit_url))
            messages = [ str(msg) for msg in response.context['messages'] ]
            self.assert_("You don't have permission to modify this object"
                         in messages[0])

    def test_download_master(self):
        response = self.client.get(self.download_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as AnonymousUser'
                         % (expected, code, self.download_url))
        expected = 'attachment; filename=%s' % self.obj.master.label
        self.assertEqual(response['Content-Disposition'], expected,
                        "Expected '%s' but returned '%s' for %s content disposition" % \
                        (expected, response['Content-Disposition'], self.download_url))
        with open(self.ingest_fname) as ingest_f:        
            self.assertEqual(ingest_f.read(), response.content,
                'download response content should be equivalent to file ingested as master datastream')

        # test image object (different datastraem)
        img_download_url = reverse('file:download', kwargs={'pid': self.imgobj.pid})
        response = self.client.get(img_download_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as AnonymousUser'
                         % (expected, code, img_download_url))
        expected = 'attachment; filename=%s' % self.imgobj.master.label
        self.assertEqual(response['Content-Disposition'], expected,
                        "Expected '%s' but returned '%s' for %s content disposition" % \
                        (expected, response['Content-Disposition'], img_download_url))
        with open(self.image_fname) as ingest_f:        
            self.assertEqual(ingest_f.read(), response.content,
                'download response content should be equivalent to file ingested as master datastream')
            
        # errors not tested here because they should be handled by eulcore view

    def test_view_metadata_min(self):
        # view metadata - minimal fields present
        response = self.client.get(self.view_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as AnonymousUser'
                         % (expected, code, self.view_url))
        
        dc = self.obj.dc.content
        self.assertContains(response, dc.title)
        self.assertNotContains(response, 'Creator',
            msg_prefix='metadata view should not include creator when not set in dc')
        self.assertNotContains(response, 'Contributor',
            msg_prefix='metadata view should not include contributor when not set in dc')
        self.assertNotContains(response, 'Coverage:',
            msg_prefix='metadata view should not include coverage when not set in dc')
        self.assertNotContains(response, 'Language:',
            msg_prefix='metadata view should not include language when not set in dc')
        self.assertNotContains(response, 'Publisher:',
            msg_prefix='metadata view should not include publisher when not set in dc')
        self.assertNotContains(response, 'Source',
            msg_prefix='metadata view should not include source when not set in dc')
        self.assertNotContains(response, 'Type:',
            msg_prefix='metadata view should not include type when not set in dc')
        self.assertNotContains(response, 'Format:',
            msg_prefix='metadata view should not include format when not set in dc')
        self.assertContains(response, 'Date:')
        self.assertContains(response, dc.date)

        # check for links to raw datastreams
        self.assertContains(response, reverse('file:raw-ds', kwargs={'pid': self.obj.pid, 'dsid': 'DC'}),
            msg_prefix='metadata view should link to raw DC view')
        self.assertContains(response, reverse('file:raw-ds', kwargs={'pid': self.obj.pid, 'dsid': 'RELS-EXT'}),
            msg_prefix='metadata view should link to raw RELS-EXT view')


    def test_view_metadata_full(self):        
        # update test object metadata to test template display with full fields
        self.obj.dc.content.description =  'Some explanatory text'
        self.obj.dc.content.creator_list =  ['You', 'Me']
        self.obj.dc.content.contributor_list =  ['Them']
        self.obj.dc.content.coverage_list =  ['20th Century', 'Earth']
        self.obj.dc.content.language =  'English'
        self.obj.dc.content.publisher =  'EUL'
        self.obj.dc.content.relation =  'Part of Collection Foo'
        self.obj.dc.content.source =  'the ether'
        self.obj.dc.content.subject_list =  ['testing', 'generals', 'repositories']
        self.obj.dc.content.type =  'Text'
        self.obj.dc.content.format =  'text/plain'
        self.obj.dc.content.identifier =  'foo1'
        self.obj.save('adding DC content to test metadata view')
        
        response = self.client.get(self.view_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s as AnonymousUser'
                         % (expected, code, self.view_url))

        dc = self.obj.dc.content
        self.assertContains(response, dc.description)
        self.assertContains(response, 'Creators:')
        self.assertContains(response, dc.creator_list[0])
        self.assertContains(response, dc.creator_list[1])
        self.assertContains(response, 'Contributor:')
        self.assertContains(response, dc.contributor_list[0])
        self.assertContains(response, 'Coverage:')
        self.assertContains(response, dc.coverage_list[0])
        self.assertContains(response, dc.coverage_list[1])
        self.assertContains(response, 'Language:')
        self.assertContains(response, dc.language)
        self.assertContains(response, 'Publisher:')
        self.assertContains(response, dc.publisher)
        self.assertContains(response, 'Source:')
        self.assertContains(response, dc.source)
        self.assertContains(response, 'Type:')
        self.assertContains(response, dc.type)
        self.assertContains(response, 'Format:')
        self.assertContains(response, dc.format)
        self.assertContains(response, 'Date:')
        self.assertContains(response, dc.date)

    def test_view_metadata_notfound(self):
        view_url = reverse('file:view', kwargs={'pid': 'bogus:123'})

        response = self.client.get(view_url)
        code = response.status_code
        expected = 404
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s (invalid pid) as AnonymousUser'
                         % (expected, code, view_url))

    def test_raw_xml_datastreams(self):
        # check that raw datastream views are configured correctly
        dc_url = reverse('file:raw-ds', kwargs={'pid': self.obj.pid, 'dsid': 'DC'})
        relsext_url = reverse('file:raw-ds', kwargs={'pid': self.obj.pid, 'dsid': 'RELS-EXT'})
        
        response = self.client.get(dc_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s (raw DC)'
                         % (expected, code, dc_url))
        self.assertEqual(response.content, self.obj.dc.content.serialize(pretty=True))

        response = self.client.get(relsext_url)
        code = response.status_code
        expected = 200
        self.assertEqual(code, expected,
                         'Expected %s but returned %s for GET %s (raw RELS-EXT)'
                         % (expected, code, relsext_url))
        # may not serialize exactly the same every time
        # simple check to make sure we're getting rdf that looks corretc
        self.assert_('<rdf:RDF' in response.content)
        self.assert_(self.obj.pid in response.content)


