import functools
from enum import Enum
from typing import Sequence

import keypirinha as kp
import keypirinha_util as kpu

from .lib.api import Api
from .lib.legacy_api import Api as LegacyApi


class SuggestionMode(Enum):
    Filter = 0,
    Issues = 1


ICON_KEY_DEFAULT = "youtrack"


class YouTrackServer():
    NAME_DEFAULT: str = "YouTrack"
    LABEL_DEFAULT: str = "YouTrack"
    LEGACY_API_DEFAULT: bool = False

    suggestion_mode: SuggestionMode = SuggestionMode.Filter

    def __init__(self, plugin, name: str, max_results: int):
        self.reset()
        self.plugin = plugin
        self.name = name
        self.max_results = max_results

        self.filter_icon = ICON_KEY_DEFAULT
        self.issues_icon = ICON_KEY_DEFAULT
        self.filter_label = self.LABEL_DEFAULT
        self.issues_label = self.LABEL_DEFAULT
        self.show_filter_history_entry = False
        self.show_issues_history_entry = False
        self.show_filter_entry = True
        self.show_issues_entry = True

    def reset(self):
        self.filter_icon = ICON_KEY_DEFAULT
        self.issues_icon = ICON_KEY_DEFAULT
        self.max_results = 100
        self.api = None
        self.filter_prefix = ""

    def dbg(self, text):
        self.plugin.dbg(text)

    def print(self, **kwargs):
        to_print = str.join(",", [key + " = \"" + str(value) + "\"" for key, value in kwargs.items()])
        self.dbg("[" + to_print + "]")

    def init_from_config(self, settings, section):
        self.dbg('init_from_config')
        if section.lower().startswith("server/"):
            youtrack_url = settings.get("base_url", section, None)
            api_token = settings.get("api_token", section, None)
            self.legacy_api = settings.get("legacy_api", section, False)
            self.show_filter_history_entry = settings.get_bool("show_filter_history_entry", section, False)
            self.show_issues_history_entry = settings.get_bool("show_issues_history_entry", section, False)
            self.show_filter_entry = settings.get_bool("show_filter_entry", section, True)
            self.show_issues_entry = settings.get_bool("show_issues_entry", section, True)
            always_visible_issues_items = 1 + (1 if self.show_issues_history_entry else 0) + (
                1 if self.show_issues_entry else 0)
            actual_max_results = self.max_results - always_visible_issues_items
            self.api = \
                Api(api_token=api_token, youtrack_url=youtrack_url, dbg=self.dbg, max_results=actual_max_results) \
                    if not self.legacy_api \
                    else LegacyApi(api_token=api_token, youtrack_url=youtrack_url, dbg=self.dbg,
                                   max_results=actual_max_results)
            self.filter_label = settings.get("filter_label", section, self.LABEL_DEFAULT)
            self.issues_label = settings.get("issues_label", section, self.LABEL_DEFAULT)
            self.filter_icon = settings.get("filter_icon", section, ICON_KEY_DEFAULT)
            self.issues_icon = settings.get("issues_icon", section, ICON_KEY_DEFAULT)
            dont_append = settings.get_bool("filter_dont_append_whitespace", section, False)
            self.filter_prefix = settings.get("filter", section, "") + ("" if dont_append else " ")
            self.print(filter_prefix=self.filter_prefix, issues_label=self.issues_label)

    def on_suggest(self, user_input: str, items_chain: Sequence):
        self.dbg('on_suggest')

        if not items_chain:
            return []

        initial_item = items_chain[0]
        current_suggestion_type: SuggestionMode = self.get_current_suggestion_mode(items_chain)
        suggestions = []
        actual_user_input = self.filter_prefix if len(items_chain) == 1 else ""
        try:
            current_item = items_chain[-1]
            decoded = kpu.kwargs_decode(current_item.data_bag())
            previous_effective_value = str.rstrip(decoded['effective_value'])
        except:
            previous_effective_value = ""
        self.print(previous_effective_value=previous_effective_value, user_input=user_input)
        actual_user_input += str.strip(previous_effective_value) + ' '
        actual_user_input += str.strip(user_input)
        actual_user_input = str.strip(actual_user_input)
        self.print(actual_user_input=actual_user_input, user_input=user_input)
        self.print(is_filter=str(current_suggestion_type))
        if current_suggestion_type == SuggestionMode.Filter:
            self.add_filter_suggestions(actual_user_input, suggestions)
        else:
            self.add_issues_matching_filter(actual_user_input, suggestions)

        suggestions.append(self.plugin.create_item(
            category=self.plugin.ITEMCAT_SWITCH,
            label="Switch ⇆",
            short_desc="Switch between filter suggestions and issue list",
            target="switch",
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.IGNORE,
            icon_handle=self.plugin._icons[self.filter_icon],
            loop_on_suggest=True,
            data_bag=kpu.kwargs_encode(url=self.api.create_issues_url(previous_effective_value),
                                       effective_value=previous_effective_value)))

        # avoid flooding YouTrack with too many unnecessary queries in
        # case user is still typing her search
        if self.plugin.should_terminate(self.plugin.idle_time):
            return []
        if initial_item.category() == self.plugin.ITEMCAT_SWITCH:
            return []
        return suggestions

    def get_current_suggestion_mode(self, current_items):
        def calc(prev_category, next_category):
            if next_category == self.plugin.ITEMCAT_SWITCH:
                return self.plugin.ITEMCAT_FILTER if prev_category == self.plugin.ITEMCAT_ISSUES else self.plugin.ITEMCAT_ISSUES
            return next_category

        reduced = functools.reduce(calc, [item.category() for item in current_items], self.plugin.ITEMCAT_FILTER)
        return SuggestionMode.Filter if reduced == self.plugin.ITEMCAT_FILTER else SuggestionMode.Issues

    def add_filter_suggestions(self, actual_user_input, suggestions) -> None:
        self.dbg(f'actual_user_input: {actual_user_input}')
        api_result_suggestions = self.api.get_suggestions(actual_user_input)
        # the first displays the current filter so far
        first = True
        for api_result_suggestion in api_result_suggestions:
            start = api_result_suggestion.start
            end = api_result_suggestion.end

            user_input_start_ = actual_user_input[:start]
            user_input_end_ = actual_user_input[end:]
            effective_value = user_input_start_ + api_result_suggestion.full_option + user_input_end_

            data_bag_encoded = kpu.kwargs_encode(url=self.api.create_issues_url(effective_value),
                                                 effective_value=effective_value)
            desc = api_result_suggestion.description + " | " + effective_value if first else api_result_suggestion.description
            first = False
            suggestions.append(self.plugin.create_item(
                category=self.plugin.ITEMCAT_FILTER,
                label=api_result_suggestion.full_option,
                short_desc=desc,
                target=kpu.kwargs_encode(server=self.name, label=api_result_suggestion.option),
                args_hint=kp.ItemArgsHint.ACCEPTED,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self.plugin._icons[self.filter_icon],
                loop_on_suggest=True,
                data_bag=data_bag_encoded))
        if self.show_filter_history_entry:
            self.add_filter_entry(actual_user_input, suggestions, True)
        if self.show_filter_entry:
            self.add_filter_entry(actual_user_input, suggestions, False)

    def add_filter_entry(self, actual_user_input, suggestions, is_history):
        suggestions.insert(0, self.plugin.create_item(
            category=self.plugin.ITEMCAT_FILTER,
            # only history items' label is searched, so make it contain something useful
            label=self.filter_label + " ▶ " + actual_user_input,
            short_desc="Open" + (" • add to history" if is_history else ""),
            target=kpu.kwargs_encode(server=self.name, effective_value=actual_user_input, is_history=is_history),
            args_hint=kp.ItemArgsHint.FORBIDDEN,
            hit_hint=kp.ItemHitHint.KEEPALL if is_history else kp.ItemHitHint.IGNORE,
            icon_handle=self.plugin._icons[self.filter_icon],
            loop_on_suggest=False,
            data_bag=(kpu.kwargs_encode(url=self.api.create_issues_url(actual_user_input),
                                        effective_value=actual_user_input))))

    def add_issues_matching_filter(self, actual_user_input: str, suggestions: Sequence) -> None:
        self.dbg("add_issues_matching_filter for " + actual_user_input)
        api_result_suggestions = self.get_issues_matching_filter(actual_user_input)

        if len(api_result_suggestions) > self.max_results:
            amt = str(self.max_results) + "+ issues"
        else:
            amt = str(len(api_result_suggestions)) + " issues"
        if self.show_issues_entry:
            self.add_issues_entry(actual_user_input, amt, suggestions, False)
        if self.show_issues_history_entry:
            self.add_issues_entry(actual_user_input, amt, suggestions, True)
        for res in api_result_suggestions[:self.max_results]:
            suggestions.append(res)

    def add_issues_entry(self, actual_user_input, amt, suggestions, is_history):
        suggestions.append(self.plugin.create_item(
            category=self.plugin.ITEMCAT_ISSUES,
            label=self.issues_label + " ▶ " + actual_user_input,
            short_desc=amt + (" • add to history" if is_history else ""),
            target=kpu.kwargs_encode(server=self.name, effective_value=actual_user_input, is_history=is_history),
            args_hint=kp.ItemArgsHint.ACCEPTED,
            hit_hint=kp.ItemHitHint.KEEPALL if is_history else kp.ItemHitHint.IGNORE,
            icon_handle=self.plugin._icons[self.issues_icon],
            loop_on_suggest=True,
            data_bag=(kpu.kwargs_encode(url=self.api.create_issues_url(actual_user_input),
                                        effective_value=actual_user_input))))

    def get_issues_matching_filter(self, actual_user_input):
        issues = self.api.get_issues_matching_filter(actual_user_input)
        suggestions = []
        for issue in issues:
            suggestions.append(self.plugin.create_item(
                category=self.plugin.ITEMCAT_ISSUES,
                label=issue.summary + " [" + issue.id + "]",
                short_desc=
                issue.id +
                (" ▶ " + issue.description[:150] if issue.description is not None else ""),
                target=issue.id,
                args_hint=kp.ItemArgsHint.FORBIDDEN,
                hit_hint=kp.ItemHitHint.NOARGS,
                icon_handle=self.plugin._icons[self.issues_icon],
                loop_on_suggest=False,
                data_bag=(kpu.kwargs_encode(url=issue.url))))
        return suggestions
