from mycroft import MycroftSkill, intent_file_handler


class VoiceCRM(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('new-contact.intent')
    def handle_new_contact(self, message):
        self.speak_dialog("ask-surname", expect_response=True)
        resp = self.get_response("ask-surname")
        print("RESPONSE: " + resp)


def create_skill():
    return VoiceCRM()

