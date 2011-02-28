from django.http import HttpResponse
from django.template import RequestContext
from django.conf import settings
from os.path import join

import logging

from engine import TransformerFile
from engine import EMPTYDOC
from django.conf import settings

DEFAULT_PAGE_NAMESPACE=""        # WooMe's page namespace is "woome"
DEFAULT_PAGE_PATTERN="%s%s.xslt" # WooMe's page pattern is "%s_%s.xslt"

def page(request, page="index", namespace=DEFAULT_PAGE_NAMESPACE, **kwargs):
    """A generic XSLT view which just runs a page name derived XSLT file.

    Pass in a page to be rendered (this could come from a urls
    statement) and optionally a namespace.

    The 'namespace' allows you to namespace all the XSLT files that
    will be used like this in your transforms directory. For example,
    to serve a page ^main/$ you could write an XSLT called
    static_main.xslt. To use that you would declare your page url
    like:

      '(r'(?P<page>.*)/$', 'djangoxslt.xslt.views.page', {"namespace": "static"}),
      
    In order to make the namespace work we also allow a page pattern
    to be specified in the settings file. The page pattern is used to
    define how the namespace and the page name combine. The above
    example would require the following declared in settings.py:

       XSLT_PAGE_PATTERN="%s_%s.xslt"
    """
    logger = logging.getLogger("xslt.views.page")
    logger.info("page = %s namespace = %s" % (page, namespace))
    page_pattern = getattr(settings, "XSLT_PAGE_PATTERN", DEFAULT_PAGE_PATTERN)
    p = page_pattern % (namespace, page)
    t = TransformerFile(join(settings.TRANSFORMS, p))
    c = RequestContext(request, {})
    c.update(kwargs)
    out = t(EMPTYDOC, context=c)
    return HttpResponse(out)


# End
