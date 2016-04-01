#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# django-rest-swagger documentation build configuration file, created by
# sphinx-quickstart on Sun Nov  9 17:02:55 2014.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys
from rest_framework_swagger import VERSION

extensions = []

templates_path = ['_templates']

source_suffix = '.rst'

master_doc = 'index'

project = 'django-rest-swagger'
copyright = '2014, Marc Gibbons'

sys.path.append("../../")
version = VERSION
release = VERSION

exclude_patterns = []


pygments_style = 'sphinx'
html_theme = 'default'

html_static_path = ['_static']

htmlhelp_basename = 'django-rest-swaggerdoc'


latex_elements = {
}

latex_documents = [
    ('index', 'django-rest-swagger.tex', 'django-rest-swagger Documentation',
     'Marc Gibbons', 'manual'),
]


man_pages = [
    ('index', 'django-rest-swagger', 'django-rest-swagger Documentation',
     ['Marc Gibbons'], 1)
]

texinfo_documents = [
    ('index', 'django-rest-swagger', 'django-rest-swagger Documentation',
     'Marc Gibbons', 'django-rest-swagger', 'One line description of project.',
     'Miscellaneous'),
]
