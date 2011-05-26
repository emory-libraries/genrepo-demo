# genrepo-demo doc build configuration file

import genrepo

extensions = ['sphinx.ext.autodoc', 'sphinx.ext.intersphinx', 'sphinx.ext.todo']

# paths
exclude_trees = ['build']
source_suffix = '.rst'
master_doc = 'index'
# project metadata
project = u'Generic Ingest prototype'
copyright = u'2011, Emory University Libraries '
version = '%d.%d' % genrepo.__version_info__[:2]
release = genrepo.__version__
modindex_common_prefix = ['genrepo.']

pygments_style = 'sphinx'

# html settings
html_theme = 'default'
htmlhelp_basename = 'genrepodoc'

# latex settings
latex_documents = [
  ('index', 'GenericIngestprototype.tex', u'Generic Ingest prototype Documentation',
   u'Emory University Libraries ', 'manual'),
]

# extension settings: sphinx.ext.intersphinx
intersphinx_mapping = {
    'django': ('http://docs.djangoproject.com/en/1.2/ref/', 'http://docs.djangoproject.com/en/dev/_objects/'),
    'eulcommon': ('http://eulcommon.readthedocs.org/en/latest/', None),
    'eulfedora': ('http://eulfedora.readthedocs.org/en/latest/', None),
    'python': ('http://docs.python.org/', None),
}
