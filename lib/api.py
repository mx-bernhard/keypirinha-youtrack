from typing import Sequence, Callable, Union
from urllib import parse, request
from xml.dom import minidom
from xml.dom.minidom import Element

from .util import get_as_xml, get_value, get_child_att_value

class IntellisenseResult(object):
    def __init__(self, full_option: str, prefix: Union[str, None], suffix: Union[str,None], option: str, start: int, end: int, description: str):
        self.description = description
        self.end = end
        self.start = start
        self.option = option
        self.suffix = suffix
        self.prefix = prefix
        self.full_option = full_option

class Issue(object):
    def __init__(self, id: str, summary: str, description: str, url: str):
        self.url = url
        self.id = id
        self.summary = summary
        self.description = description

class Api():
    AUTH_HEADER: str = 'Authorization'
    TOKEN_PREFIX: str = 'Bearer '
    YOUTRACK_INTELLISENSE_ISSUE_API: str = '{base_url}/rest/issue/intellisense/?'
    YOUTRACK_LIST_OF_ISSUES_API: str = '{base_url}/rest/issue?'
    YOUTRACK_ISSUE: str = '{base_url}/issue/{id}'
    YOUTRACK_ISSUES: str = '{base_url}/issues/?'

    def __init__(self, api_token: str, youtrack_url: str, dbg):
        super().__init__()
        self.dbg = dbg
        self.api_token = api_token
        self.youtrack_url = youtrack_url

    def open_url(self, http_url) -> str:
        req = request.Request(http_url)
        req.add_header(self.AUTH_HEADER, self.TOKEN_PREFIX + self.api_token)
    
        with request.urlopen(req) as resp:
            content = resp.read()
            return content

    def print(self, **kwargs):
        toPrint = str.join(",", [key + " = \"" + str(value) + "\"" for key, value in kwargs.items()])
        self.dbg("[" + toPrint + "]")

    def create_issues_url(self, filter):
        return self.YOUTRACK_ISSUES.format(base_url=self.youtrack_url) + parse.urlencode({'q': filter})

    def create_issue_url(self, id):
        return self.YOUTRACK_ISSUE.format(base_url=self.youtrack_url, id=id)

    def get_intellisense_suggestions(self, actual_user_input: str) -> Sequence[IntellisenseResult]:
        """
        There is no non-legacy yet (YouTrack 2019.2) but already announced that it will be discontinued
        once everything has been published under the new api.
        """
        requestUrl = self.YOUTRACK_INTELLISENSE_ISSUE_API.format(base_url=self.youtrack_url)
        filter = parse.urlencode({'filter': actual_user_input})
        requestUrl = requestUrl + filter
        self.print(requesturl=requestUrl)
        content: bytes = self.open_url(requestUrl)
        api_result_suggestions = self.parse_intellisense_suggestions(content)
        return api_result_suggestions

    def parse_intellisense_suggestions(self, response: bytes) -> Sequence[IntellisenseResult]:
        dom = get_as_xml(response)
        if (dom.documentElement.nodeName != 'IntelliSense'): return []
        items = [itemOrRecentItem
                 for suggestOrRecent in dom.documentElement.childNodes
                 for itemOrRecentItem in suggestOrRecent.childNodes
                 if isinstance(itemOrRecentItem, Element) and itemOrRecentItem.nodeName in ['item', 'recentItem']]
        result = []

        for item in items:
            prefix: str = get_value(item, 'prefix')
            suffix: str = get_value(item, 'suffix')
            option: str = get_value(item, 'option')
            description: str = get_value(item, 'description')
            start: int = int(get_child_att_value(item, 'completion', 'start'))
            end: int = int(get_child_att_value(item, 'completion', 'end'))
            if option is None: continue
            res = str.join('', (item for item in [prefix, option, suffix] if item is not None))
            intelliRes = IntellisenseResult(
                full_option=res,
                prefix=prefix,
                suffix=suffix,
                option=option,
                start=start,
                end=end,
                description=description)
            result.append(intelliRes)
        return result

    def parse_list_of_issues_result(self, response: str) -> Sequence[Issue]:
        dom = get_as_xml(response)
        if (dom.documentElement.nodeName != 'issueCompacts'): return []
        items = [issue for issue in dom.documentElement.childNodes
                 if isinstance(issue, minidom.Element) and issue.nodeName == 'issue']
        issues: Sequence[Issue] = []
        for item in items:
            self.print(item=str(item))
            id = item.getAttribute('id')
            description = self.extract_field_value('description', "", item)
            summary: str = self.extract_field_value('summary', "--no summary--", item)
            issue = Issue(id=id, summary=summary, description=description, url=self.create_issue_url(id))
            issues.append(issue)
            self.print(id=id, summary=summary,url=issue.url)
        return issues

    
    def extract_field_value(self, field_name: str, fallback: str, item) -> str:
        return next((get_value(fieldNode, "value")
                     for fieldNode in item.childNodes
                     if isinstance(fieldNode, minidom.Element) and fieldNode.nodeName == 'field' and fieldNode.getAttribute(
            'name') == field_name),
                    fallback)

    def get_issues_matching_filter(self, actual_user_input: str) -> Sequence[Issue]:
        requestUrl: str = self.YOUTRACK_LIST_OF_ISSUES_API.format(base_url=self.youtrack_url)
        filter: str = parse.urlencode({'filter': actual_user_input})
        requestUrl = requestUrl + filter
        self.print(requesturl=requestUrl)
        content: str = self.open_url(requestUrl)
        self.dbg("parsing issues result")
        issues = self.parse_list_of_issues_result(content)
        return issues

