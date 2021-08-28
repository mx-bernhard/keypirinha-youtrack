from lib.api import Api


def do_nothing(*args):
    pass


api = Api('<token>', '<url>', do_nothing)


def suggestions():
    result = api.get_suggestions('statu')
    return result


def issues():
    result = api.get_issues_matching_filter('test')


issues()
