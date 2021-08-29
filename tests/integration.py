import sys

from lib.api import Api


def do_nothing(*args):
    pass

token = sys.argv[1]
url = sys.argv[2]
api = Api(token, url, do_nothing, max_results=100)


def suggestions():
    result = api.get_suggestions('statu')
    return result


def issues():
    result = api.get_issues_matching_filter('test')


issues()
