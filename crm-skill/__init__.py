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

class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('new-contact.intent')
    def handle_new_contact(self, message):
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
        surname_name = self.get_response("About whom?")
        list_contacts = find_contacts(surname_name)
        if( len(list_contacts<=0))
        {  
           #     task1 
        }
        
        elif( len(list_contacts==1))
        {   
             activity = self.get_response("What should I remind you?")

             date = self.get_response("When?")
        }
        else()
        {
             #da vedere, caso in cui si trovano piu contatti
        }

def create_skill():
    return VoiceCRM()
