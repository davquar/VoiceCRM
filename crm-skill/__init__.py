from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse
from mycroft_bus_client import MessageBusClient, Message
from lingua_franca.format import nice_date_time, nice_date
from datetime import datetime, timezone

from .constants import *

contacts = [
    {
        "name": "jo",
        "surname": "peter",
        "nickname": "baubau",
        "birth_date": "1996-01-01",
        "activities": [ 
            {"activity": "bar", "date": datetime(2021, 4, 5, 21, 0, tzinfo=timezone.utc)},
            {"activity": "nada","date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 3, 26, tzinfo=timezone.utc)}
        ],
        "reminders": []
    },
    {
        "name": "joe",
        "surname": "peter",
        "nickname": "bla bla bla",
        "birth_date": "1996-02-02",
        "activities": [
            {"activity": "pizza", "date": datetime(2021, 4, 5, tzinfo=timezone.utc)},
            {"activity": "cannelloni","date": datetime(2021, 4, 2, tzinfo=timezone.utc)},
            {"activity": "tennis", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "bungee jumping","date": datetime(2021, 3, 8, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 2, 28, tzinfo=timezone.utc)},
            {"activity": "new year's eve", "date": datetime(2021, 1, 1, tzinfo=timezone.utc)},
        ],
        "reminders": []
    }
]

def add_contact(name: str, surname: str, nickname=''):
    """Create new contact with the given name and surname """
    contacts.append({
        "name": name,
        "surname": surname,
        "nickname": nickname,
    })

def get_contact_by_nickname(nickname: str) -> dict:
    """Returns the (first/only) contact with the given nickname"""
    for item in contacts:
        if item["nickname"] == nickname:
            return item
    return None

def get_contact(name: str, surname: str, nickname: str) -> list:
    """Returns all the contacts with the given name, surname and nickname
    An empty argument means that it should not be considered in the search"""
    return list(filter(lambda contact: (contact["name"] == name or name=='') and (contact["surname"] == surname or surname=='') and (contact["nickname"] == nickname or nickname==''), contacts))

def all_name_surname_nick(s: str) -> list:
    """Returns (raw) all the contacts which name or surname or nickname (or a combination of them) matches the given string"""
    lis=s.split(' ')
    if len(lis)==1:
        return [['','',lis[0]],['',lis[0],''],[lis[0],'','']]
    else:
        n=len(lis)//2
        a1=all_name_surname_nick(' '.join(lis[:n]))
        a2=all_name_surname_nick(' '.join(lis[n:]))
        res=[]
        for e1 in a1:
            for e2 in a2:
                app=[]
                flag = -1
                if e2[0]!='' and e1[0]!='':
                    app.append(e1[0]+' '+e2[0])
                    flag=0
                elif e1[0]!='':
                    app.append(e1[0])
                else:
                    app.append(e2[0])
                if e2[1]!='' and e1[1]!='':
                    app.append(e1[1]+' '+e2[1])
                    flag=1
                elif e1[1]!='':
                    app.append(e1[1])
                else:
                    app.append(e2[1])
                if e2[2]!='' and e1[2]!='':
                    app.append(e1[2]+' '+e2[2])
                    flag=2
                elif e1[2]!='':
                    app.append(e1[2])
                else:
                    app.append(e2[2])
                if flag>-1:
                    splittedE2 = e2[flag].split(' ')
                    for i in range(len(splittedE2)):
                        if ' '.join(splittedE2[i+1:])=='':
                            word=' '.join(splittedE2[:i+1])+' '+e1[flag]+' '.join(splittedE2[i+1:])
                        else:
                            word=' '.join(splittedE2[:i+1])+' '+e1[flag]+' '+' '.join(splittedE2[i+1:])
                        app2=app.copy()
                        app2[flag]=word
                        res.append(app2)
                res.append(app)
        return res

def get_all_contacts(s: str) -> list:
    """Wraps all_name_surname_nick"""
    list_contacts = []
    lis=all_name_surname_nick(s)
    for l in lis :  
        list_contacts += get_contact(l[0], l[1], l[2])
    return list_contacts

def add_reminder(contact: dict, act: str, date: datetime):
    """Adds the given activity and date to the given contact"""
    contact['reminders'].append({'activity':act,'date':date})

def updateResponseList(contStep: int, numberOfActivities: int) -> list:
    """Returns the appropriate listing options, basing on the given parameters"""
    ret = []

    if contStep > 1:
        ret.append('back')
    ret.append('repeat')
    if numberOfActivities == 0:
        ret.append('continue')
    ret.append('exit')

    return ret

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

    @intent_file_handler('new-contact.intent')
    def handle_new_contact(self, message):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname, action, state = self.wrap_get_response("what is the surname?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return

            if state == 1:
                name, action, state = self.wrap_get_response("okay, the name?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK})
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    continue
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if len(get_contact(name, surname, '')) > 0:
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
                contact = get_contact(name, surname, '')[0]
                state += 1

            if state == 4:
                gender, action, state = self.wrap_get_response("What is the gender?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_SKIP})
                if action is None:
                    contact["gender"] = gender
                    self.speak(f"{gender}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                else:
                    continue

            if state == 5:
                birth_date, action, state = self.wrap_get_response("Birth date?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP})
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
                nickname, action, state = self.wrap_get_response("Nickname?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP})
                if action is None:
                    if get_contact_by_nickname(nickname) is not None:
                        self.speak(f"You already have someone with that nickname. Choose another one.")
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

    @intent_file_handler('add-reminder.intent')
    def handle_new_reminder(self, message):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname_name, action, state = self.wrap_get_response("About whom?", state, allowed_actions={ACTION_REPEAT, ACTION_STOP})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT:
                    continue

                list_contacts = get_all_contacts(surname_name)
                if len(list_contacts)<=0:
                    # the contact does not exist --> ask to create
                    should_proceed = self.ask_yesno(f"The contact you call not exist. So, do you want to add it?")
                    if should_proceed == 'yes':
                        self.handle_new_contact(message)
                    return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag=0
                    for i in range(len(list_contacts)):
                        if (list_contacts[i]['nickname'] is None):
                            identikit='no'
                        else:
                            identikit = self.ask_yesno(f"Did you mean {surname_name}, {list_contacts[i]['nickname']}?")
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            list_contacts[0] = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            self.speak_dialog('')
                        else:
                            self.speak_dialog('')
                    if flag==0:
                        self.speak_dialog('sorry I did not find your contact')
                        return

            if state == 1:
                activity, action, state = self.wrap_get_response("What should I remind you?", state, allowed_actions={ACTION_STOP, ACTION_BACK, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    continue
                
            if state == 2:
                utt, action, state = self.wrap_get_response("When should I remind it to you?", state, allowed_actions={ACTION_STOP, ACTION_BACK, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    continue

                parsed_datetime = parse.extract_datetime(utt)
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue
                else:
                    date = parsed_datetime[0]
 
                # call the reminder-skill to activate the reminder in mycroft
                self.bus.emit(Message('recognizer_loop:utterance', {"utterances": [f"remind me to {activity} on {utt}"], "lang": "en-us"}))
                add_reminder(list_contacts[0], activity, date)
                done = True

    @intent_file_handler("new-activity.intent")
    def handle_new_activity(self, message):
        done = False
        state = 0
        while not done:
            if state == 0:
                if message.data.get("person") != None:
                    person = message.data.get("person")
                else:
                    person, action, state = self.wrap_get_response("whith whom you have done this activity?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT})
                    if action == ACTION_STOP:
                        self.speak_dialog("finishing")
                        return
                    if action == ACTION_REPEAT:
                        continue
                list_contacts = get_all_contacts(person)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno(f"Hey, I don't know {person}. Do you want to add them?")
                    if should_proceed == 'yes':
                        self.handle_new_contact(message)
                        return
                    else:
                        self.speak("Ok, I'm here if you need.")
                        return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag=0
                    for i in range(len(list_contacts)):
                        if (list_contacts[i]['nickname'] is None):
                            identikit='no'
                        else:
                            identikit = self.ask_yesno(f"Did you mean {person}, {list_contacts[i]['nickname']}?")
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            contact = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            self.speak_dialog('')
                        else:
                            self.speak_dialog('')
                    if flag==0:
                        self.speak_dialog('sorry I did not find your contact')
                        return
                else:
                    contact = list_contacts[0]
            
            if state == 1:
                activity, action, state = self.wrap_get_response("Ok, what have you done with them?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_BACK or action == ACTION_REPEAT:
                    continue

            if state == 2:
                utt, action, state = self.wrap_get_response("Perfect, when did you do it?", state, allowed_actions={ACTION_STOP, ACTION_BACK, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_BACK or action == ACTION_REPEAT:
                    continue

                parsed_datetime = parse.extract_datetime(utt)
                if parsed_datetime is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue
                else:
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

    @intent_file_handler('last-activities.intent')
    def handle_last_activities(self, message):
        done = False
        state = 0
        while not done:
            if state == 0:
                surname_name, action, state = self.wrap_get_response("About whom?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT:
                    continue

                list_contacts = get_all_contacts(surname_name)
                if len(list_contacts)<=0:
                    # the contact does not exist --> exit
                    self.speak("I don't know {}".format(surname_name))
                    return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag=0
                    for i in range(len(list_contacts)):
                        if (list_contacts[i]['nickname'] is None):
                            identikit='no'
                        else:
                            identikit = self.ask_yesno(f"Did you mean {surname_name}, {list_contacts[i]['nickname']}?")
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            list_contacts[0] = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            continue
                        else:
                            continue
                    if flag==0:
                        self.speak_dialog('sorry I did not find your contact')
                        return
                if len(list_contacts[0]['activities']) == 0:
                    self.speak("You have not any activities with {}".format(surname_name))
                    return
                numberOfActivities=len(list_contacts[0]['activities'])-1 # the position in the list of the activity to read
                nextStep='repeat'                                        # continue, repeat, back, exit
                contStep=0                                               # already done steps
                responseList = ['repeat', 'continue', 'exit']
                while nextStep!='exit':
                    contStep+=1
                    for i in range(5):
                        if numberOfActivities<0:
                            self.speak("you have no other activities with this contact")
                            break  
                        else:
                            activity = list_contacts[0]['activities'][numberOfActivities]['activity']
                            datetime = list_contacts[0]['activities'][numberOfActivities]['date']
                            if datetime.hour == 0 and datetime.minute == 0:
                                self.speak(f"{activity} at {nice_date(datetime)}")
                            else:
                                self.speak(f"{activity} at {nice_date_time(datetime)}")
                            numberOfActivities-=1
                    
                    # ask and handle the next step
                    nextStep=None
                    responseList = updateResponseList(contStep, numberOfActivities)
                    while nextStep not in responseList:
                        nextStep = self.ask_selection(responseList, f"What do you want to do?")
                    if nextStep=='repeat':
                        numberOfActivities=len(list_contacts[0]['activities'])-1-((contStep-1)*5)
                        contStep-=1
                    elif nextStep=='back':
                        numberOfActivities=len(list_contacts[0]['activities'])-1-((contStep-2)*5)
                        contStep-=2
                
                self.speak("Great! I have done!")
                done = True

def create_skill():
    return VoiceCRM()