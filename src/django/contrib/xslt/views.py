from django.http import HttpResponse
from django.template import RequestContext
from django.conf import settings
from os.path import join

import logging

from engine import TransformerFile
from engine import EMPTYDOC

DEFAULT_PAGE_NAMESPACE="page"
DEFAULT_PAGE_PATTERN="%s_%s.xslt"

def page(request, page="index", namespace=DEFAULT_PAGE_NAMESPACE, **kwargs):
    logger = logging.getLogger("xslt.views.page")
    logger.info("page = %s namespace = %s" % (page, namespace))

    p = DEFAULT_PAGE_PATTERN % (namespace, page)
    t = TransformerFile(join(settings.TRANSFORMS, p))
    c = RequestContext(request, {})
    c.update(kwargs)
    out = t(EMPTYDOC, context=c)
    return HttpResponse(out)


# End
