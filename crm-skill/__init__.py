import time
from datetime import datetime, timezone
from lingua_franca.format import nice_date_time, nice_date
from mycroft_bus_client import MessageBusClient, Message
from mycroft import MycroftSkill, intent_file_handler, intent_handler
from mycroft.util import parse

from adapt.intent import IntentBuilder

from .constants import *
from .db import *
from .util import *


class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.client = MessageBusClient()
        self.client.run_in_thread()

    def wrap_get_response(self, question: str, state: int,
        allowed_actions = {ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP}, dialog_data=None, reject_stopwords=False):
        """Wraps the self.get_response method with logic to simplify handling multiple states of a specific task.
        Returns (utterance; user-specified action; next state, based on the action)"""
        utt = self.get_response(question) if dialog_data is None else self.get_response(question, dialog_data)
        if allowed_actions is not None:
            for action in allowed_actions:
                # try an exact match
                if self.voc_match(utt, action, exact=True):
                    if action == ACTION_BACK:
                        state = state - 1
                    elif action == ACTION_SKIP:
                        state = state + 1
                    return utt, action, state

                # if no exact match, check if the utterance contains an action word
                if self.voc_match(utt, action, exact=False):
                    if action == ACTION_BACK and self.ask_yesno("ask-confirmation-back") == "yes":
                        state = state - 1
                    elif action == ACTION_SKIP and self.ask_yesno("ask-confirmation-skip") == "yes":
                        state = state + 1
                    elif action == ACTION_STOP and self.ask_yesno("ask-confirmation-stop") == "yes":
                        return utt, action, state
                    elif action == ACTION_REPEAT and self.ask_yesno("ask-confirmation-repeat") == "yes":
                        return utt, action, state

        # default: no action words; regular data
        # if the utterance contains potentially bad data, ask for confirmation

        if reject_stopwords:
            utt = utt.replace("the name is", "").replace("the surname is", "").replace("it is", "").replace("the nickname is", "") \
                .replace("her name is", "").replace("his name is", "")

        if reject_stopwords and self.voc_match(utt, "stopwords"):
            if self.ask_yesno("ask-confirmation-good-data", {"utt": utt}) != "yes":
                return None, ACTION_REPEAT, state

        # everything smooth with the utterance; increment the state
        return utt, None, state + 1

    @intent_handler(IntentBuilder("NewContact")
        .optionally("Name")
        .optionally("Surname")
        .require("NewContactKeyword")
    )
    @intent_file_handler("new-contact.intent")
    def handle_new_contact(self, message, is_inner_task=False) -> dict:
        done = False
        state = 0

        # get entities if the user used a compact phrase
        match_dict = parse_regex(self, "NewContact", message.data.get("utterance")) if message is not None else None
        utt_name = match_dict.get("Name")                                           if match_dict is not None else None
        utt_surname = match_dict.get("Surname")                                     if match_dict is not None else None

        while not done:
            if state == 0:
                if utt_surname is None:
                    utt_surname, action, state = self.wrap_get_response("ask-surname", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    }, reject_stopwords=True)
                    if action == ACTION_REPEAT:
                        continue
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return

                    if utt_surname is None:
                        return
                else:
                    state += 1

                self.speak_dialog("generic-data-done-repeat", {"data": utt_surname})

            if state == 1:
                if utt_name is None:
                    utt_name, action, state = self.wrap_get_response("ask-name", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT, ACTION_BACK
                    }, reject_stopwords=True)
                    if action in (ACTION_REPEAT, ACTION_BACK):
                        continue
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return

                    if utt_name is None:
                        return
                else:
                    state += 1

                nickname_mandatory = False
                list_contacts = get_contact(utt_name, utt_surname, "")
                similar_contacts = len(list_contacts)
                if similar_contacts > 0:
                    # ask for contact disambiguation
                    self.speak_dialog("similar-contacts-wname", {"number": similar_contacts, "name": utt_name})

                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            self.speak_dialog("error-contact-exists", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })
                            return

                    if self.ask_yesno("ask-sure-another-person", {"name": utt_name, "surname": utt_surname}) == "yes":
                        nickname_mandatory = True
                        continue
                    self.speak_dialog("finishing")
                    return

                else:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_name})

            if state == 2:
                allowed_actions = {ACTION_STOP, ACTION_REPEAT, ACTION_BACK}
                if not nickname_mandatory:
                    allowed_actions.update({ACTION_SKIP})
                utt_nickname, action, state = self.wrap_get_response("ask-nickname", state, allowed_actions=allowed_actions,
                                                                     dialog_data={"name": utt_name, "surname": utt_surname},
                                                                     reject_stopwords=True)
                if action is None:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_nickname})
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                elif action == ACTION_BACK:
                    utt_name=None
                    continue
                else:
                    add_contact(utt_name, utt_surname, "")
                    state += 1
                    continue

                if utt_nickname is None:
                    return

                if get_contact_by_nickname(utt_nickname) is not None:
                    self.speak_dialog("error-duplicate-nickname", {"data": utt_nickname})
                    state -= 1
                    continue

            if state == 3:
                add_contact(utt_name, utt_surname, utt_nickname)
                state += 1

            if state == 4:
                should_proceed = self.ask_yesno("contact-added-ask-details", {"name": utt_name, "surname": utt_surname})
                contact = get_contact(utt_name, utt_surname, "")[0]
                last_actions.append({
                    "type": "contact",
                    "contact": contact["id"]
                })
                if should_proceed == "yes":
                    state += 1
                    continue
                if is_inner_task:
                    self.speak_dialog("finishing-inner")
                else:
                    self.speak_dialog("finishing")
                return contact

            if state == 5:
                utt_gender, action, state = self.wrap_get_response("ask-gender", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_SKIP, ACTION_BACK
                }, dialog_data={"name": utt_name}, reject_stopwords=True)
                if action is None:
                    if self.voc_match(utt_gender, "genders"):
                        contact["gender"] = utt_gender
                        self.speak_dialog("generic-data-done-repeat", {"data": utt_gender})
                    else:
                        contact["gender"] = "other"
                elif action == ACTION_STOP:
                    if is_inner_task:
                        self.speak_dialog("finishing-inner")
                    else:
                        self.speak_dialog("finishing")
                    return contact
                else:
                    continue

                if utt_gender is None:
                    return

            if state == 6:
                utt_birth_date, action, state = self.wrap_get_response("ask-birth-date", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP
                }, dialog_data={"name": utt_name})
                if action is None:
                    try:
                        contact["birth-date"] = parse.extract_datetime(utt_birth_date)[0]
                    except Exception:
                        # in some mysterious occasions, the parser would throw a TypeError
                        # we can catch it to make the user repeat the date.
                        # see issue #38
                        contact["birth-date"] = None

                    if contact["birth-date"] is None:
                        # no datetime found in the utterance --> repeat
                        self.speak_dialog("error-not-date")
                        state -= 1
                        continue
                    if contact["birth-date"] > datetime.now(tz=timezone.utc):
                        contact["birth-date"] = None
                        self.speak_dialog("error-datetime-future")
                        state -= 1
                        continue

                    self.speak_dialog("generic-data-done-repeat", {"data": utt_birth_date})
                elif action == ACTION_STOP:
                    if is_inner_task:
                        self.speak_dialog("finishing-inner")
                    else:
                        self.speak_dialog("finishing")
                    return contact
                else:
                    continue

                if utt_birth_date is None:
                    return

            if state == 7:
                if is_inner_task:
                    self.speak_dialog("finishing-inner")
                else:
                    self.speak_dialog("finishing")
                done = True
                return contact

    @intent_handler(IntentBuilder("NewReminder")
        .optionally("Person")
        .require("NewReminderKeyword")
    )
    def handle_new_reminder(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        match_dict = parse_regex(self, "AddReminder", message.data.get("utterance"))
        utt_person = match_dict.get("Person")     if match_dict is not None else None
        utt_datetime = match_dict.get("DateTime") if match_dict is not None else None

        while not done:
            if state == 0:
                if utt_person is not None:
                    state += 1
                else:
                    utt_person, action, state = self.wrap_get_response("ask-about-whom", state, allowed_actions={
                        ACTION_REPEAT, ACTION_STOP
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue

                    if utt_person is None:
                        return

                list_contacts, utt_person_clean = get_all_contacts(utt_person, self)

                if len(list_contacts) == 1:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_person_clean})

                if len(list_contacts)<=0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno("ask-create-contact-wname", {"person": utt_person_clean})
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None, True)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return

                elif len(list_contacts)>1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person_clean})
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            list_contacts[0] = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return

            if state == 1:
                utt_activity, action, state = self.wrap_get_response("ask-what-remind", state, allowed_actions={
                    ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action in (ACTION_REPEAT, ACTION_BACK):
                    continue

                if utt_activity is None:
                    return

            if state == 2:
                if utt_datetime is None:
                    utt_datetime, action, state = self.wrap_get_response("ask-when-remind", state, allowed_actions={
                        ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action in (ACTION_REPEAT, ACTION_BACK):
                        continue

                    if utt_datetime is None:
                        return
                else:
                    state += 1

                self.speak_dialog("generic-data-done-repeat", {"data": utt_datetime})

                try:
                    parsed_datetime = parse.extract_datetime(utt_datetime)
                except Exception:
                    # in some mysterious occasions, the parser would throw a TypeError
                    # we can catch it to make the user repeat the date.
                    # see issue #38
                    parsed_datetime = None
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    utt_datetime = None
                    self.speak_dialog("error-not-date")
                    state -= 1
                    continue

                date = parsed_datetime[0]

                if date < datetime.now(tz=timezone.utc):
                    utt_datetime = None
                    self.speak_dialog("error-datetime-past")
                    state -= 1
                    continue

                self.disable_intent("NewReminder")

                # call the reminder-skill to activate the reminder in mycroft
                self.bus.emit(Message("recognizer_loop:utterance", {"utterances":
                    [f"remind me to {utt_activity} related to {utt_person} on {utt_datetime}"],
                    "lang": "en-us"}
                ))
                add_reminder(list_contacts[0], utt_activity, date)

                last_actions.append({
                    "type": "reminder",
                    "contact": list_contacts[0]["id"]
                })

            if state == 3:
                time.sleep(1) # wait for the external skill to avoid race condition
                self.enable_intent("NewReminder")
                spoken_contact = list_contacts[0]["nickname"] if list_contacts[0]["nickname"] != "" else list_contacts[0]["name"]
                should_repeat = self.ask_yesno("ask-repeat-task-reminder", {
                    "person": spoken_contact,
                })
                if should_repeat == "yes":
                    # reset fields, and restart from the questions
                    done = False
                    utt_person, utt_datetime = None, None
                    state = 1
                    continue

            self.speak_dialog("finishing")
            done = True


    @intent_handler(IntentBuilder("NewActivity")
        .require("NewActivityKeyword")
    )
    def handle_new_activity(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        match_dict = parse_regex(self, "NewActivity", message.data.get("utterance"))
        utt_person = match_dict.get("Person")     if match_dict is not None else None
        utt_datetime = match_dict.get("DateTime") if match_dict is not None else None
        utt_activity = match_dict.get("Activity") if match_dict is not None else None

        while not done:
            if state == 0:
                if utt_person is None:
                    utt_person, action, state = self.wrap_get_response("ask-with-whom", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue

                    if utt_person is None:
                        return
                else:
                    state += 1

                list_contacts, utt_person_clean = get_all_contacts(utt_person, self)
                if len(list_contacts) == 1:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_person})
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno("ask-create-contact-wname", {"person": utt_person_clean})
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None, True)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return
                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person_clean})
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            contact = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return

                else:
                    contact = list_contacts[0]


            if state == 1:
                if utt_activity is None:
                    utt_activity, action, state = self.wrap_get_response("ask-activity", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT, ACTION_BACK
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action in (ACTION_BACK, ACTION_REPEAT):
                        continue
                else:
                    state += 1

                if utt_activity is None:
                    return

            if state == 2:
                if utt_datetime is None:
                    utt_datetime, action, state = self.wrap_get_response("ask-activity-when", state, allowed_actions={
                        ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action in (ACTION_BACK, ACTION_REPEAT):
                        continue

                    if utt_datetime is None:
                        return

                    self.speak_dialog("generic-data-done-repeat", {"data": utt_datetime})

                else:
                    state += 1

                utt_datetime = pastify_year(self, utt_datetime)
                utt_datetime = pastify_weekday(self, utt_datetime)
                try:
                    parsed_datetime = parse.extract_datetime(utt_datetime)
                except Exception:
                    # in some mysterious occasions, the parser would throw a TypeError
                    # we can catch it to make the user repeat the date.
                    # see issue #38
                    parsed_datetime = None
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    utt_datetime = None
                    self.speak_dialog("error-not-date")
                    state -= 1
                    continue

                date = parsed_datetime[0]

                if date > datetime.now(tz=timezone.utc):
                    self.speak_dialog("error-datetime-future")
                    utt_datetime = None
                    state -= 1
                    continue

                index = 0
                too_short = True
                for index, item in enumerate(contact["activities"]):
                    if item["date"] < date:
                        too_short = False
                        break


                if too_short:
                    contact["activities"].append({
                        "activity": utt_activity,
                        "date": date
                    })
                else:
                    contact["activities"].insert(index, {
                        "activity": utt_activity,
                        "date": date
                    })

                self.speak_dialog("end-new-activity", {
                    "activity": utt_activity,
                    "name": contact["name"],
                    "surname": contact["surname"],
                    "datetime": nice_date(date) if date.hour == 0 and date.minute == 0 else nice_date_time(date),
                })

                last_actions.append({
                    "type": "activity",
                    "contact": contact["id"],
                    "activity": utt_activity,
                    "date": date
                })

            if state == 3:
                spoken_contact = contact["nickname"] if contact["nickname"] != "" else contact["name"]
                should_repeat = self.ask_yesno("ask-repeat-task-activity", {
                    "person": spoken_contact,
                })
                if should_repeat == "yes":
                    # reset fields, and restart from the questions
                    done = False
                    utt_person, utt_datetime, utt_activity = None, None, None
                    state = 1
                    continue

            self.speak_dialog("finishing")
            done = True

    @intent_file_handler("delete-last-action.intent")
    def handle_deletion_last_action(self):
        if len(last_actions) > 0:
            last_action = last_actions[-1]
            action_type = last_action["type"]
            contact_id = last_action["contact"]
            contact = get_contact_by_id(contact_id)
            if action_type == "contact":
                if self.ask_yesno("delete-last-contact", {
                    "name": contact["name"],
                    "surname": contact["surname"],
                    "nickname": contact["nickname"],
                }) == "yes":
                    remove_contact(contact)
                    self.speak_dialog("done")
                else:
                    self.speak_dialog("finishing")
            if action_type == "activity":
                if self.ask_yesno("delete-last-activity", {
                    "name": contact["name"],
                    "surname": contact["surname"],
                    "nickname": contact["nickname"],
                    "date": nice_date_time(last_action["date"]),
                    "activity": last_action["activity"],
                }) == "yes":
                    for index, activity in enumerate(contact["activities"]):
                        if (last_action["activity"] == activity["activity"] and last_action["date"] == activity["date"]):
                            remove_activity(contact, index)
                            self.speak_dialog("done")
                else:
                    self.speak_dialog("finishing")
            if action_type == "reminder":
                if self.ask_yesno("delete-last-reminder", {
                    "date": nice_date_time(contact["reminders"][-1]["date"]),
                    "name": contact["name"],
                    "surname": contact["surname"],
                    "nickname": contact["nickname"],
                    "activity": contact["reminders"][-1]["activity"],
                }) == "yes":
                    remove_reminder(contact)
                    self.speak_dialog("done")
                else:
                    self.speak_dialog("finishing")
            if action_type == "relationship":
                contact_id2 = last_action["contact2"]
                contact2 = get_contact_by_id(contact_id2)
                if self.ask_yesno("delete-last-relationship", {
                    "person1_name": contact["name"],
                    "person1_surname": contact["surname"],
                    "person1_nickname": contact["nickname"],
                    "relationship": last_action["relationship"],
                    "person2_name": contact2["name"],
                    "person2_surname": contact2["surname"],
                    "person2_nickname": contact2["nickname"],
                }) == "yes":
                    remove_relationship(contact, contact2)
                    self.speak_dialog("done")
                else:
                    self.speak_dialog("finishing")
        else:
            self.speak_dialog("no-more-actions")

    @intent_handler(IntentBuilder("LastActivities")
        .optionally("LastActivitiesKeyword")
    )
    def handle_last_activities(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        match_dict = parse_regex(self, "LastActivities", message.data.get("utterance"))
        utt_person = match_dict.get("Person") if match_dict is not None else None

        while not done:
            if state == 0:
                if utt_person is not None:
                    state += 1
                else:
                    utt_person, action, state = self.wrap_get_response("ask-about-whom", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue

                    if utt_person is None:
                        return



                list_contacts, utt_person_clean = get_all_contacts(utt_person, self)
                if len(list_contacts) == 1:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_person})
                if len(list_contacts) <= 0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno("ask-create-contact-wname", {"person": utt_person_clean})
                    if should_proceed == "yes":
                        self.handle_new_contact(None, True)
                    return


                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person_clean})
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            list_contacts[0] = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return

                if len(list_contacts[0]["activities"]) == 0:
                    self.speak_dialog("no-activities", {"name": list_contacts[0]["name"]})
                    return
                number_of_activities = 0                           # the position in the list of the activities to read
                next_step = "repeat"                               # continue, repeat, back, exit
                cont_step = 0                                      # already done steps
                response_list = ["repeat", "continue", "exit"]
                self.speak_dialog("intro-activities")
                while next_step != "exit":
                    cont_step += 1
                    for i in range(5):
                        if number_of_activities >= len(list_contacts[0]["activities"]):
                            self.speak_dialog("no-other-activities", {"name": list_contacts[0]["name"]})
                            break

                        activity = list_contacts[0]["activities"][number_of_activities]["activity"]
                        date = list_contacts[0]["activities"][number_of_activities]["date"]
                        if date.hour == 0 and date.minute == 0:
                            self.speak_dialog("read-activity", {"activity": activity, "when": nice_date(date)})
                        else:
                            self.speak_dialog("read-activity", {"activity": activity, "when": nice_date_time(date)})
                        number_of_activities += 1

                    # ask and handle the next step
                    next_step = None
                    response_list = make_response_list(cont_step, number_of_activities, len(list_contacts[0]["activities"]))
                    while next_step not in response_list:
                        next_step = self.ask_selection(response_list)
                    if next_step == "repeat":
                        number_of_activities = (cont_step - 1) * 5
                        cont_step -= 1
                    elif next_step == "back":
                        number_of_activities = (cont_step - 2) * 5
                        cont_step -= 2

                self.speak_dialog("finishing")
                done = True

    @intent_handler(IntentBuilder("NewRelationship")
        .optionally("Person1")
        .optionally("Person2")
        .optionally("RelationshipType")
        .optionally("Is")
        .optionally("A")
        .optionally("Of")
        .optionally("RelationshipKeyword")
    )
    @intent_file_handler("add-relationship.intent")
    def handle_add_relationships(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        match_dict = parse_regex(self, "NewRelationship", message.data.get("utterance"))
        utt_person = match_dict.get("Person1")                if match_dict is not None else None
        utt_relationship = match_dict.get("RelationshipType") if match_dict is not None else None
        utt_person2 = match_dict.get("Person2")               if match_dict is not None else None
        found_relationship = "first"

        while not done:
            if state == 0:
                if utt_person is not None:
                    state += 1
                else:
                    utt_person, action, state = self.wrap_get_response("ask-about-whom-rel", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue

                    if utt_person is None:
                        return

                list_contacts, utt_person_clean = get_all_contacts(utt_person, self)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno("ask-create-contact-wname", {"person": utt_person_clean})
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None, True)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return
                if len(list_contacts) == 1:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_person_clean})
                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person_clean})
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            contact1 = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return
                else:
                    contact1 = list_contacts[0]

            if state == 1:
                if utt_relationship is not None and found_relationship is not None:
                    state += 1
                else:
                    utt_relationship, action, state = self.wrap_get_response("ask-relationship", state,
                        allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK}, reject_stopwords=False)
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue

                found_relationship = None
                for current_rp in RP_INVERSE:
                    if self.voc_match(utt_relationship, current_rp, exact=False):
                        found_relationship = current_rp
                        break

                if found_relationship is None:
                    state -= 1
                    continue

                self.speak_dialog("generic-data-done-repeat", {"data": found_relationship})

            if state == 2:
                if utt_person2 is not None:
                    state += 1
                else:
                    utt_person2, action, state = self.wrap_get_response(f"Whose {found_relationship} is {contact1['name']}", state,
                        allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK})
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue
                    if utt_person2 is None:
                        return

                list_contacts, utt_person2_clean = get_all_contacts(utt_person2, self)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno("ask-create-contact-wname", {"person": utt_person2_clean})
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None, True)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return
                if len(list_contacts) == 1:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_person2_clean})
                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {
                        "number": len(list_contacts),
                        "name": utt_person2_clean
                    })
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {
                                "name": list_contacts[i]["name"],
                                "surname": list_contacts[i]["surname"]
                            })

                        if identikit == "yes":
                            contact2 = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return
                else:
                    contact2 = list_contacts[0]

            if state == 3:
                add_relationship(contact1["id"], contact2["id"], found_relationship)
                last_actions.append({
                    "type": "relationship",
                    "contact": contact1["id"],
                    "contact2": contact2["id"],
                    "relationship": found_relationship
                })
                self.speak_dialog("finishing")
                done = True


def create_skill():
    return VoiceCRM()


def make_response_list(cont_step: int, number_of_activities: int, activities_length: int) -> list:
    """Returns the appropriate listing options, basing on the given parameters"""
    ret = []

    if cont_step > 1:
        ret.append("back")
    ret.append("repeat")
    if number_of_activities < activities_length:
        ret.append("continue")
    ret.append("exit")

    return ret
