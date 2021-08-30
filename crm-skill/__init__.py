import time
from datetime import datetime, timezone
from lingua_franca.format import nice_date_time, nice_date
from mycroft_bus_client import MessageBusClient, Message
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse

from .constants import *
from .db import *


class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.client = MessageBusClient()
        self.client.run_in_thread()

    def wrap_get_response(self, question: str, state: int,
        allowed_actions = {ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP}, dialog_data=None):
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
        return utt, None, state + 1

    @intent_file_handler("new-contact.intent")
    def handle_new_contact(self, message) -> dict:
        done = False
        state = 0

        # get entities if the user used a compact phrase
        utt_name = message.data.get("name")         if message is not None else None
        utt_surname = message.data.get("surname")   if message is not None else None

        while not done:
            if state == 0:
                if utt_surname is None:
                    utt_surname, action, state = self.wrap_get_response("ask-surname", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    })
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
                    })
                    if action in (ACTION_REPEAT, ACTION_BACK):
                        continue
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return

                    if utt_name is None:
                        return
                else:
                    state += 1

                self.speak_dialog("generic-data-done-repeat", {"data": utt_name})

                nickname_mandatory = False
                list_contacts = get_contact(utt_name, utt_surname, "")
                similar_contacts = len(list_contacts)
                if similar_contacts > 0:
                    # ask for contact disambiguation
                    self.speak_dialog("similar-contacts", {"number": similar_contacts, "name": utt_name})

                    for i, _ in enumerate(list_contacts):
                        flag_nickname = True
                        flag_birthdate = True
                        if list_contacts[i]["nickname"] is None or (list_contacts[i]["nickname"]==""):
                            flag_nickname = False
                        if list_contacts[i]["birth_date"] is None or (list_contacts[i]["birth_date"]==""):
                            flag_birthdate = False

                        if flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate-wnick", {
                                "name": utt_name,
                                "surname": utt_surname,
                                "nickname": list_contacts[i]["nickname"],
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        elif flag_nickname and not flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact", {
                                "name": utt_name,
                                "surname": utt_surname,
                                "nickname": list_contacts[i]["nickname"]
                            })
                        elif not flag_nickname and flag_birthdate:
                            identikit = self.ask_yesno("ask-disambiguate-contact-wbdate", {
                                "name": utt_name,
                                "surname": utt_surname,
                                "birthdate": list_contacts[i]["birth_date"]
                            })
                        else:
                            identikit = self.ask_yesno("ask-disambiguate-contact-nobir-nonick", {"name": utt_name, "surname": utt_surname})

                        if identikit == "yes":
                            self.speak_dialog("error-contact-exists", {"name": utt_name, "surname": utt_surname})
                            return

                    if self.ask_yesno("ask-sure-another-person", {"name": utt_name, "surname": utt_surname}) == "yes":
                        nickname_mandatory = True
                        continue
                    self.speak_dialog("finishing")
                    return

            if state == 2:
                allowed_actions = {ACTION_STOP, ACTION_REPEAT, ACTION_BACK}
                if not nickname_mandatory:
                    allowed_actions.update({ACTION_SKIP})
                utt_nickname, action, state = self.wrap_get_response("ask-nickname", state, allowed_actions=allowed_actions,
                                                                     dialog_data={"name": utt_name, "surname": utt_surname})
                if action is None:
                    self.speak_dialog("generic-data-done-repeat", {"data": utt_nickname})
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
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
                self.speak_dialog("finishing")
                return contact

            if state == 5:
                utt_gender, action, state = self.wrap_get_response("ask-gender", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_SKIP
                }, dialog_data={"name": utt_name})
                if action is None:
                    if self.voc_match(utt_gender, "genders"):
                        contact["gender"] = utt_gender
                        self.speak_dialog("generic-data-done-repeat", {"data": utt_gender})
                    else:
                        contact["gender"] = "other"
                elif action == ACTION_STOP:
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
                    self.speak_dialog("finishing")
                    return contact
                else:
                    continue

                if utt_birth_date is None:
                    return

            if state == 7:
                self.speak_dialog("end-new-contact", {
                    "name": contact["name"],
                    "surname": contact["surname"],
                })
                done = True
                return contact

    @intent_file_handler("add-reminder.intent")
    def handle_new_reminder(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        utt_person = message.data.get("person")     if message is not None else None
        utt_datetime = message.data.get("datetime") if message is not None else None

        while not done:
            if state == 0:
                if utt_person is not None and utt_datetime is not None:
                    state += 1
                elif utt_person is not None:
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

                self.speak_dialog("generic-data-done-repeat", {"data": utt_person})

                list_contacts = get_all_contacts(utt_person)
                if len(list_contacts)<=0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno("ask-create-contact")
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return

                elif len(list_contacts)>1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person})
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
                            #self.speak_dialog("generic-data-done-repeat", {"data": utt_person})
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
                    self.speak_dialog("error-not-date")
                    state -= 1
                    continue

                date = parsed_datetime[0]

                if date < datetime.now(tz=timezone.utc):
                    utt_datetime = None
                    self.speak_dialog("error-datetime-past")
                    state -= 1
                    continue

                self.disable_intent("add-reminder.intent")

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
                self.enable_intent("add-reminder.intent")
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

    @intent_file_handler("new-activity.intent")
    def handle_new_activity(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        utt_person = message.data.get("person")     if message is not None else None
        utt_datetime = message.data.get("datetime") if message is not None else None
        utt_activity = message.data.get("activity") if message is not None else None

        # questions can be skipped if all entities exist and are valid
        skip_questions = False

        while not done:
            if state == 0:
                if utt_person is not None and utt_datetime is not None and utt_activity is not None:
                    skip_questions = True
                    state += 1
                elif utt_person is not None:
                    state += 1
                else:
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

                self.speak_dialog("generic-data-done-repeat", {"data": utt_person})

                list_contacts = get_all_contacts(utt_person)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno("ask-create-contact")
                    if should_proceed == "yes":
                        list_contacts = [self.handle_new_contact(None)]
                        if list_contacts[0] is None:
                            return
                    else:
                        self.speak_dialog("finishing")
                        return
                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person})
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
                            #self.speak_dialog("generic-data-done-repeat", {"data": utt_person})
                            contact = list_contacts[i]
                            flag = 1
                            break

                    if flag == 0:
                        self.speak_dialog("error-contact-not-found")
                        return

                else:
                    contact = list_contacts[0]


            if state == 1:
                if not skip_questions:
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
                if not skip_questions:
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

                try:
                    parsed_datetime = parse.extract_datetime(utt_datetime)
                except Exception:
                    # in some mysterious occasions, the parser would throw a TypeError
                    # we can catch it to make the user repeat the date.
                    # see issue #38
                    parsed_datetime = None
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    self.speak_dialog("error-not-date")
                    state -= 1
                    skip_questions = False
                    continue

                date = parsed_datetime[0]

                if date > datetime.now(tz=timezone.utc):
                    self.speak_dialog("error-datetime-future")
                    state -= 1
                    skip_questions = False
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
                    "datetime": nice_date_time(date),
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
                    done, skip_questions = False, False
                    utt_person, utt_datetime, utt_activity = None, None, None
                    state = 1
                    continue

            self.speak_dialog("finishing")
            done = True

    @intent_file_handler("delete-last-action.intent")
    def handle_deletion_last_action(self, message):
        if len(last_actions) > 0:
            last_action = last_actions[-1]
            type = last_action["type"]
            contact_id = last_action["contact"]
            contact = get_contact_by_id(contact_id)
            if type == "contact":

                should_delete = self.ask_yesno("Your last action is: You added {} {} {} to your contacts list. Do you want delete them?".
                    format(contact['name'],
                           contact['surname'],
                           contact['nickname']))
                if should_delete == "yes":
                    remove_contact(contact)
                    self.speak_dialog("I removed {} {} {} from your contacts list.".
                        format(contact['name'],
                               contact['surname'],
                               contact['nickname']))
                else:
                    self.speak_dialog("finishing")
            if type == "activity":
                should_delete = self.ask_yesno("Your last action is: You added the following activity: {} for {} related to {} {} {}. Do you want delete it?".
                    format(last_action['activity'],
                           last_action['date'],
                           contact['name'],
                           contact['surname'],
                           contact['nickname']))
                if should_delete == "yes":
                    for index, activity in enumerate(contact['activities']):
                        if (last_action['activity'] == activity['activity'] and last_action['date'] == activity['date']):
                            remove_activity(contact, index)
                            self.speak_dialog("I removed the activity.")
                else:
                    self.speak_dialog("finishing")
            if type == "reminder":
                should_delete = self.ask_yesno("Your last action is: You set the following reminder: {} for {} related to {} {} {}. Do you want delete it?".
                    format(contact['reminders'][-1]['activity'],
                           contact['reminders'][-1]['date'],
                           contact['name'],
                           contact['surname'],
                           contact['nickname']))
                if should_delete == "yes":
                    remove_reminder(contact)
                    self.speak_dialog("I removed the reminder.")
                else:
                    self.speak_dialog("finishing")
        else:
            self.speak_dialog("The last action cannot be undone")

    @intent_file_handler("last-activities.intent")
    def handle_last_activities(self, message):
        done = False
        state = 0

        # get entities if the user used a compact phrase
        utt_person = message.data.get("person") if message is not None else None

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

                self.speak_dialog("generic-data-done-repeat", {"data": utt_person})

                list_contacts = get_all_contacts(utt_person)
                if len(list_contacts) <= 0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno("ask-create-contact")
                    if should_proceed == "yes":
                        self.handle_new_contact(None)
                    return
                if len(list_contacts) > 1:
                    self.speak_dialog("similar-contacts-wname", {"number": len(list_contacts), "name": utt_person})
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
                            #self.speak_dialog("generic-data-done-repeat", {"data": utt_person})
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
