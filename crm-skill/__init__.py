from mycroft import MycroftSkill, intent_file_handler


class Sample(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('sample.intent')
    def handle_sample(self, message):
        contact = message.data.get('contact')

        self.speak_dialog('sample', data={
            'contact': contact
        })


def create_skill():
    return Sample()

