from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse
from itertools import permutations

contacts = [
    {
        "name": "john",
        "surname": "red",
        "birth_date": "1996-01-01",
        "activities": [],
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

    @intent_file_handler('new-contact.intent')
    def handle_new_contact(self, message):
        ''' handler per creare un nuovo contatto '''
        surname = self.get_response("what is the surname?")
        name = self.get_response("okay, the name?")
        self.log.info(get_contact(name, surname))
        if len(get_contact(name, surname)) > 0:
           self.speak(f"You already have {name} {surname}. I'll stop here.")
           return
        
        add_contact(name, surname)
        should_proceed = self.ask_yesno(f"Okay, I've added {name} {surname}. Do you want to add other details to them?")
        if should_proceed == "no":
            self.speak("Great! I'll stop here.")
            return

        contact = get_contact(name, surname)[0]
    
        gender = self.get_response("What is the gender?", num_retries=1)
        contact["gender"] = gender
        self.speak(f"{gender}, done")

        birth_date = self.get_response("Birth date?", num_retries=1)
        contact["birth-date"] = parse.extract_datetime(birth_date)
        self.speak(f"{birth_date}, done")

        self.speak("Great! Tell me if you need more.")

    @intent_file_handler('add-reminder.intent')
    def handle_new_reminder(self, message):
        ''' handler per creare un nuovo reminder '''
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
            # the final contact is set into list_contacts[0]
            return

        activity = self.get_response("What should I remind you?")
        date = parse.extract_datetime(self.get_response("When should I remind you?"))
        add_reminder(list_contacts[0],activity,date)

        self.speak("Great! I have added your reminder for {}".format(surname_name))

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
        while nextStep!='exit':
            cont=0 # number of activities read in this step (from 0 to 5)
            for i in range(5):
                cont+=1 # I read an activity
                self.speak("In date {}. {}".format(list_contacts[0]['activities'][numberOfActivities][0],list_contacts[0]['activities'][numberOfActivities][1]))
                numberOfActivities-=1
                if numberOfActivities<0:
                    break # exit from the for
            # now I ask the user if he want to repeat these activities or exit or continue reading
            nextStep=None
            while nextStep not in ['repeat', 'continue', 'exit']:
                nextStep = self.get_response("What will I have to do? Repeat, continue or exit?")
                if nextStep=='repeat':
                    nextStep+=cont
        self.speak("Great! I have done!")



def create_skill():
    return VoiceCRM()