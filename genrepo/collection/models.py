# file genrepo/collection/models.py
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

from django.conf import settings
from django.db.models import Model

from eulfedora.server import Repository
from eulfedora.models import DigitalObject
from eulfedora.rdfns import relsext

class AccessibleObject(DigitalObject):
    """A place-holder Fedora Object for auto-generating a PublicAccess
    content model which will be used for Fedora XACML access controls.
    """
    PUBLIC_ACCESS_CMODEL = 'info:fedora/emory-control:PublicAccess'
    CONTENT_MODELS = [ PUBLIC_ACCESS_CMODEL ]



class Collection(Model):
    '''Collection place-holder object to define Django permissions on
    :class:`CollectionObject` . 
    '''
    class Meta:
        permissions = (
            # add, change, and delete are created by default
        )


class CollectionObject(DigitalObject):
    """A Fedora CollectionObject.  Inherits the standard Dublin Core
    and RELS-EXT datastreams from
    :class:`~eulcore.fedora.models.DigitalObject`, and adds a content
    model to identify this item as a Collection object.
    """
    COLLECTION_CONTENT_MODEL = 'info:fedora/emory-control:Collection-1.0'
    CONTENT_MODELS = [ COLLECTION_CONTENT_MODEL, AccessibleObject.PUBLIC_ACCESS_CMODEL ]

    @property
    def default_pidspace(self):
        # use configured fedora pidspace (if any) when minting pids
        # dynamic property so it will always get current setting (e.g., if changed for tests)
        return getattr(settings, 'FEDORA_PIDSPACE', None)

    @staticmethod
    def all():
        """
        Returns all collections in the repository as
        :class:`~genrepo.collection.models.CollectionObject`
        """
        repo = Repository()
        colls = repo.get_objects_with_cmodel(CollectionObject.COLLECTION_CONTENT_MODEL,
                                             type=CollectionObject)
        return colls

    @property
    def members(self):
        '''Return all Fedora objects in the repository that are related to the current
        collection via isMemberOfCollection.'''
        # FIXME: loses repo permissions/credentials here... 
        repo = Repository()
        members = repo.risearch.get_subjects(relsext.isMemberOfCollection, self.uri)
        # for now, just returning as generic DigitalObject instances
        for pid in members:
            # TODO: should we restrict to accessible objects only?
            # (requires passing correct credentials through...)
            yield repo.get_object(pid)

    

