import urllib
from typing import Sequence, Union
from urllib import parse, request
import json


class SuggestionResult(object):
    def __init__(self, full_option: str, prefix: Union[str, None], suffix: Union[str, None], option: str, start: int,
                 end: int, description: str):
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


class Api:
    AUTH_HEADER: str = 'Authorization'
    TOKEN_PREFIX: str = 'Bearer '
    YOUTRACK_INTELLISENSE_ISSUE_API: str = '{base_url}/api/search/assist?'
    YOUTRACK_LIST_OF_ISSUES_API: str = '{base_url}/api/issues?'
    YOUTRACK_ISSUE: str = '{base_url}/issue/{id}'
    YOUTRACK_ISSUES: str = '{base_url}/issues/?'

    def __init__(self, api_token: str, youtrack_url: str, dbg, max_results: int):
        super().__init__()
        self.dbg = dbg
        self.api_token = api_token
        self.youtrack_url = youtrack_url
        self.max_results = max_results

    def open_url(self, http_url) -> str:
        req = request.Request(http_url)
        req.add_header(self.AUTH_HEADER, self.TOKEN_PREFIX + self.api_token)

        with request.urlopen(req) as resp:
            content = resp.read()
            return content

    def print(self, **kwargs):
        to_print = str.join(",", [key + " = \"" + str(value) + "\"" for key, value in kwargs.items()])
        self.dbg("[" + to_print + "]")

    def create_issues_url(self, filter):
        return self.YOUTRACK_ISSUES.format(base_url=self.youtrack_url) + parse.urlencode({'q': filter})

    def create_issue_url(self, id):
        return self.YOUTRACK_ISSUE.format(base_url=self.youtrack_url, id=id)

    def get_filters_url(self):
        return self.YOUTRACK_INTELLISENSE_ISSUE_API.format(base_url=self.youtrack_url) + parse.urlencode({
            'fields': 'suggestions(completionEnd,completionStart,description,option,prefix,suffix)'
        })

    def get_suggestions(self, actual_user_input: str) -> Sequence[SuggestionResult]:
        request_url = self.get_filters_url()
        self.print(requesturl=request_url)
        json_data = json.dumps({
            'caret': len(actual_user_input),
            'query': actual_user_input
        })
        post_data = json_data.encode('utf-8')
        suggestions_request = urllib.request.Request(request_url, data=post_data)
        suggestions_request.method = 'POST'
        self.add_common_headers(suggestions_request)
        response = self.read_response(suggestions_request)

        api_result_suggestions = self.parse_suggestions_response(response)
        return api_result_suggestions

    def add_common_headers(self, the_request):
        the_request.add_header(self.AUTH_HEADER, self.TOKEN_PREFIX + self.api_token)
        the_request.add_header('Content-Type', 'application/json')

    @staticmethod
    def read_response(request_to_read):
        with urllib.request.urlopen(request_to_read) as resp:
            response = json.loads(resp.read().decode('utf-8'))
            return response

    @staticmethod
    def parse_suggestions_response(response: dict) -> Sequence[SuggestionResult]:
        items = response['suggestions']

        result = []

        for item in items:
            prefix: str = item['prefix']
            suffix: str = item['suffix']
            option: str = item['option']
            description: str = item['description']
            start: int = int(item['completionStart'])
            end: int = int(item['completionEnd'])
            if option is None: continue
            res = str.join('', (item for item in [prefix, option, suffix] if item is not None))
            intelli_res = SuggestionResult(
                full_option=res,
                prefix=prefix,
                suffix=suffix,
                option=option,
                start=start,
                end=end,
                description=description)
            result.append(intelli_res)
        return result

    def parse_list_of_issues_result(self, response: str) -> Sequence[Issue]:
        issues: Sequence[Issue] = []
        for item in response:
            id_readable = item['idReadable']
            description = item['description']
            summary: str = item['summary'] if item['summary'] is not None else "--no summary--"
            issue = Issue(id=id_readable, summary=summary, description=description,
                          url=self.create_issue_url(id_readable))
            issues.append(issue)
        return issues

    def get_issues_matching_filter(self, actual_user_input: str) -> Sequence[Issue]:
        request_url: str = self.YOUTRACK_LIST_OF_ISSUES_API.format(base_url=self.youtrack_url)
        query_part: str = parse.urlencode({'query': actual_user_input, '$top': self.max_results + 1, 'fields': 'description,summary,idReadable'})
        request_url = request_url + query_part
        issues_request = urllib.request.Request(request_url)
        self.add_common_headers(issues_request)
        self.print(requesturl=request_url)
        json_response = self.read_response(issues_request)
        self.dbg("parsing issues result")
        issues = self.parse_list_of_issues_result(json_response)
        self.dbg(f'{len(issues)} issues retrieved.')
        return issues
