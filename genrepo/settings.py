# file genrepo/settings.py
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

# Django settings for genrepo project.

import os

# Get the directory of this file for relative dir paths.
# Django sets too many absolute paths.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# Site base url, when not deployed at root url (e.g., '/genrepo' )
SITE_URL_PREFIX = ''

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    # django default context processors
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.contrib.messages.context_processors.messages",
    # additional context processors
    "django.core.context_processors.request", # always include request in render context
    "genrepo.version_context", # include app version
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'genrepo.urls'

TEMPLATE_DIRS = [
    os.path.join(BASE_DIR, 'templates'),
]

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'eulfedora',
    'genrepo.accounts',
    'genrepo.collection',
    'genrepo.file',
)


AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',
)

FILE_UPLOAD_HANDLERS = (
    # removing default MemoryFileUploadHandler so all uploaded files can be treated the same
    'django.core.files.uploadhandler.TemporaryFileUploadHandler',
)

# session configuration
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'    # use same cache in use elsewhere
SESSION_COOKIE_AGE = 604800   # 1 week (Django default is 2 weeks)
SESSION_COOKIE_SECURE = True  # mark cookie as secure, only transfer via HTTPS
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# using default django login url
LOGIN_URL = SITE_URL_PREFIX + '/accounts/login/'

AUTH_PROFILE_MODULE = 'emory_ldap.EmoryLDAPUserProfile'


try:
    from localsettings import *
except ImportError:
    import sys
    print >>sys.stderr, 'No local settings. Trying to start, but if ' + \
        'stuff blows up, try copying localsettings.py.sample to ' + \
        'localsettings.py and setting appropriately for your environment.'
    pass

import sys
try:
    sys.path.extend(EXTENSION_DIRS)
except NameError:
    pass # EXTENSION_DIRS not defined. This is OK; we just won't use it.
del sys

# use eulfedora test suite runner for start/stop test fedora configuration & setup
TEST_RUNNER = 'eulfedora.testutil.FedoraTestSuiteRunner'

try:
    # use xmlrunner variant if it's installed
    import xmlrunner
    TEST_RUNNER = 'eulfedora.testutil.FedoraXmlTestSuiteRunner'
    TEST_OUTPUT_DIR='test-results'
    TEST_OUTPUT_VERBOSE = True
    TEST_OUTPUT_DESCRIPTIONS = True
except ImportError:
    pass


