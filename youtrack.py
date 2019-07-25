import functools
import os
import shutil
import traceback
import urllib
import webbrowser
from enum import Enum
from urllib import parse
from urllib import request
from xml.dom import minidom

import keypirinha
import keypirinha as kp
import keypirinha_util as kpu

ICON_KEY_DEFAULT = "youtrack"

class YouTrackServer():
    AUTH_HEADER = 'Authorization'
    TOKEN_PREFIX = 'Bearer '
    KEYWORD_DEFAULT = "youtrack"
    NAME_DEFAULT = "YouTrack"
    LABEL_DEFAULT = "YouTrack"
    YOUTRACK_INTELLISENSE_ISSUE_API = '{base_url}/rest/issue/intellisense/?'
    YOUTRACK_LIST_OF_ISSUES_API = '{base_url}/rest/issue?'
    YOUTRACK_ISSUE = '{base_url}/issue/{id}'
    YOUTRACK_ISSUES = '{base_url}/issues/?'

    def __init__(self, plugin, name):
        self.reset()
        self.plugin = plugin
        self.name = name

    def reset(self):
        self.filter_icon = ICON_KEY_DEFAULT
        self.issues_icon = ICON_KEY_DEFAULT
        self.keyword = self.KEYWORD_DEFAULT
        self.api_token = ''
        self.youtrack_url = ''

    def dbg(self, text):
        self.plugin.dbg(text)

    def print(self, **kwargs):
        toPrint = str.join(",", [key + " = \"" + str(value) + "\"" for key, value in kwargs.items()])
        self.dbg("[" + toPrint + "]")

    def init_from_config(self, settings, section):
        self.dbg('init_from_config')
        if section.lower().startswith("server/"):
            self.youtrack_url = settings.get("base_url", section, None)
            self.api_token = settings.get("api_token", section, None)
            self.filter_label = settings.get("filter_label", section, self.LABEL_DEFAULT)
            self.issues_label = settings.get("issues_label", section, self.LABEL_DEFAULT)
            self.name = settings.get("name", section, self.NAME_DEFAULT)
            self.filter_icon = settings.get("filter_icon", section, ICON_KEY_DEFAULT)
            self.issues_icon = settings.get("issues_icon", section, ICON_KEY_DEFAULT)
            self.keyword = settings.get("keyword", section, self.KEYWORD_DEFAULT)

    def open_url(self, http_url, token):
        req = request.Request(http_url)
        req.add_header(self.AUTH_HEADER, self.TOKEN_PREFIX + token)

        with request.urlopen(req) as resp:
            content = resp.read()
            return content

    def ensureSpace(self, text, added):
        res = text
        if (added is not None):
            if (not text.endswith(" ")): res += " "
            return text + added

    def on_suggest(self, plugin, user_input, items_chain):
        """
        :type user_input: str
        """
        self.dbg('on_suggest')

        if not items_chain:
            return []

        initial_item = items_chain[0]
        def calc(category, next_category):
            if (next_category == plugin.ITEMCAT_SWITCH):
                return plugin.ITEMCAT_FILTER if category == plugin.ITEMCAT_ISSUES else plugin.ITEMCAT_ISSUES
            return next_category

        current_suggestion_type = functools.reduce(calc, [item.category() for item in items_chain])

        current_items = items_chain[1:len(items_chain)]
        suggestions = []
        actual_user_input = ""
        previous_effective_value = ""
        if (len(current_items) > 0):
            current_item = current_items[-1]
            previous_effective_value = kpu.kwargs_decode(current_item.data_bag())['effective_value']
            actual_user_input += previous_effective_value
        actual_user_input += user_input
        self.print(actual_user_input = actual_user_input, user_input=user_input)
        self.print(is_filter=current_suggestion_type == plugin.ITEMCAT_FILTER)
        if current_suggestion_type == plugin.ITEMCAT_FILTER:
            self.add_filter_suggestions(actual_user_input, plugin, suggestions)
        else:
            self.add_issues_matching_filter(actual_user_input, plugin, suggestions)

        suggestions.append(plugin.create_item(
            category=plugin.ITEMCAT_SWITCH,
            label="Switch ⇆",
            short_desc="Switch between filter suggestions and issue list",
            target="switch",
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.IGNORE,
            icon_handle=plugin._icons[self.filter_icon],
            loop_on_suggest=True,
            data_bag=kpu.kwargs_encode(url=self.create_issues_url(previous_effective_value),effective_value=previous_effective_value)))

        # avoid flooding YouTrack with too many unnecessary queries in
        # case user is still typing her search
        if plugin.should_terminate(plugin.idle_time):
            return []
        if initial_item.category() == plugin.ITEMCAT_SWITCH :
            return []
        return suggestions

    def add_filter_suggestions(self, actual_user_input, plugin, suggestions):
        api_result_suggestions = self.fetch_suggestions(actual_user_input, plugin)
        first = True
        for api_result_suggestion in api_result_suggestions:
            start = api_result_suggestion.start
            end = api_result_suggestion.end

            user_input_start_ = actual_user_input[:start]
            user_input_end_ = actual_user_input[end:]
            effective_value = user_input_start_ + api_result_suggestion.full_option + user_input_end_

            data_bag_encoded = kpu.kwargs_encode(url=self.create_issues_url(effective_value),
                                                 effective_value=effective_value)
            desc = api_result_suggestion.description + " | " + effective_value if first else api_result_suggestion.description
            first = False
            suggestions.append(plugin.create_item(
                category=plugin.ITEMCAT_FILTER,
                label=api_result_suggestion.full_option,
                short_desc=desc,
                target=kpu.kwargs_encode(server=self.name, label=api_result_suggestion.option),
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=plugin._icons[self.filter_icon],
                loop_on_suggest=True,
                data_bag=data_bag_encoded))
        if len(suggestions) == 0:
            suggestions.insert(0, plugin.create_item(
                category=plugin.ITEMCAT_FILTER,
                label=actual_user_input,
                short_desc=actual_user_input,
                target=actual_user_input,
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=plugin._icons[self.filter_icon],
                loop_on_suggest=True,
                data_bag=(kpu.kwargs_encode(url=self.create_issues_url(actual_user_input),
                                            effective_value=actual_user_input))))

    def fetch_suggestions(self, actual_user_input, plugin):
        requestUrl = self.YOUTRACK_INTELLISENSE_ISSUE_API.format(base_url=self.youtrack_url)
        filter = parse.urlencode({'filter': actual_user_input})
        requestUrl = requestUrl + filter
        self.print(requesturl=requestUrl)
        content = self.open_url(requestUrl, self.api_token)
        api_result_suggestions = self.youtrack_intellisense_legacy(plugin, content)
        return api_result_suggestions

    def create_issues_url(self, filter):
        return self.YOUTRACK_ISSUES.format(base_url=self.youtrack_url) + parse.urlencode({'q': filter})

    def create_issue_url(self, id):
        return self.YOUTRACK_ISSUE.format(base_url=self.youtrack_url, id=id)

    def get_value(self, node, node_name):
        return next((child.childNodes[0].nodeValue for child in node.childNodes if child.nodeName == node_name), None)

    def get_child_att_value(self, node, node_name, att_name):
        return next((child.getAttribute(att_name) for child in node.childNodes if child.nodeName == node_name), None)

    def youtrack_intellisense_legacy(self, plugin, response):
        """
        There is no non-legacy yet (YouTrack 2019.2) but already announced that it will be discontinued
        once everything has been published under the new api.
        :param response:
        :return:
        """
        try:
            dom = self.get_as_xml(response)
            if (dom.documentElement.nodeName != 'IntelliSense'): return []
            items = [itemOrRecentItem
                     for suggestOrRecent in dom.documentElement.childNodes
                     for itemOrRecentItem in suggestOrRecent.childNodes
                     if isinstance(itemOrRecentItem, minidom.Element) and itemOrRecentItem.nodeName in ['item','recentItem']]
            list = []

            for item in items:
                prefix = self.get_value(item, 'prefix')
                suffix = self.get_value(item, 'suffix')
                option = self.get_value(item, 'option')
                description = self.get_value(item, 'description')
                start = int(self.get_child_att_value(item, 'completion', 'start'))
                end = int(self.get_child_att_value(item, 'completion', 'end'))
                if option is None: continue
                res = option
                if suffix is not None: res = res + suffix
                if prefix is not None: res = prefix + res
                list.append(AttrDict({'full_option': res, 'prefix': prefix, 'suffix': suffix, 'option': option,'start':start,'end':end,'description':description}))
            return list
        except Exception as e:
            self.warn("Failed to parse response.")
            traceback.print_exc()
            return []

    def get_as_xml(self, response):
        response = response.decode(encoding="utf-8", errors="strict")
        dom = minidom.parseString(response)
        return dom

    def add_issues_matching_filter(self, actual_user_input, plugin, suggestions):
        self.dbg("add_issues_matching_filter for " + actual_user_input)
        requestUrl = self.YOUTRACK_LIST_OF_ISSUES_API.format(base_url=self.youtrack_url)
        filter = parse.urlencode({'filter': actual_user_input})
        requestUrl = requestUrl + filter
        self.print(requesturl=requestUrl)
        content = self.open_url(requestUrl, self.api_token)
        api_result_suggestions = self.parse_list_of_issues_result_legacy(plugin, content)
        for res in api_result_suggestions:
            suggestions.append(res)
        suggestions.insert(0, plugin.create_item(
            category=plugin.ITEMCAT_ISSUES,
            label=actual_user_input,
            short_desc=actual_user_input,
            target=actual_user_input,
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.NOARGS,
            icon_handle=plugin._icons[self.issues_icon],
            loop_on_suggest=True,
            data_bag=(kpu.kwargs_encode(url=self.create_issues_url(actual_user_input),
                                        effective_value=actual_user_input))))


    def parse_list_of_issues_result_legacy(self, plugin, response):
        try:
            dom = self.get_as_xml(response)
            if (dom.documentElement.nodeName != 'issueCompacts'): return []
            self.dbg("parsing issues result")
            items = [issue for issue in dom.documentElement.childNodes
                     if isinstance(issue, minidom.Element) and issue.nodeName == 'issue']
            suggestions = []
            for item in items:
                id = item.getAttribute('id')
                summary = self.extract_field_value('summary', "--no summary--", item)
                description = self.extract_field_value('description', None, item)
                self.print(id=id,summary=summary)
                suggestions.append(plugin.create_item(category=plugin.ITEMCAT_ISSUES,
                label=summary,
                short_desc=id + (" ▶ " + description if description is not None else ""),
                target=id,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=plugin._icons[self.issues_icon],
                loop_on_suggest=False,
                data_bag=(kpu.kwargs_encode(url=self.create_issue_url(id)))))
            return suggestions
        except Exception as e:
            plugin.warn("Failed to parse response.")
            traceback.print_exc()
            return []

    def extract_field_value(self, field_name, fallback, item):
        return next((self.get_value(fieldNode, "value") for fieldNode in item.childNodes if isinstance(fieldNode,
                                                                                                       minidom.Element) and fieldNode.nodeName == 'field' and fieldNode.getAttribute(
            'name') == field_name), fallback)


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self



class YouTrack(kp.Plugin):
    """
    A plugin for YouTrack search functionality.
    """

    ACTION_BROWSE = "browse"
    ACTION_COPY_RESULT = "copy_result"
    ACTION_COPY_URL = "copy_url"

    CONFIG_SECTION_MAIN = "main"
    DEFAULT_IDLE_TIME = 0.25

    ITEMCAT_FILTER = kp.ItemCategory.USER_BASE + 1
    ITEMCAT_ISSUES = kp.ItemCategory.USER_BASE + 2
    ITEMCAT_SWITCH = kp.ItemCategory.USER_BASE + 3
    RES_ICON_PATH = 'res://{package}/icons/icon_{name}.png'
    RES_ICON_CONFIG_PATH = 'youtrack/icon_{name}.png'
    CACHE_ICON_CONFIG_PATH = 'cache://youtrack/icon_{name}.png'

    def __init__(self):
        self.dbg('__init__')
        super().__init__()
        self._debug = False
        self._icons = {}

    def __del__(self):
        self.dbg('__del__')

    def on_start(self):
        self.dbg('on_start')
        self._init_actions()
        self._read_config()
        self._load_icons()

    def _read_config(self):
        settings = self.load_settings()
        self.idle_time = settings.get_float(
            "idle_time", self.CONFIG_SECTION_MAIN,
            fallback=self.DEFAULT_IDLE_TIME, min=0.25, max=3)


        self.servers = {}

        for section in settings.sections():
            if section.lower().startswith("server/"):
                server_label = section[len("server/"):].strip()
            else:
                continue

            server_enabled = settings.get_bool("enable", section, fallback=True)
            if (not server_enabled):
                continue
            server_name = server_label.lower()

            if not server_name:
                self.warn("Skipping empty server name in config section [{}].".format(section))
                continue
            if server_name in self.servers:
                self.warn(
                    ('YouTrack server "{}" declared more than once. ' +
                    'Ignoring subsequent declarations').format(server_label))
                continue

            try:
                server_ = YouTrackServer(self, server_name)
                server_.init_from_config(settings, section)
                self.servers[server_name] = server_
            except ValueError as exc:
                self.warn(str(exc))
                self.warn("Server [{}] skipped due to error".format(section))
                continue


    def _init_actions(self):
        self.dbg('_init_actions')
        actions = [
            self.create_action(
                name=self.ACTION_BROWSE,
                label='Open in browser',
                short_desc='Open in browser, thus showing issues matching the filter.'),
            self.create_action(
                name=self.ACTION_COPY_URL,
                label="Copy url",
                short_desc="Copy issues url to clipboard"),
            self.create_action(
                name=self.ACTION_COPY_RESULT,
                label="Copy filter",
                short_desc="Copy issues filter to clipboard"),
        ]
        self.actions_names = []
        for act in actions:
            self.actions_names.append(act.name())
        self.set_actions(self.ITEMCAT_FILTER, actions)
        self.set_actions(self.ITEMCAT_ISSUES, actions)

    def on_catalog(self):
        self.dbg('on_catalog')

        catalog = []
        for server_name, server in self.servers.items():
            self.set_default_icon(self._icons[ICON_KEY_DEFAULT])
            self.info("Creating catalog entry for server issues_label={issues_label}, filter_label={filter_label}, name={name}, server_name={server_name}, issues_icon={issues_icon}, filter_icon={filter_icon}".format(
                filter_icon=server.filter_icon,
                issues_icon=server.issues_icon,
                issues_label=server.issues_label,
                filter_label=server.filter_label,
                server_name=server_name,
                name=server.name))
            str.join(",", self._icons)
            catalog.append(self.create_item(
                category=self.ITEMCAT_FILTER,
                label=server.filter_label,
                short_desc=server.name,
                target=kpu.kwargs_encode(server=server_name),
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self._icons[server.filter_icon]))
            catalog.append(self.create_item(
                category=self.ITEMCAT_ISSUES,
                label=server.issues_label,
                short_desc=server.name,
                target=kpu.kwargs_encode(server=server_name),
                args_hint=kp.ItemArgsHint.REQUIRED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self._icons[server.issues_icon]))
        self.set_catalog(catalog)

    def on_suggest(self, user_input, items_chain):
        if not items_chain or items_chain[0].category() not in [self.ITEMCAT_FILTER, self.ITEMCAT_ISSUES, self.ITEMCAT_SWITCH]:
            return
        current_item = items_chain[0]
        target_props = kpu.kwargs_decode(current_item.target())
        server_name = target_props['server']

        try:
            server = self.servers[server_name]
        except KeyError:
            self.warn('Item definition not found in current config: "{}"'.format(server_name))
            return

        suggestions = [current_item.clone()]

        # default item
        suggestions[0].set_args(user_input)

        # avoid doing unnecessary network requests in case user is still typing
        if self.should_terminate(self.idle_time):
            return

        server_suggestions = []

        try:
            server_suggestions = server.on_suggest(self, user_input, items_chain)
            self.dbg("len=" + str(len(server_suggestions)))
            if self.should_terminate():
                return
        except urllib.error.HTTPError as exc:
            server_suggestions.append(self.create_error_item(
                label=user_input, short_desc=str(exc)))
        except Exception as exc:
            server_suggestions.append(self.create_error_item(
                label=user_input, short_desc="Error: " + str(exc)))
            traceback.print_exc()

        if not server_suggestions:  # change default item
            server_suggestions[0].set_short_desc("No suggestions found (default action: open browser)")

        self.set_suggestions(server_suggestions, kp.Match.ANY, kp.Sort.NONE)


    def on_execute(self, item, action):
        self.dbg('on_execute')

        if not item or not item.data_bag():
            return
        data_bag = kpu.kwargs_decode(item.data_bag())
        if not data_bag:
            return

        # ACTION_KEY_DEFAULT
        if not action or action.name() == self.ACTION_BROWSE:
            webbrowser.open(data_bag['url'])
        elif action.name() == self.ACTION_COPY_URL:
            kpu.set_clipboard(data_bag['url'])
        elif action.name() == self.ACTION_COPY_RESULT and item.category() != self.ITEMCAT_ISSUES:
            kpu.set_clipboard(data_bag['effective_value'])

    def on_events(self, flags):
        self.dbg('on_events')
        if flags & kp.Events.PACKCONFIG:
            self.info("Configuration changed, rebuilding catalog...")
            self._read_config()
            self.on_catalog()

    def _load_icons(self):
        for key, icon in self._icons.items():
            icon.free()
        self._icons.clear()
        self._icons[ICON_KEY_DEFAULT] = self._load_resource_icon(ICON_KEY_DEFAULT)
        for server in self.servers.values():
            self.add_if_missing(server.issues_icon)
            self.add_if_missing(server.filter_icon)

    def add_if_missing(self, icon):
        if not icon in self._icons:
            self.dbg(str.format("loading icon {0}", icon))
            self._icons[icon] = self._load_resource_icon(name=icon)

    def _load_resource_icon(self, name):
        full_name = self.package_full_name()
        package_path = self.RES_ICON_PATH.format(package=full_name, name=name)
        config_icon_path = os.path.join(keypirinha.user_config_dir(), self.RES_ICON_CONFIG_PATH.format(name=name))
        cache_dir = keypirinha.package_cache_dir(full_name)
        # create package dir in cache dir
        try: os.makedirs(cache_dir)
        except: pass

        # copy to cache so that cache:// works
        try:
            shutil.copy(config_icon_path, cache_dir)
            package_path = self.CACHE_ICON_CONFIG_PATH.format(package=full_name,name=name)
        except Exception as e:
            self.dbg("Could not copy {file} to cache {cache} ".format(file=config_icon_path,cache=cache_dir) )

        return self.load_icon([config_icon_path, package_path])
