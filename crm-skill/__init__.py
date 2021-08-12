from datetime import datetime, timezone
from lingua_franca.format import nice_date_time, nice_date
from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse
from mycroft_bus_client import MessageBusClient, Message

from .constants import *
from .db import *

class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.client = MessageBusClient()
        self.client.run_in_thread()

    def wrap_get_response(self, question: str, state: int, exact_match=False, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP}):
        """Wraps the self.get_response method with logic to simplify handling multiple states of a specific task.
        Returns (utterance; user-specified action; next state, based on the action)"""
        utt = self.get_response(question)
        if allowed_actions is not None:
            for action in allowed_actions:
                if self.voc_match(utt, action, exact=exact_match):
                    if action == ACTION_BACK:
                        state = state - 1
                    elif action == ACTION_SKIP:
                        state = state + 1
                    return utt, action, state
        return utt, None, state + 1

    @intent_file_handler("new-contact.intent")
    def handle_new_contact(self):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname, action, state = self.wrap_get_response("what is the surname?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return

            if state == 1:
                name, action, state = self.wrap_get_response("okay, the name?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_BACK
                })
                if action in (ACTION_REPEAT, ACTION_BACK):
                    continue
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if len(get_contact(name, surname, "")) > 0:
                    self.speak(f"You already have {name} {surname}. I'll stop here.")
                    return

            if state == 2:
                add_contact(name, surname)
                state += 1

            if state == 3:
                should_proceed = self.ask_yesno(f"Okay, I've added {name} {surname}. Do you want to add other details to them?")
                if should_proceed == "no":
                    self.speak_dialog("finishing")
                    return
                contact = get_contact(name, surname, "")[0]
                state += 1

            if state == 4:
                gender, action, state = self.wrap_get_response("What is the gender?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_SKIP
                })
                if action is None:
                    contact["gender"] = gender
                    self.speak(f"{gender}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                else:
                    continue

            if state == 5:
                birth_date, action, state = self.wrap_get_response("Birth date?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP
                })
                if action is None:
                    contact["birth-date"] = parse.extract_datetime(birth_date)
                    if contact["birth-date"] is None:
                        # no datetime found in the utterance --> repeat
                        self.speak("Hmm, that's not a date")
                        state -= 1
                        continue
                    self.speak(f"{birth_date}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                else:
                    continue

            if state == 6:
                nickname, action, state = self.wrap_get_response("Nickname?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP
                })
                if action is None:
                    if get_contact_by_nickname(nickname) is not None:
                        self.speak("You already have someone with that nickname. Choose another one.")
                        state -= 1
                        continue
                    contact["nickname"] = nickname
                    self.speak(f"{nickname}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                else:
                    continue

            if state == 7:
                self.speak_dialog("finishing")
                done = True

    @intent_file_handler("add-reminder.intent")
    def handle_new_reminder(self):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname_name, action, state = self.wrap_get_response("About whom?", state, allowed_actions={
                    ACTION_REPEAT, ACTION_STOP
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT:
                    continue

                list_contacts = get_all_contacts(surname_name)
                if len(list_contacts)<=0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno("The contact you call not exist. So, do you want to add it?")
                    if should_proceed == "yes":
                        self.handle_new_contact()
                    return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        if list_contacts[i]["nickname"] is None:
                            identikit="no"
                        else:
                            identikit = self.ask_yesno(f"Did you mean {surname_name}, {list_contacts[i]['nickname']}?")
                        if identikit == "yes":
                            self.speak_dialog("Ok, I get it")
                            list_contacts[0] = list_contacts[i]
                            flag = 1
                            break
                        if identikit == "no":
                            self.speak_dialog("")
                        else:
                            self.speak_dialog("")
                    if flag == 0:
                        self.speak_dialog("sorry I did not find your contact")
                        return

            if state == 1:
                activity, action, state = self.wrap_get_response("What should I remind you?", state, allowed_actions={
                    ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action in (ACTION_REPEAT, ACTION_BACK):
                    continue

            if state == 2:
                utt, action, state = self.wrap_get_response("When should I remind it to you?", state, allowed_actions={
                    ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action in (ACTION_REPEAT, ACTION_BACK):
                    continue

                parsed_datetime = parse.extract_datetime(utt)
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue

                date = parsed_datetime[0]

                # call the reminder-skill to activate the reminder in mycroft
                self.bus.emit(Message("recognizer_loop:utterance", {"utterances": [f"remind me to {activity} on {utt}"], "lang": "en-us"}))
                add_reminder(list_contacts[0], activity, date)
                done = True

    @intent_file_handler("new-activity.intent")
    def handle_new_activity(self, message):
        done = False
        state = 0
        while not done:
            if state == 0:
                if message.data.get("person") is not None:
                    person = message.data.get("person")
                else:
                    person, action, state = self.wrap_get_response("whith whom you have done this activity?", state, allowed_actions={
                        ACTION_STOP, ACTION_REPEAT
                    })
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue
                list_contacts = get_all_contacts(person)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno(f"Hey, I don't know {person}. Do you want to add them?")
                    if should_proceed == "yes":
                        self.handle_new_contact()
                        return
                    self.speak("Ok, I'm here if you need.")
                    return
                if len(list_contacts) > 1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        if list_contacts[i]["nickname"] is None:
                            identikit="no"
                        else:
                            identikit = self.ask_yesno(f"Did you mean {person}, {list_contacts[i]['nickname']}?")
                        if identikit == "yes":
                            self.speak_dialog("Ok, I get it")
                            contact = list_contacts[i]
                            flag=1
                            break
                        if identikit == "no":
                            self.speak_dialog("")
                        else:
                            self.speak_dialog("")
                    if flag == 0:
                        self.speak_dialog("sorry I did not find your contact")
                        return
                else:
                    contact = list_contacts[0]

            if state == 1:
                activity, action, state = self.wrap_get_response("Ok, what have you done with them?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT, ACTION_BACK
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action in (ACTION_BACK, ACTION_REPEAT):
                    continue

            if state == 2:
                utt, action, state = self.wrap_get_response("Perfect, when did you do it?", state, allowed_actions={
                    ACTION_STOP, ACTION_BACK, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action in (ACTION_BACK, ACTION_REPEAT):
                    continue

                parsed_datetime = parse.extract_datetime(utt)
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue

                date = parsed_datetime[0]

                index = 0
                too_short = True
                for index, item in enumerate(contact["activities"]):
                    if item["date"] < date:
                        too_short = False
                        break

                if too_short:
                    contact["activities"].append({
                        "activity": activity,
                        "date": date
                    })
                else:
                    contact["activities"].insert(index, {
                        "activity": activity,
                        "date": date
                    })

                self.speak("Awesome, done!")
                done = True

    @intent_file_handler("last-activities.intent")
    def handle_last_activities(self):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname_name, action, state = self.wrap_get_response("About whom?", state, allowed_actions={
                    ACTION_STOP, ACTION_REPEAT
                })
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT:
                    continue

                list_contacts = get_all_contacts(surname_name)
                if len(list_contacts) <= 0:
                    # the contact does not exist --> exit
                    self.speak("I don't know {}".format(surname_name))
                    return
                if len(list_contacts) > 1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag = 0
                    for i, _ in enumerate(list_contacts):
                        if list_contacts[i]["nickname"] is None:
                            identikit="no"
                        else:
                            identikit = self.ask_yesno(f"Did you mean {surname_name}, {list_contacts[i]['nickname']}?")
                        if identikit == "yes":
                            self.speak_dialog("Ok, I get it")
                            list_contacts[0] = list_contacts[i]
                            flag=1
                            break
                        if identikit == "no":
                            continue
                        continue
                    if flag==0:
                        self.speak_dialog("sorry I did not find your contact")
                        return
                if len(list_contacts[0]["activities"]) == 0:
                    self.speak("You have not any activities with {}".format(surname_name))
                    return
                number_of_activities = len(list_contacts[0]["activities"]) - 1 # the position in the list of the activity to read
                next_step = "repeat"                                           # continue, repeat, back, exit
                cont_step = 0                                                  # already done steps
                response_list = ["repeat", "continue", "exit"]
                while next_step != "exit":
                    cont_step += 1
                    for i in range(5):
                        if number_of_activities < 0:
                            self.speak("you have no other activities with this contact")
                            break

                        activity = list_contacts[0]["activities"][number_of_activities]["activity"]
                        date = list_contacts[0]["activities"][number_of_activities]["date"]
                        if date.hour == 0 and date.minute == 0:
                            self.speak(f"{activity} at {nice_date(date)}")
                        else:
                            self.speak(f"{activity} at {nice_date_time(date)}")
                        number_of_activities -= 1

                    # ask and handle the next step
                    next_step = None
                    response_list = make_response_list(cont_step, number_of_activities)
                    while next_step not in response_list:
                        next_step = self.ask_selection(response_list, "What do you want to do?")
                    if next_step == "repeat":
                        number_of_activities = len(list_contacts[0]["activities"]) - 1 - ((cont_step - 1) * 5)
                        cont_step -= 1
                    elif next_step == "back":
                        number_of_activities = len(list_contacts[0]["activities"]) - 1 - ((cont_step - 2) * 5)
                        cont_step -= 2

                self.speak("Great! I have done!")
                done = True

def create_skill():
    return VoiceCRM()

def make_response_list(cont_step: int, number_of_activities: int) -> list:
    """Returns the appropriate listing options, basing on the given parameters"""
    ret = []

    if cont_step > 1:
        ret.append("back")
    ret.append("repeat")
    if number_of_activities == 0:
        ret.append("continue")
    ret.append("exit")

    return ret
