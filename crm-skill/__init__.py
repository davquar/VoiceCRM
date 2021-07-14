from mycroft import MycroftSkill, intent_file_handler
from mycroft.util import parse

contacts = [
    {
        "name": "john",
        "surname": "red",
        "birth_date": "1996-01-01",
        "activities": []
    }
]

def get_contact(name, surname):
    return list(filter(lambda contact: contact["name"] == name and contact["surname"] == surname, contacts))

def add_contact(name, surname):
    contacts.append({
        "name": name,
        "surname": surname
    })

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

def create_skill():
    return VoiceCRM()