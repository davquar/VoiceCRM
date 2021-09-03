import re
from datetime import datetime

def parse_regex(mycroft, intent_name: str, utterance: str) -> dict:
    '''
    Matches the given utterance against the regexes defined inside the
    file in vocab/regex/<lang>/intent_name.rx,
    and returns the matching entities, otherwise None.
    '''
    utterance = utterance + "\n"    # append newline to avoid unterminated subpattern error in the regex matching
    regex_file = mycroft.find_resource(intent_name + ".rx", "regex")

    with open(regex_file, "r") as reader:
        for regex in reader.readlines():
            prog = re.compile(regex)
            match = prog.match(utterance)
            if match is not None:
                reader.close()
                return match.groupdict()
    return None


def pastify_weekday(mycroft, utterance: str) -> str:
    '''
    Prepends "last" to the given utterance (that contains a weekday), if it doesn't begin with it already.
    This function is used to make sure that a weekday is always in the past
    and not interpreted as in the future.
    '''
    utterance = utterance.replace("on ", "").replace("this ", "")
    weekdays_file = mycroft.find_resource("weekdays.list", "vocab")
    with open(weekdays_file, "r") as reader:
        for weekday in reader.readlines():
            if weekday[:-1] == utterance:
                reader.close()
                return "last " + utterance
    return utterance


def pastify_year(mycroft, utterance: str) -> str:
    '''
    Appends the current year to the given utterance (that contains an absolute date).
    This function is used to make sure that a date is always in the past
    and not interpreted as in the future.
    '''
    months_file = mycroft.find_resource("months.list", "vocab")
    with open(months_file, "r") as reader:
        for month in reader.readlines():
            if month[:-1] in utterance:
                reader.close()
                return utterance + " " + str(datetime.today().year)
    return utterance
