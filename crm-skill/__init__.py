from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse
from itertools import permutations

from .constants import *

contacts = [
    {
        "name": "jo",
        "surname": "peter",
        "nickname": "baubau",
        "birth_date": "1996-01-01",
        "activities": [ {"activity": "bar", "date": "2021-05-04"},
                        {"activity": "cinema", "date": "2021-03-01"}, 
                        {"activity": "nada","date": "2021-04-04"} ],
        "reminders": []
    },
    {
        "name": "joe",
        "surname": "peter",
        "birth_date": "1996-02-02",
        "activities": [],
        "reminders": []
    }
]

def get_contact(name, surname):
    ''' return all contacts with name and surname '''
    return list(filter(lambda contact: contact["name"] == name and contact["surname"] == surname, contacts))

def get_contact_wnick(name, surname, nickname):
    ''' return all contacts with name, surname and nickname '''
    return list(filter(lambda contact: contact["name"] == name and contact["surname"] == surname and contact["nickname"] == nickname, contacts))

def add_contact(name, surname):
    ''' create new contact with name and surname '''
    contacts.append({
        "name": name,
        "surname": surname
    })

def find_contacts(s):
    ''' return all contact with name/surname or surname-name s (name and surname are divided by space) '''
    list_contacts = []
    list_name_surname = name_surname(s)
    for l in list_name_surname :  
        list_contacts += get_contact(l[0], l[1])
    return list_contacts

def find_contacts_wnick(s):
    list_contacts = []
    list_name_surname = name_surname_nick(s)
    for l in list_name_surname :  
        list_contacts += get_contact_wnick(l[0], l[1], l[2])
    return list_contacts

def name_surname(s):
    ''' return all possible combination of name-surname'''
    perms = list(permutations(s.split(' ')))
    res = []
    for el in perms:
        for i in range(len(el)-1):
            res.append([' '.join(el[:i+1]),' '.join(el[i+1:])])
    return res

'''da fare'''
def name_surname_nick(s):
    ''' return all possible combination of name-surname-nick'''
    perms = list(permutations(s.split(' ')))
    res = []
    for el in perms:
        for i in range(len(el)-1):
            res.append([' '.join(el[:i+1]),' '.join(el[i+1:])])
    return res

def add_reminder(contact,act,date):
    contact['reminders'].append({'activity':act,'date':date})

class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def wrap_get_response(self, question, state, exact_match=False, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK, ACTION_SKIP}):
        '''
        Wraps the self.get_response method with logic to simplify handling multiple states of a specific task.
        Returns (utterance; user-specified action; next state, based on the action)
        '''
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
                self.log.info(get_contact(name, surname))
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    continue
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if len(get_contact(name, surname)) > 0:
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
                contact = get_contact(name, surname)[0]
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
                    
                    
             '''da rivedere se nickname è opzionale o no. Se si, chiede se ha un nickname, se non lo ha il campo rimane vuoto'''
             '''vedere anche se il nickname è gia usato da altro contatto'''
              '''nickname = self.get_response("What is the nickname?", num_retries=1)
              contact["nickname"] = nickname
              self.speak(f"{nickname}, done")'''

            if state == 6:
                self.speak_dialog("finishing")
                done = True

    @intent_file_handler('add-reminder.intent')
    def handle_new_reminder(self, message):
        done = False
        state = 0
        while not done:
            self.log.info("STATE: {}".format(state))
            if state == 0:
                surname_name, action, state = self.wrap_get_response("About whom?", state, allowed_actions={ACTION_REPEAT, ACTION_STOP})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT:
                    continue

                list_contacts = find_contacts(surname_name) # we get all possible contact
                if len(list_contacts)<=0:
                    # the contact does not exist. We create it, calling task 1, and then we continue adding the reminder
                    should_proceed = self.ask_yesno(f"The contact you call not exist. So, do you want to add it?")
                    if should_proceed == 'yes':
                        self.handle_new_contact(message)
                        list_contacts = find_contacts(surname_name) # we get the contact
                    else: return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag=0
                    for i in range(len(list_contacts)):
                        if (list_contacts[i]['nickname'] is None):
                            identikit='no'
                        else:
                            identikit = self.ask_yesno(f'Did you mean {surname_name}, {list_contacts[i]['nickname']}?')
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            list_contacts[0] = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            self.speak_dialog('')
                        else:
                            self.speak_dialog('')
                    if flag==0
                        self.speak_dialog('sorry I did not find your contact')
                        return

            if state == 1:
                activity, action, state = self.wrap_get_response("What should I remind you?", state, allowed_actions={ACTION_STOP, ACTION_BACK, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    self.log.info("SAID REPEAT OR BACK!!")
                    continue
                
            if state == 2:
                utt, action, state = self.wrap_get_response("When should I remind it to you?", state, allowed_actions={ACTION_STOP, ACTION_BACK, ACTION_REPEAT})
                if action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                if action == ACTION_REPEAT or action == ACTION_BACK:
                    continue

                date = parse.extract_datetime(utt)
                if date is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue
                add_reminder(list_contacts[0], activity, date)
                self.speak("Great! I have added your reminder for {}".format(surname_name))
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
                list_contacts = find_contacts(person)
                if len(list_contacts) == 0:
                    should_proceed = self.ask_yesno(f"Hey, I don't know {person}. Do you want to add them?")
                    if should_proceed == 'yes':
                        self.handle_new_contact(message)
                        contact = find_contacts(person)
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
                            identikit = self.ask_yesno(f'Did you mean {person}, {list_contacts[i]['nickname']}?')
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            contact = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            self.speak_dialog('')
                        else:
                            self.speak_dialog('')
                    if flag==0
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

                date = parse.extract_datetime(utt)
                if date is None:
                    # no datetime found in the utterance --> repeat
                    self.speak("Hmm, that's not a date")
                    state -= 1
                    continue

                contact["activities"].append({
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

                list_contacts = find_contacts(surname_name) # we get all possible contact
                if len(list_contacts)<=0:
                    # the contact does not exist. We exit
                    self.speak("I don't know {}".format(surname_name))
                    return
                elif len(list_contacts)>1:
                    self.speak(f"I have found {len(list_contacts)} contacts that could satisfy your request")
                    flag=0
                    for i in range(len(list_contacts)):
                        if (list_contacts[i]['nickname'] is None):
                            identikit='no'
                        else:
                            identikit = self.ask_yesno(f'Did you mean {surname_name}, {list_contacts[i]['nickname']}?')
                        if identikit == 'yes':
                            self.speak_dialog('Ok, I get it')
                            list_contacts[0] = list_contacts[i]
                            flag=1
                            break
                        elif identikit == 'no':
                            self.speak_dialog('')
                        else:
                            self.speak_dialog('')
                    if flag==0
                        self.speak_dialog('sorry I did not find your contact')
                        return
                if len(list_contacts[0]['activities'])==0:
                    self.speak("You have not any activities with {}".format(surname_name))
                    return
                numberOfActivities=len(list_contacts[0]['activities'])-1 # the position in the list of the activity I have to read now
                nextStep='repeat' # variable to know if the user want to continue, repeat the latest 5 activities or continue in the past
                cont=0 # number of activities read in this step (from 0 to 5)
                while nextStep!='exit':
                    for i in range(5):
                        if numberOfActivities<0:
                            self.speak("you have no other activities with this contact")
                            break  
                        else:
                            cont+=1 
                            self.speak(f"activity {contacts[0]['activities'][numberOfActivities]['activity']} on date {contacts[0]['activities'][numberOfActivities]['date']}")
                            numberOfActivities-=1
                    # now I ask the user if he want to repeat these activities or exit or continue reading
                    nextStep=None
                    while nextStep not in ['repeat', 'continue', 'exit']:
                        nextStep = self.get_response("What will I have to do? Repeat, continue or exit?")
                        if nextStep=='repeat':
                            numberOfActivities=len(list_contacts[0]['activities'])-1
                            cont=0
                
                self.speak("Great! I have done!")
                done = True

def create_skill():
    return VoiceCRM()
