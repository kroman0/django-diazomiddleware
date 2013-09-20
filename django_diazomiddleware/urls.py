import diazo
from django.conf.urls import patterns
from os.path import join, dirname

urlpatterns = patterns('',
                      (r'^diazo-debug/(?P<path>.*)$', 'django.views.static.serve', {
                       'document_root': join(dirname(diazo.__file__), 'debug_resources')}),
                       )
