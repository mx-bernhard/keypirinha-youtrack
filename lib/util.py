from xml.dom import minidom


def get_as_xml(response: bytes):
    response = response.decode(encoding="utf-8", errors="strict")
    dom = minidom.parseString(response)
    return dom


def get_value(node, node_name):
    return next((child.childNodes[0].nodeValue for child in node.childNodes if child.nodeName == node_name), None)


def get_child_att_value(node, node_name, att_name):
    return next((child.getAttribute(att_name) for child in node.childNodes if child.nodeName == node_name), None)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self
