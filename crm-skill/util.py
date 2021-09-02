import re

def parse_regex(mycroft, intent_name: str, utterance: str) -> dict:
    '''
    Matches the given utterance against the regexes defined inside the
    file in vocab/regex/<lang>/intent_name.rx,
    and returns the matching entities, otherwise None.
    '''
    utterance = utterance + "\n"    # append newline to avoid unterminated subpattern error in the regex matching
    regex_file = mycroft.find_resource(intent_name + ".rx", "regex")

    with open(regex_file, "r") as reader:
        print(utterance)
        for regex in reader.readlines():
            prog = re.compile(regex)
            match = prog.match(utterance)
            print(regex)
            print(match)
            if match is not None:
                reader.close()
                return match.groupdict()
    return None
