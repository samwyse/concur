#!/usr/bin/env python

"""xml2json.py  Convert XML to JSON

Relies on ElementTree for the XML parsing.  This is based on
pesterfish.py but uses a different XML->JSON mapping.
The XML->JSON mapping is described at
http://www.xml.com/pub/a/2006/05/31/converting-between-xml-and-json.html

Rewritten to a command line utility by Hay Kranen < github.com/hay > with
contributions from George Hamilton (gmh04) and Dan Brown (jdanbrown)

XML                              JSON
<e/>                             "e": null
<e>text</e>                      "e": "text"
<e name="value" />               "e": { "@name": "value" }
<e name="value">text</e>         "e": { "@name": "value", "#text": "text" }
<e> <a>text</a ><b>text</b> </e> "e": { "a": "text", "b": "text" }
<e> <a>text</a> <a>text</a> </e> "e": { "a": ["text", "text"] }
<e> text <a>text</a> </e>        "e": { "#text": "text", "a": "text" }

This is very similar to the mapping used for Yahoo Web Services
(http://developer.yahoo.com/common/json.html#xml).

This is a mess in that it is so unpredictable -- it requires lots of testing
(e.g. to see if values are lists or strings or dictionaries).  For use
in Python this could be vastly cleaner.  Think about whether the internal
form can be more self-consistent while maintaining good external
characteristics for the JSON.

Look at the Yahoo version closely to see how it works.  Maybe can adopt
that completely if it makes more sense...

R. White, 2006 November 6
"""

import json
import optparse
import sys

import xml.etree.cElementTree as ET

class UsingPrefix(object):
    
    def __init__(self, sep=':', default_namespace=None):
        import re
        self.sep = sep
        if default_namespace and default_namespace[0] == '{':
            default_namespace, tag = tuple(default_namespace[1:].rsplit("}", 1))
        self.default_namespace = default_namespace
        self.reserved = re.compile(r'^ns\d+$|' + re.escape(self.sep)).search
        self.namespace_count = 0
        self.namespace_map = {
            # "well-known" namespace prefixes
            "http://www.w3.org/XML/1998/namespace": "xml",
            "http://www.w3.org/1999/xhtml": "html",
            "http://www.w3.org/1999/02/22-rdf-syntax-ns#": "rdf",
            "http://schemas.xmlsoap.org/wsdl/": "wsdl",
            # xml schema
            "http://www.w3.org/2001/XMLSchema": "xs",
            "http://www.w3.org/2001/XMLSchema-instance": "xsi",
            # dublin core
            "http://purl.org/dc/elements/1.1/": "dc",
        }
        
    def register_namespace(prefix, uri):
        if self.reserved(prefix):
            raise ValueError("Prefix format reserved for internal use")
        for k, v in self.namespace_map.items():
            if k == uri or v == prefix:
                del self.namespace_map[k]
        self.namespace_map[uri] = prefix
        
    def encode(self, qname):
        if qname[0] == '{':
            uri, tag = tuple(qname[1:].rsplit("}", 1))
            if uri == self.default_namespace:
                return tag
            ns_map = self.namespace_map
            prefix = ns_map.get(uri)
            if prefix is None:
                prefix = "ns%d" % self.namespace_count
                ns_map[uri] = prefix
                self.namespace_count += 1
            qname = self.sep.join((prefix, tag))
        return qname
    
    def decode(self, tag):
        try:
            prefix, tag = tag.split(self.sep, 1)
        except ValueError:
            if self.default_namespace:
                return "{%s}%s" % (self.default_namespace, tag)
        for k, v in self.namespace_map.items():
            if v == prefix:
                uri = k
                break
        else:
            if self.default_namespace is None:
                return tag
            else:
                return "{%s}%s" % (self.default_namespace, tag)
        return "{%s}%s" % (uri, tag)

default_canonization = UsingPrefix()

def elem_to_internal(elem, strip=1, canonize=default_canonization):
    """Convert an Element into an internal dictionary (not JSON!)."""

    d = {}
    for key, value in list(elem.attrib.items()):
        d['@' + key] = value

    # loop over subelements to merge them
    for subelem in elem:
        v = elem_to_internal(subelem, strip=strip, canonize=canonize)
        tag = canonize.encode(subelem.tag)
        value = v[tag]
        try:
            # add to existing list for this tag
            d[tag].append(value)
        except AttributeError:
            # turn existing entry into a list
            d[tag] = [d[tag], value]
        except KeyError:
            # add a new non-list entry
            d[tag] = value
    text = elem.text
    tail = elem.tail
    if strip:
        # ignore leading and trailing whitespace
        if text:
            text = text.strip()
        if tail:
            tail = tail.strip()

    if tail:
        d['#tail'] = tail

    if d:
        # use #text element if other attributes exist
        if text:
            d["#text"] = text
    else:
        # text is the value if no attributes
        d = text or None
    return {canonize.encode(elem.tag): d}

def internal_to_elem(pfsh, factory=ET.Element, canonize=default_canonization):

    """Convert an internal dictionary (not JSON!) into an Element.

    Whatever Element implementation we could import will be
    used by default; if you want to use something else, pass the
    Element class as the factory parameter.
    """

    attribs = {}
    text = None
    tail = None
    sublist = []
    tag = list(pfsh.keys())
    if len(tag) != 1:
        raise ValueError("Illegal structure with multiple tags: %s" % tag)
    tag = tag[0]
    value = pfsh[tag]
    if isinstance(value, dict):
        for k, v in list(value.items()):
            if k[:1] == "@":
                attribs[k[1:]] = v
            elif k == "#text":
                text = v
            elif k == "#tail":
                tail = v
            elif isinstance(v, list):
                for v2 in v:
                    sublist.append(internal_to_elem({k: v2}, factory=factory, canonize=canonize))
            else:
                sublist.append(internal_to_elem({k: v}, factory=factory, canonize=canonize))
    else:
        text = value
    e = factory(canonize.decode(tag), attribs)
    for sub in sublist:
        e.append(sub)
    e.text = text
    e.tail = tail
    return e

def elem2json(elem, strip=1):
    """Convert an ElementTree or Element into a JSON string."""

    if hasattr(elem, 'getroot'):
        elem = elem.getroot()
    return json.dumps(elem_to_internal(elem, strip=strip))

def json2elem(json_data, factory=ET.Element):
    """Convert a JSON string into an Element.

    Whatever Element implementation we could import will be used by
    default; if you want to use something else, pass the Element class
    as the factory parameter.
    """

    return internal_to_elem(json.loads(json_data), factory)

def xml2json(xmlstring, strip=1):
    """Convert an XML string into a JSON string."""

    elem = ET.fromstring(xmlstring)
    return elem2json(elem, strip=strip)


def json2xml(json_data, factory=ET.Element):
    """Convert a JSON string into an XML string.

    Whatever Element implementation we could import will be used by
    default; if you want to use something else, pass the Element class
    as the factory parameter.
    """

    elem = internal_to_elem(json.loads(json_data), factory)
    return ET.tostring(elem)

def main():
    p = optparse.OptionParser(
        description='Converts XML to JSON or the other way around',
        prog='xml2json',
        usage='%prog -t xml2json -o file.json file.xml'
    )
    p.add_option('--type', '-t', help="'xml2json' or 'json2xml'")
    p.add_option('--out', '-o', help="Write to OUT instead of stdout")
    options, arguments = p.parse_args()

    if len(arguments) == 1:
        input = open(arguments[0]).read()
    else:
        p.print_help()
        sys.exit(-1)

    if (options.type == "xml2json"):
        out = xml2json(input, strip=0)
    else:
        out = json2xml(input)

    if (options.out):
        file = open(options.out, 'w')
        file.write(out)
        file.close()
    else:
        print(out)

if __name__ == "__main__":
    main()

