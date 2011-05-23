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

from django.conf import settings
from django.db.models import Model

from eulfedora.models import DigitalObject, FileDatastream
from eulfedora.rdfns import oai
from genrepo.collection.models import AccessibleObject


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
        return self.rels_ext.content.value(subject=self.uriref, predicate=oai.itemID)
    def _set_oai_id(self, value):
	# if value is None, remove the value
        if value is None:
            self._del_oai_id()
        else:
            # update/replace any oai item id (only one allowed)
            self.rels_ext.content.set((self.uriref, oai.itemID, Literal(value)))
    def _del_oai_id(self):
        self.rels_ext.content.remove((self.uriref, oai.itemID, self.oai_id))
    oai_id = property(_get_oai_id, _set_oai_id, _del_oai_id)
    


