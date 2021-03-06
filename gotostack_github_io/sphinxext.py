# Copyright 2013 New Dream Network, LLC (DreamHost)
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import six
import string
import subprocess


def _html_page_context(app, pagename, templatename, context, doctree):
    # Insert the cgit link into the template context.
    context['other_versions'] = _get_other_versions(app)
    return None


def _get_other_versions(app):
    if not app.config.html_theme_options.get('show_other_versions', False):
        return []

    git_cmd = ["git", "tag"]
    try:
        raw_version_list = subprocess.Popen(
            git_cmd, stdout=subprocess.PIPE).communicate()[0]
    except OSError:
        app.warn('Cannot get tags from git repository. '
                 'Not setting "other_versions".')
        raw_version_list = ''

    # grab last five that start with a number and reverse the order
    if six.PY3:
        raw_version_list = raw_version_list.decode("utf8")
    _tags = [t.strip("'") for t in raw_version_list.split('\n')]
    other_versions = [
        t for t in _tags if t and t[0] in string.digits
        # Don't show alpha, beta or release candidate tags
        and 'rc' not in t and 'a' not in t and 'b' not in t
    ][:-5:-1]
    return other_versions


def builder_inited(app):
    theme_dir = os.path.join(os.path.dirname(__file__), 'theme')
    app.info('Using gotostack theme from %s' % theme_dir)
    # Insert our theme directory at the front of the search path and
    # force the theme setting to use the one in the package unless
    # another gotostack theme is already selected. This is done here,
    # instead of in setup(), because conf.py is read after setup()
    # runs, so if the conf contains these values the user values
    # overwrite these. That's not bad for the theme, but it breaks the
    # search path.
    app.config.html_theme_path.insert(0, theme_dir)
    # Set the theme name
    if not app.config.html_theme.startswith('gotostack'):
        app.config.html_theme = 'gotostack'
    # Re-initialize the builder, if it has the method for setting up
    # the templates and theme.
    if hasattr(app.builder, 'init_templates'):
        app.builder.init_templates()
    # Register our page context additions
    app.connect('html-page-context', _html_page_context)


def setup(app):
    app.connect('builder-inited', builder_inited)
