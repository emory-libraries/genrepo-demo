# file genrepo/file/models.py
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

from rdflib import Literal
import json

from django.conf import settings
from django.db.models import Model

from eulfedora import rdfns
from eulfedora.models import DigitalObject, FileDatastream
from eulfedora.server import Repository
from eulxml import xmlmap
from genrepo.collection.models import AccessibleObject, CollectionObject


class File(Model):
    '''File place-holder object to define Django permissions on
    :class:`FileObject` . 
    '''
    class Meta:
        permissions = (
            # add, change, and delete are created by default
        )

class FileObject(DigitalObject):
    """An opaque file for repositing on behalf of a user. Inherits the
    standard Dublin Core and RELS-EXT datastreams from
    :class:`~eulcore.fedora.models.DigitalObject`, and adds both a
    ``master`` datastream to contain the user's file as well as a content
    model for identifying these objects.
    """
    CONTENT_MODELS = [ AccessibleObject.PUBLIC_ACCESS_CMODEL ]

    @property
    def default_pidspace(self):
        # use configured fedora pidspace (if any) when minting pids
        # dynamic property so it will always get current setting (e.g., if changed for tests)
        return getattr(settings, 'FEDORA_PIDSPACE', None)


    master = FileDatastream("master", "reposited master file", defaults={
            'versionable': True,
        })
    "reposited master :class:`~eulcore.fedora.models.FileDatastream`"


    def _get_oai_id(self):
        return self.rels_ext.content.value(subject=self.uriref, predicate=rdfns.oai.itemID)
    def _set_oai_id(self, value):
	# if value is None, remove the value
        if value is None:
            self._del_oai_id()
        else:
            # update/replace any oai item id (only one allowed)
            self.rels_ext.content.set((self.uriref, rdfns.oai.itemID, Literal(value)))
    def _del_oai_id(self):
        self.rels_ext.content.remove((self.uriref, rdfns.oai.itemID, self.oai_id))
    oai_id = property(_get_oai_id, _set_oai_id, _del_oai_id)

    @property
    def collection(self):
        collection_uri = self.rels_ext.content.value(subject=self.uriref,
                                                     predicate=rdfns.relsext.isMemberOfCollection)
        if collection_uri:
            return CollectionObject(self.api, str(collection_uri).replace('info:fedora/', ''))
    

class DziImage(xmlmap.XmlObject):
    # simple xmlobject to generate DZI xml for DeepZoom/Seadragon functionality
    ROOT_NAME = 'Image'
    ROOT_NS = 'http://schemas.microsoft.com/deepzoom/2008'
    ROOT_NAMESPACES = { 'dz' : ROOT_NS}

    tilesize = xmlmap.IntegerField('@TileSize')
    overlap = xmlmap.IntegerField('@Overlap')
    format = xmlmap.StringField('@Format')
    width = xmlmap.IntegerField('dz:Size/@Width')
    height = xmlmap.IntegerField('dz:Size/@Height')

class ImageObject(FileObject):
    CONTENT_MODELS = [ 'info:fedora/genrepo-demo:Image-1.0', AccessibleObject.PUBLIC_ACCESS_CMODEL ]
    IMAGE_SERVICE = 'genrepo-demo:DjatokaImageService'
    
    content_types = ('image/jpeg', 'image/jp2', 'image/gif', 'image/bmp', 'image/png', 'image/tiff')

    # DC & RELS-EXT inherited; override master
    master = FileDatastream("source-image", "Master TIFF image", defaults={
            'mimetype': 'image/tiff',
            # FIXME: versioned? checksum?
        })

    has_preview = True
    is_image = True

    def get_preview_image(self):
        return self.getDissemination(self.IMAGE_SERVICE, 'getRegion', params={'level': 1})

    def get_region(self, params):
        # expose djatoka getRegion method for djatoka seadragon deep zoom
        return self.getDissemination(self.IMAGE_SERVICE, 'getRegion', params=params)

    _image_metadata = None
    @property
    def image_metadata(self):
        'Image metadata as returned by Djatoka getMetadata method (width, height, etc.)'
        if self._image_metadata is None:
            imgmeta = self.getDissemination(self.IMAGE_SERVICE, 'getMetadata')
            # getDissemination returns a tuple of result, url
            # load the image metadata returned by djatoka via json and return
            self._image_metadata = json.loads(imgmeta[0])
        return self._image_metadata

    # expose width & height from image metadata as properties
    @property
    def width(self):
        return self.image_metadata['width']
    @property
    def height(self):
        return self.image_metadata['height']

    def deepzoom_info(self):
        # generate deepzoom image info xmlobject for based on width & height
        return  DziImage(tilesize=256, overlap=1, format='jpg',
                           width=self.width, height=self.height)


class EmoryImageObject(ImageObject):
    # local image - same functionality as ImageObject, but cmodel & services in emory-control pidspace
    CONTENT_MODELS = [ 'info:fedora/emory-control:Image-1.0' ]
    IMAGE_SERVICE = 'emory-control:DjatokaImageService'
    

digital_object_classes = [ImageObject, FileObject, EmoryImageObject]

def init_by_cmodel(pid, request=None):
    # given a pid, initialize the appropriate type of digital object class based on content models
    repo = Repository(request=request)
    obj = repo.get_object(pid)
    # get a lit of content models on the object
    cmodels = list(repo.risearch.get_objects(obj.uri, rdfns.model.hasModel))
    type = None
    for objtype in digital_object_classes:
        # if every content model for the digital object class is present, use that type
        if all(cm in cmodels for cm in objtype.CONTENT_MODELS):
            type = objtype
            break

    # fallback
    if type is None:
        type = FileObject

    return repo.get_object(pid, type=type)

    
def object_type_from_mimetype(mimetype):
    # given a file mimetype, determine the appropriate digitalobject class to use
    for objtype in digital_object_classes:
        if hasattr(objtype, 'content_types') and mimetype in objtype.content_types:
            return objtype

    # if no match was found, use generic file object class
    return FileObject
