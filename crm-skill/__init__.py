from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse
from itertools import permutations

from .constants import *

contacts = [
    {
        "name": "jo",
        "surname": "peter",
        "birth_date": "1996-01-01",
        "activities": [ {"activity": "bar", "date": "2021-05-04"},
                        {"activity": "cinema", "date": "2021-03-01"}, 
                        {"activity": "nada","date": "2021-04-04"} ],
        "reminders": []
    }
]

def get_contact(name, surname):
    ''' return all contacts with name and surname '''
    return list(filter(lambda contact: contact["name"] == name and contact["surname"] == surname, contacts))

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

def name_surname(s):
    ''' return all possible combination of name-surname'''
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

    def wrap_get_response(self, question, state, exact_match=False, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK}):
        '''
        Wraps the self.get_response method with logic to simplify handling multiple states of a specific task.
        Returns (utterance; user-specified action; next state, based on the action)
        '''
        utt = self.get_response(question)
        if allowed_actions is not None:
            for action in allowed_actions:
                if self.voc_match(utt, action, exact=exact_match):
                    state = state - 1 if action == ACTION_BACK else state
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
                gender, action, state = self.wrap_get_response("What is the gender?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT})
                if action is None:
                    contact["gender"] = gender
                    self.speak(f"{gender}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                elif action == ACTION_REPEAT:
                    continue

            if state == 5:
                birth_date, action, state = self.wrap_get_response("Birth date?", state, allowed_actions={ACTION_STOP, ACTION_REPEAT, ACTION_BACK})
                if action is None:
                    contact["birth-date"] = parse.extract_datetime(birth_date)
                    self.speak(f"{birth_date}, done")
                elif action == ACTION_STOP:
                    self.speak_dialog("finishing")
                    return
                elif action == ACTION_REPEAT or action == ACTION_BACK:
                    continue

            if state == 6:
                self.speak_dialog("finishing")
                done = True

    @intent_file_handler('add-reminder.intent')
    def handle_new_reminder(self, message):
        surname_name = self.get_response("About whom?")
        list_contacts = find_contacts(surname_name) # we get all possible contact
        if len(list_contacts)<=0:
            # the contact does not exist. We create it, calling task 1, and then we continue adding the reminder
            should_proceed = self.ask_yesno(f"The contact you call not exist. So, do you want to add it?")
            if should_proceed == 'yes':
                self.handle_new_contact(message)
                list_contacts = find_contacts(surname_name) # we get the contact
            else: return
        elif len(list_contacts)>1:
            # there are more than one contact. We select the final contact by the set
            return

        activity = self.get_response("What should I remind you?")
        date = parse.extract_datetime(self.get_response("When should I remind you?"))
        add_reminder(list_contacts[0],activity,date)

        self.speak("Great! I have added your reminder for {}".format(surname_name))

    @intent_file_handler("new-activity.intent")
    def handle_new_activity(self, message):
        if message.data.get("person") != None:
            person = message.data.get("person")
        else:
            person = self.get_response("whith whom you have done this activity?")
        list_contacts = find_contacts(person)
        if len(list_contacts) == 0:
            should_proceed = self.ask_yesno(f"Hey, I don't know {person}. Do you want to add them?")
            if should_proceed == 'yes':
                self.handle_new_contact(message)
                contact = find_contacts(person)
            else:
                self.speak("Ok, I'm here if you need.")
                return
        else:
            contact = list_contacts[0]
        
        activity = self.get_response("Ok, what have you done with them?")
        date = parse.extract_datetime(self.get_response("Perfect, when did you do it?"))
        contact["activities"].append({
            "activity": activity,
            "date": date
        })
    
        self.speak("Awesome, done!")

    @intent_file_handler('last-activities.intent')
    def handle_last_activities(self, message):
        surname_name = self.get_response("About whom?")
        if surname_name==None:
            self.speak('TROPPO TEMPO')
            return
        list_contacts = find_contacts(surname_name) # we get all possible contact
        if len(list_contacts)<=0:
            # the contact does not exist. We exit
            self.speak("{} does not exist! Tell me another command".format(surname_name))
            return
        elif len(list_contacts)>1:
            # there are more than one contact. We select the final contact by the set
            # the final contact is set into list_contacts[0]
            return
        if len(list_contacts[0]['activities'])==0:
            self.speak("You have not any activities with {}. Ok, tell me another command".format(surname_name))
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

def create_skill():
    return VoiceCRM()
