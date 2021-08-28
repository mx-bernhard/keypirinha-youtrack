from lib.api import Api


def do_nothing(*args):
    pass


api = Api('perm:YjNybmhhcmQ=.a2V5cGlyaW5oYUBob21l.fuW8XVvgPBgoWH3fueIijP1ewBSVGS', 'https://youtrack.jetbrains.com', do_nothing)


def suggestions():
    result = api.get_suggestions('statu')
    return result


def issues():
    result = api.get_issues_matching_filter('test')


issues()
