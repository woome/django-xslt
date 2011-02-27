# XSLT helper
from __future__ import with_statement

"""
A Django template engine for XSLT.

This isn't a real template engine, in the sense that it does not
provide any Template class. We'll work towards that.

It does allow Django to use XSLT templates and to include context
variables in your templates with an xpath syntax.

In order to do this we implement an extension system that makes
context variables map to xpath functions. 

A context variable called as a function with no arguments returns the
string rendering of the context variable.

However, a context variable called with an argument is intended to
allow abstracted rendering behaviour. The argument is called the
''mapper key'' and provides a string -> callable mapping which will be
used to render the of the context variable to a legal XPath value. The
callable mapped to is called the ''renderer''.

Three renderers are defined by default:

 * xml 

   returns the context variable string evaluated but wrapped in a DIV
   element.

 * parse

   attempts to XML parse the context variable string evaluation.

 * parsehtml

   attempts to HTML parse the context variable string evaluation, the
   parsed document is normalized to XML before being returned so that
   it can be succesfully evaluated by XSLT.

   Currently, we fix any HTML parsed document with the XHTML namespace.


Further renderers may be specified in settings with the variable
XSLT_MAPPER:

 import project.render
 XSLT_MAPPER = {
       "project_special_render": project.render.do_render
    }

mapping keys defined in settings may override the default renderers.
"""

from django.conf import settings

from lxml import etree
from lxml.builder import E
from StringIO import StringIO
import re
import logging
import traceback

# This is a simple empty document you can pass into Transformer.__call__ if you need to.
EMPTYDOC = etree.Element("empty")

# DO NOT change these without running the xslt unit-tests in this module.
FUNC_MATCH_RE1 = re.compile(r"{?xdjango:[^}]+}?")
FUNC_MATCH_RE2 = re.compile(r"{?xdjango:([^(]+)\((.*?)\)}?")

# taken from drivel.config
def dotted_import(name):
    mod, attr = name.split('.'), []
    obj = None
    while mod:
        try:
            obj = __import__('.'.join(mod), {}, {}, [''])
        except ImportError, e:
            attr.insert(0, mod.pop())
        else:
            for a in attr:
                try:
                    obj = getattr(obj, a)
                except AttributeError, e:
                    raise AttributeError('could not get attribute %s from %s -> %s (%r)' % (
                        a, '.'.join(mod), '.'.join(attr), obj))
            return obj
    raise ImportError('could not import %s' % name)


class Exml(object):
    """A simple document builder for lxml"""
    def __init__(self, element_name, **attribs):
        self.el = None
        self.element_name = element_name
        self.attribs = attribs

    def append(self, element_name, **attribs):
        if self.el == None:
            self.el = etree.Element(self.element_name)
            for name,value in self.attribs.iteritems():
                self.el.set(name,str(value))

        ne=etree.SubElement(self.el, element_name)
        for name,value in attribs.iteritems():
            ne.set(name,str(value))

        ec = Exml(element_name, **attribs)
        ec.el = ne
        return ec


class Xml(object):
    def __init__(self, data, base_url=None, parser=None):
        self.parser = parser if parser else etree.XMLParser()
        self.data = data
        self.base_url = base_url

    def __call__(self):
        doc = etree.fromstring(
            self.data,
            parser=self.parser,
            base_url=self.base_url)
        return doc

class Html(Xml):
    def __init__(self, data, base_url=None, parser=None):
        super(Html,self).__init__(data, base_url, parser if parser else etree.HTMLParser())

XHTML_NAMESPACE = "http://www.w3.org/1999/xhtml"
DJANGO_NAMESPACE="http://djangoproject.com/template/xslt"

from django.template import Variable
from django.template import VariableDoesNotExist
import types
import threading
djangothread = threading.local()

class DjangoContextFunc(object):
    """Implements an extension function for django contexts"""
    def __init__(self, name, context=None):
        self.logger = logging.getLogger("xslt.DjangoContextFunc.%s" % name)
        self.logger.debug("creating %s" % name)
        self.name = name
        # Define some default mappers and extend with settings
        self.mappers = {
            "xml": self.xml,
            "parsehtml": self.parsehtml,
            "parse": self.parse
            }
        self._context = context
        try:
            self.mappers.update(settings.XSLT_MAPPER)
        except AttributeError:
            pass

    @property
    def context(self):
        if self._context is None:
            return djangothread.context
        return self._context

    def _django_eval(self):
        """
        When the variable doesn't resolve, we return an empty string,
        this allows for tests such as:
        <xsl:if test="django:form.errors()">
            <xsl:value-of select="django:form.errors.fieldname" />
        </xsl:if>
        
        Where form.errors is a dict, and form.errors['fieldname'] 
        may not exist, returning an empty string will allow evaluation
        to continue.
        """
        try:
            e = Variable(self.name).resolve(self.context)
            return e
        except VariableDoesNotExist, e:
            # Nic says: I think there should be some debug setting
            # here to make this report the error
            errmsg = "problem evaling variable %s %s %s" % (
                self.name,
                e.__class__.__name__,
                e
                )
            self.logger.error(errmsg)
            return ""
        except Exception, e:
            errmsg = "problem evaling variable %s %s %s" % (
                self.name,
                e.__class__.__name__,
                e
                )
            self.logger.error(errmsg)
            if settings.DEBUG:
                return [E.error(errmsg)]
            return ""

    def parsehtml(self, ctx_value, *args):
        try:
            # First make it HTML
            htmldoc = etree.HTML(ctx_value)
            xmldoc = etree.XML(re.sub(
                    "<html>", 
                    """<html xmlns="%s">""" % XHTML_NAMESPACE,
                    etree.tostring(htmldoc)
                    ))
            self.logger.debug(etree.tostring(xmldoc))
            doc= [xmldoc]
            return doc
        except etree.XMLSyntaxError, e:
            self.logger.debug(ctx_value)
            for i in e.error_log:
                self.logger.error("couldn't transform %s" % i)
                self.logger.debug(traceback.format_exc())
            if settings.DEBUG:
                errors = [E.li(str(error)) for error in e.error_log]
                return [E.ol(*errors)]
            return ""

    def parse(self, ctx_value, *args):
        try:
            ## Not sure if it's better to return EMPTYDOC from here if nothing is passed in
            if ctx_value:
                xmldoc = etree.fromstring(unicode(ctx_value))
                doc= [xmldoc]
                return doc
            else:
                return EMPTYDOC
        except etree.XMLSyntaxError, e:
            self.logger.debug(ctx_value)
            for i in e.error_log:
                self.logger.error("couldn't transform %s via %s %s" % (i, ctx_value, args))
                self.logger.debug(traceback.format_exc())
            if settings.DEBUG:
                errors = [E.li(str(error)) for error in e.error_log]
                return [E.ol(*errors)]
            return ""

    def xml(self, ctx_value, *args):
        e = etree.Element("div" if len(args) < 2 else args[1])
        e.text = ctx_value
        return [e]
    
    def __call__(self, ctx, *args):
        """Treat a django context variable as an XSLT callable.

        If the context object supports the __xml__ protocol then the
        method is called (with any arguments) and the return value is
        expected to be some XML value like an lxml DOM or an XPath
        value, like a string.

        If the call specifies a renderer name as arg #1 then the
        renderer name is looked up in settings.XSLT_MAPPER and the
        resulting callable name evaled and then passed the context
        variable and the rest of the args.
        
        If the context object does not support __xml__ and the call
        does not specify a renderer then it is just str(evaled).

        The arguments to this function are the normal xpath extension
        function arguments: 'ctx' is an opaque xpath context value and
        'args' is (mostly) the list of arguments supplied to the xpath
        function.
        """
        self.logger.debug("called %s" % args[0] if len(args) > 0 else "")
        try:
            ctx_value = self._django_eval()
            self.logger.debug("context value %s" % ctx_value)

            # If the context object supports the render protocol use it
            try:
                # We just EXPECT the value to be XML
                if len(args):
                    return ctx_value.__xml__(*args)
                return ctx_value.__xml__()
            except AttributeError:
                pass
            
            # If there are no args there is no defined renderer
            if not len(args):
                if isinstance(ctx_value, basestring):
                    return ctx_value
                return str(ctx_value)

            # If the argument are xpath evaled they are general complex
            # lxml returns them as lists... python is expecting something simpler
            # not sure the best way to do this... maybe a higher level API
            # passing a context to the function.
            a = [str(x[0]) if isinstance(x,type([])) else x \
                     for x in args]
            fn = a.pop(0)

            # This is a useful place to put trace breaks
            # you can test fn for your renderer name
            renderer_mapped = self.mappers[fn]
            if isinstance(renderer_mapped, basestring):
                try:
                    renderer = renderer_mapped.split(".")
                    self.logger.debug("found renderer %s" % ".".join(renderer))
                    r = dotted_import(renderer_mapped)
                    value = r(ctx_value, *a)
                except Exception, e:
                    errmsg = "renderer %s had error %s" % (
                        ".".join(renderer),
                        e)
                    self.logger.error(errmsg, exc_info=True)
                    return [E.error(errmsg)]
                else:
                    return value
            elif isinstance(renderer_mapped, types.FunctionType):
                value = renderer_mapped(ctx_value, *a)
                self.logger.debug("%s returning %s", fn, value)
                return value
            elif isinstance(renderer_mapped, types.MethodType):
                value = renderer_mapped(ctx_value, *a)
                self.logger.debug("%s returning %s", fn, value)
                return value
        except Exception, e:
            errmsg = "resolving context call %s had error %s %s" % (
                self.name,
                e.__class__.__name__,
                e)
            self.logger.error(errmsg, exc_info=True)
            return [E.error(errmsg + traceback.format_exc())]
            
        
class DjangoResolver(etree.Resolver):
    """A base django resolver.

    This is necessary to discover functions used in  every XSLT document.

    The resolver connects xpath expressions of the kind:

      xdjango:contextvarname(args)

    to context variable mapping implementations; eg:

      xdjango:contextvar('xml')

    will cause the Django context variable 'contextvar' to be rendered 
    with the XML context variable renderer, while:

      xdjango:contextvar('reported')

    will cause the Django context variable 'contextvar' to be rendered
    with the renderer 'reported', presumably a custom renderer for that
    data type.
    """

    def __init__(self, transformer):
        self.transformer = transformer
        # Not sure, do we need our own resolver as well?
        self.parser = etree.XMLParser()

    def _resolve(self, content, context, base_url=None):
        xml = etree.parse(StringIO(content), self.parser)

        # We should check this is an xslt document
        results = xml.xpath(
            "//@*",
            namespaces={
                # The tag used here is relied upon in the following regexing
                "xdjango": DJANGO_NAMESPACE,
                })
        # Not a perfect regex here, {} should wrap, or not.
        djangocalls = [r for r in results if FUNC_MATCH_RE1.search(r)]

        for call in djangocalls:
            offset = 0
            while True:
                m = FUNC_MATCH_RE2.search(call, offset)
                if m is None:
                    break
                name = m.group(1)
                offset = m.end()
                if name not in self.transformer.fns:
                    self.transformer.fns[name] = DjangoContextFunc(name)
        # We want to call the actual super here
        return super(DjangoResolver, self).resolve_string(
            content, 
            context, 
            base_url=base_url)

    def resolve(self, url, pubid, context):
        """Implement resolver for django transformers.

        At the moment this seems to only be able to do file based resolving.
        That's because I'm not sure how to differentiate on the url.
        """
        if url.partition(':')[0] not in ['http', 'django', 'querydirect']:
            # FIXME
            # We need a decent error here to say we couldn't find it.
            with open(url) as fd:
                content = fd.read()
                return self._resolve(content, context, base_url=url)

    def resolve_file(self, f, context, base_url=None):
        content = f.read()
        return self._resolve(content, context, base_url=base_url)

    def resolve_filename(self, filename, context):
        with open(filename) as f:
            content = f.read()
            return self._resolve(content, context, base_url=filename)
    
    def resolve_string(self, content, context, base_url=None):
        return self._resolve(content, context, base_url=base_url)


# Hook management

_transformer_init_hook_list = []
_transformer_percall_hook_list = []

def _transformer_init_hook(transformer_object):
    """Purely backward stuff
    
    This links our two xslt systems.
    """
    global _transformer_init_hook_list
    for hook_func in _transformer_init_hook_list:
        hook_func(transformer_object)

def _transformer_percall_hook(transformer_object, doc, context, **params):
    for hook_func in _transformer_percall_hook_list:
        hook_func(transformer_object, doc, context, **params)

def add_init_hook(hookfunc):
    """Add the specified function to the list of functions called when we init a transformer."""
    global _transformer_init_hook_list
    if hookfunc not in _transformer_init_hook_list:
        _transformer_init_hook_list += [hookfunc]

def add_percall_hook(hookfunc):
    """Add the specified function to the list of functions called when we call a transformer.

    The hook must be a function like this:

      function(transformer_object, doc, context, **params)
    
    the parameters should be obvious.
    """
    global _transformer_percall_hook_list
    if hookfunc not in _transformer_init_hook_list:
        _transformer_percall_hook_list += [hookfunc]


# Transformers

class Transformer(object):
    def __init__(self, 
                 content, 
                 resolv=lambda c,p: etree.fromstring(c,p),
                 parser=None,
                 context=None):
        """Make a transformer object.

        The transformer wraps all the django specific functionality.
        
        Params:
          content is the XML content, this could be a string or a url
             the exact semantics of content are defined by resolver
           
          resolv is a function that is called to return the XSLT
          document, it is called like this:

              xsltdoc = resolv(content, parser)

          where content and parser are both the args from __init__.
          The default value of resolv is:

              lambda c,p: etree.fromstring(c,p)

          parser is the XMLParser to use. a default is supplied. 
        """
        context = context if context else {}

        global DJANGO_NAMESPACE
        self.logger = logging.getLogger("xslt.Transformer")
        self.fns = etree.FunctionNamespace(DJANGO_NAMESPACE)

        # Setup the rest of the environment
        self.parser = parser if parser else etree.XMLParser()

        # We call out here to anything that's defined
        _transformer_init_hook(self)

        # Setup the djangoxslt resolver
        self.resolver = DjangoResolver(self)
        self.parser.resolvers.add(self.resolver)

        # lxml doesn't seem to use the parser's resolver for this
        # Hence we need to do the great big hack below
        self.xslt_doc = resolv(content, self.parser)

        ## Great big hack
        # We should check this is an xslt document
        xml = self.xslt_doc
        results = xml.xpath(
            "//@*",
            namespaces={
                # The tag used here is relied upon in the following regexing
                "xdjango": DJANGO_NAMESPACE,
                })
        # Not a perfect regex here, {} should wrap, or not.
        djangocalls = [r for r in results if FUNC_MATCH_RE1.search(r)]
        for call in djangocalls:
            offset = 0
            while True:
                m = FUNC_MATCH_RE2.search(call, offset)
                if m is None:
                    break
                name = m.group(1)
                offset = m.end()
                if name not in self.fns:
                    self.fns[name] = DjangoContextFunc(name)
        # End Great big hack

        qs_extension = QuerySetTemplateElement()
        extensions = {(DJANGO_NAMESPACE, 'queryset'): qs_extension}
        self.xslt = etree.XSLT(self.xslt_doc, extensions=extensions)

    def __xslt_error__(self, errorlist):
        """Format an errorlist.

        Override this if you want your errors looking different.
        """
        errors = [E.li(str(error)) for error in errorlist]
        errordoc = E.html(
            E.h1("an error occurred"),
            E.ol(*errors)
            )
        return errordoc

    def __call__(self, 
                 doc=None, 
                 context=None, 
                 **params):
        from django.template import Context
        global djangothread
        djangothread.context = context if context != None else Context()
        doc = doc if doc is not None else EMPTYDOC

        # Call out to the percall hooks
        _transformer_percall_hook(self, doc, context, **params)

        # accept a string for document as well
        if isinstance(doc, basestring):
            doc = etree.fromstring(doc)

        try:
            return str(self.xslt(doc, **params))
        except etree.XSLTApplyError, e:
            self.logger.error("couldn't transform %s" % e.error_log)
            self.logger.error("couldn't transform %s" % e)
            self.logger.debug(self.__xslt_error__(e.error_log))

            if settings.DEBUG:
                return etree.tostring(self.__xslt_error__(e.error_log))
            else:
                raise
        except etree.XMLSyntaxError, e:
            for i in e.error_log:
                self.logger.error("couldn't transform %s" % i)
                self.logger.debug(traceback.format_exc())
            if settings.DEBUG:
                return etree.tostring(self.__xslt_error__(e.error_log))
            else:
                raise


from os.path import join as joinpath

def transformer_file_resolv_callback(c, p):
    """A resolver function for Transformer.

    c is the content which should be a filename
    p is the parser which we'll use.
    """
    logger = logging.getLogger("transformer_file_resolv_callback")
    try:
        stylesheet = joinpath(*c)
        return etree.parse(stylesheet, p)
    except etree.XMLSyntaxError:
        logger.error("stylesheet %s" % stylesheet)
        raise

class TransformerFile(Transformer):
    """Make a transformer from an XSLT file.

    You can pass through a list of filename parts that will be joined
    to construct a filename."""

    def __init__(self, *filename_parts, **kwargs):
        try:
            stylesheet = joinpath(filename_parts)
            self.stylesheet = stylesheet
            super(TransformerFile, self).__init__(
                stylesheet, 
                resolv=transformer_file_resolv_callback,
                **kwargs)
        except Exception, e:
            e.stylesheet = stylesheet 
            e.message = "%s {%s}" % (e.message, e.stylesheet)
            raise

from django.http import HttpResponse
def render_to_response(xslt, context, mimetype="text/html"):
    t = TransformerFile(settings.TRANSFORMS, xslt)
    return HttpResponse(t(context=context), mimetype="text/html")

class QuerySetTemplateElement(etree.XSLTExtension):
    def execute(self, context, self_node, input_node, output_parent):
        ctx = djangothread.context
        key = self_node.get('key')
        dest = self_node.get('dest')
        if '.' in key:
            qs = DjangoContextFunc(key, context=ctx)(None, 'pass')
        else:
            qs = ctx[key]
        for item in qs:
            ctx[dest] = item
            el = etree.Element('{%s}%s' % (DJANGO_NAMESPACE, dest))
            #self.apply_templates(context, el, output_parent)
            results = self.apply_templates(context, el)
            content = results[0]
            if isinstance(content, basestring):
                output_parent.text = content
            else:
                output_parent.append(content)
            #try:
                #self.process_children(context, output_parent)
            #except AttributeError, e:
                #raise RuntimeError('template not specified')
            del ctx[dest]

# End
