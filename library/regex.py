from typing import List, Pattern, Callable


class RegexMatch(object):
    def __init__(
            self,
            regex: Pattern,
            no_matches_func: Callable,
            eval_matches_func: Callable[[List[str]], bool]
    ):
        self.regex = regex
        self.no_matches_func = no_matches_func
        self.eval_matches_func = eval_matches_func


def match_regex_in_order(
        text: str,
        regex_matches: List[RegexMatch],
        final_func: Callable
):
    for rm in regex_matches:
        matches = rm.regex.match(text)
        if not matches:
            rm.no_matches_func()
            continue
        groups = matches.groups()
        if not groups:
            rm.no_matches_func()
            continue
        if rm.eval_matches_func(list(map(lambda s: str(s), groups))):
            return
    final_func()
