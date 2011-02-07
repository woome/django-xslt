from django.conf.urls.defaults import *

urlpatterns = patterns(
    'djangoxslt.xslt.views',
    url(r'^testtransform/(?P<page>[A-Z-a-z0-9_-]+)/$', 'page', {"namespace": "testtransform"}),
    )
