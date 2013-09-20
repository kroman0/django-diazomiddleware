======================
Django DiazoMiddleware
======================
Integrate Diazo in Django using Django middleware mechanism

.. image:: https://travis-ci.org/kroman0/django-diazomiddleware.png?branch=master
   :target: https://travis-ci.org/kroman0/django-diazomiddleware

************
Installation
************

settings.py
===========

::

    MIDDLEWARE_CLASSES = (
        ...
        'django_diazomiddleware.middleware.DiazoMiddleware',
    )

    DIAZO_SETTINGS = {
        'parameter_expressions': {
            'about': lambda request: "about" in request.path,
        },
        'read_network': False,
        'doctype': "<!DOCTYPE html>",
        'rules': "/theme/rules.xml",
        'enabled': True,
        'prefix': "/theme",
        'update_content_length': True,
    }

urls.py
=======

::

    urlpatterns = patterns('',
        (r'', include('django_diazomiddleware.urls')),
    )

    urlpatterns += patterns('',
        (r'^theme/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': "path_to_theme"}),
    )


********
Settings
********

- `parameter_expressions`
- `read_network`
- `doctype`
- `rules`
- `enabled`
- `prefix`
- `update_content_length`
