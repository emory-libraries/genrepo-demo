# file genrepo/collection/forms.py
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

from django import forms

from eulxml.xmlmap.dc import DublinCore
from eulxml.forms import XmlObjectForm

class CollectionDCEditForm(XmlObjectForm):
    """Form to edit
    :class:`~genrepo.collection.models.CollectionObject` metadata."""
    title = forms.CharField(required=True,
        help_text='Title or label for the collection.')
    description = forms.CharField(required=False,
        help_text='General description of the collection and its contents. (optional)',
        widget=forms.Textarea)
    # should we offer any other fields at the collection level?
    class Meta:
        model = DublinCore
        fields = ['title', 'description']
