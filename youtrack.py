import os
import shutil
import traceback
import urllib
import webbrowser
from typing import List

import keypirinha
import keypirinha as kp
import keypirinha_util as kpu

from .youtrack_server import YouTrackServer, ICON_KEY_DEFAULT


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
        self._debug = True
        self._icons = {}

    def __del__(self):
        self.dbg('__del__')

    def on_start(self):
        self.dbg('on_start')
        self._init_actions()
        self._read_config()
        self._load_icons()

    def _read_config(self):
        kp_settings = keypirinha.settings()

        settings = self.load_settings()
        app_max_results = kp_settings.get_int("max_results", "gui", 100)
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
            max_results = settings.get_int("max_results", section, app_max_results)
            max_search_results = max_results
            if max_results > app_max_results:
                max_results = app_max_results
            if max_search_results + 2 > app_max_results:
                max_search_results = app_max_results - 2
            try:
                server_ = YouTrackServer(self, server_name, max_results, max_search_results)
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
            self.info("Creating catalog entry for server name={name}, issues_label={issues_label}, filter_label={filter_label}, server_name={server_name}, issues_icon={issues_icon}, filter_icon={filter_icon},filter={filter}".format(
                filter_icon=server.filter_icon,
                issues_icon=server.issues_icon,
                issues_label=server.issues_label,
                filter_label=server.filter_label,
                server_name=server_name,
                name=server.name,
                filter=server.filter_prefix))
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

    def on_suggest(self, user_input: str, items_chain: List):
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
            server_suggestions = server.on_suggest(user_input, items_chain)
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
        if flags & kp.Events.PACKCONFIG or flags & kp.Events.APPCONFIG:
            self.info("Configuration changed, rebuilding catalog...")
            self._read_config()
            self._load_icons()
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
