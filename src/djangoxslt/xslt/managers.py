# Model Managers.

from django.db import models
from django.template import Template
from django.template import Context
import types

class XPathRenderer(object):
    """This is an interface for objects that have __xml__"""
    def __xml__(self, *args):
        return ""

def xmlify(qs, use_values=True, **kwargs):
    """XML serializer for queryset qs using the template described in kwargs.

    This operates a little like django values (indeed it uses django
    values if use_values is True) but allows you to specify the
    resulting XML name.

    So this call:

       xmlify(qs, **{
          "xml_field_name": "django_queryset__model__accessor",
          "other_xml_field": "django_queryset__deep__reference__field",
          "xml_field": "django_queryset__model__field|upper",
          }).__xml__()

    produces:

     [ "xml_field_name='value from django_queryset.model.accessor row 1'
         other_xml_field='value from django_queryset.deep.reference.field row 1'
         xml_field='value to caps from django_queryset.model.field row 1'",

       "xml_field_name='value from django_queryset.model.accessor row 2'
         other_xml_field='value from django_queryset.deep.reference.field row 2'
         xml_field='value to caps from django_queryset.model.field row 2'",
       .
       .
       .
       ]

    Any valid django template may be used on the django field name.

    If use_values is False then a normal queryset is used instead of a
    values queryset.

    The best way to use this with XSLT is to attach xmlify-ed
    querysets to a request context and then call render_to_response
    with the context object. 'xdjango:contextobject()' can then
    retrieve the queryset.
    """
    captured_qs = qs
    class XML(XPathRenderer):
        def __init__(self):
            self._cached = None

        def __xml__(self, *args):
            if self._cached == None:
                self._cached = self.__evalxml__(*args)
            return self._cached

        def __evalxml__(self, *args):
            template_list = [(name, Template('{{%s}}' % value)) \
                                 for name,value in kwargs.iteritems()]
            django_fields = [template.split("|")[0].split(".")[0] for template in kwargs.values()]

            # Do the query that gets the data to XML
            # Ordinarily we use 'values' but we can use an ordinary query if necessary
            rows = []
            text_fields = []
            if use_values:
                rows = captured_qs.values(*django_fields)
            else:
                for row in captured_qs:
                    row_result = {}
                    if django_fields:
                        for field in django_fields:
                            value = getattr(row, field)
                            row_result[field] = value() if isinstance(value, types.MethodType) else value
                            if getattr(value, 'is_text', False):
                                text_fields.append(field)
                    else:
                        row_result = row.__xml__()

                    rows += [row_result]

            # Make a nice list of template outputed rows
            from lxml import etree
            xmlname = captured_qs.model.__name__
            xmlroot = etree.Element("%ss" % xmlname.lower())
            #import pdb
            #pdb.set_trace()
            for record in rows:
                c = Context()
                c.update(record)
                child = etree.SubElement(xmlroot, xmlname.lower())
                if template_list:
                    for name,template in template_list:
                        if name in text_fields:
                            elem = etree.SubElement(child, name)
                            elem.text = template.render(c)
                        else:
                            child.attrib[name] = template.render(c)
                else:
                    parsed = etree.XML(record)
                    elem = child.append(parsed)

            return xmlroot
                
    return XML()

def xmlifyiter(iterator, name, **kwargs):
    """XML serializer to elements of 'name'.

    The kwargs specifies the XML -> iterator values mapping.  

    At the moment the iterator values are expected to be dictionary
    type objects.

    The kwargs specifies:

      an xml result attribute name = "an iterator value object dictionary key"

    for example:

      xmlifyiter(iteratorobject, "Iterable", name="username", age="age")

    =>
      <iterables>
         <iterable name="nicferrier" age="40"/>
         <iterable name="neebone" age="29"/>
         <iterable name="iamseb" age="31"/>
      </iterables>
    """
    captured_iter = iterator
    captured_element_name = name
    class XML(XPathRenderer):
        def __init__(self):
            self._cached = None

        def __xml__(self, *args):
            if self._cached == None:
                self._cached = self.__evalxml__(*args)
            return self._cached

        def __evalxml__(self, *args):
            template_list = [(name, Template('{{%s}}' % value)) \
                                 for name,value in kwargs.iteritems()]
            dict_keys = [template.split("|")[0].split(".")[0] for template in kwargs.values()]

            rows = []
            text_fields = []
            for row in captured_iter:
                row_result = {}
                for field in dict_keys:
                    value = row.get(field)
                    row_result[field] = value
                    if getattr(value, 'is_text', False):
                        text_fields.append(field)
                rows += [row_result]

            # Make a nice list of template outputed rows
            from lxml import etree
            xmlname = captured_element_name
            xmlroot = etree.Element("%ss" % xmlname.lower())
            #import pdb
            #pdb.set_trace()
            for record in rows:
                c = Context()
                c.update(record)
                child = etree.SubElement(xmlroot, xmlname.lower())
                for name,template in template_list:
                    if name in text_fields:
                        elem = etree.SubElement(child, name)
                        elem.text = template.render(c)
                    else:
                        child.attrib[name] = template.render(c)
            return xmlroot
                
    return XML()


from django.db.models.query import QuerySet
class XmlQuerySet(QuerySet):
    """A queryset that does xmlifying"""
    def xml(self, **kwargs):
        return xmlify(self, use_values=getattr(self, "use_values", True), **kwargs)

    def xml_objects(self, **kwargs):
        """Don't do a values query. Use the full object instead."""
        return xmlify(self, use_values=getattr(self, "use_values", False), **kwargs)


def monkey_qs(qs, use_values=True):
    """Clone the queryset adding an 'xml' method.

    The 'xml' method works like 'xmlify', pass kwargs for rendering
    arguments and it returns an object which supports the __xml__
    protocol.

    The objects returned from the 'xml' object attached with
    'monkey_qs' are also querysets which can be further cloned.

    For example:

      qs1 = Person.objects.filter(user__last_name="smith")
      qs2 = monkey_qs(qs1)
      qs3 = qs2.xml(username="user__username", firstname="user__firstname")
      qs4 = qs3.filter(age__gte=18)
      xmldata = qs4.__xml__()
    """
    capturedclone = qs._clone

    def baseclone(xml_closure):
        newclone = capturedclone()
        newclone.__xml__ = lambda *args: xml_closure.__xml__(*args)
        newclone._clone = lambda: baseclone(xml_closure)
        return newclone

    def adapt(*args, **kwargs):
        newclone = capturedclone(*args, **kwargs)
        xml_protocol_obj = xmlify(qs, use_values=use_values, **kwargs)
        newclone.__dict__["__xml__"] = lambda *args: xml_protocol_obj.__xml__(*args)
        newclone.__dict__["_clone"] = lambda: baseclone(xml_protocol_obj)
        return newclone

    def xmlclone(selfarg, *args, **kwargs):
        newclone = capturedclone(*args, **kwargs)
        newclone.__dict__["xml"] = lambda *args,**kwargs: adapt(*args, **kwargs)
        newclone.__dict__["use_values"] = use_values
        newclone.__dict__["_clone"] = types.MethodType(xmlclone, selfarg, selfarg.__class__)
        return newclone
    return xmlclone(qs)


class RenderingManager(models.Manager):
    """Use monkey_qs to decorate the queryset.

    This makes querysets that use values calls by default. To get a
    queryset that will render without using values create the manager
    with:

      use_values=False
    """
    def __init__(self, use_values=True):
        models.Manager.__init__(self)
        self.use_values = use_values

    def get_query_set(self):
        qs = super(RenderingManager, self).get_query_set()
        return monkey_qs(qs)

# End
