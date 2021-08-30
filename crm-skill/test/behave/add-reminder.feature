Feature: add-reminder

  Scenario: add new reminder to an existing contact
    Given an english speaking user
     When the user says "remind me something"
     Then "crm-skill" should reply with dialog from "ask-about-whom.dialog"
     And the user says "elon musk"
     Then "crm-skill" should reply with dialog from "ask-what-remind.dialog"
     And the user says "pay the rent"
     Then "crm-skill" should reply with dialog from "ask-when-remind.dialog"
     And the user says "1 october"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderDate.dialog"
     And "crm-skill" should reply with dialog from "ask-repeat-task-reminder.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"

  Scenario: add new reminder to an existing ambiguous contact
    Given an english speaking user
     When the user says "remind me something related to michael jordan"
     Then "crm-skill" should reply with dialog from "similar-contacts-wname.dialog"
     And "crm-skill" should reply with dialog from "ask-disambiguate-contact.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-what-remind.dialog"
     And the user says "michael's birthday"
     Then "crm-skill" should reply with dialog from "ask-when-remind.dialog"
     And the user says "tomorrow"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderTomorrow.dialog"
     And "crm-skill" should reply with dialog from "ask-repeat-task-reminder.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"


  Scenario: add new reminder to a new contact
    Given an english speaking user
     When the user says "add a new activity"
     Then "crm-skill" should reply with dialog from "ask-whit-whom.dialog"
     And the user says "joe biden"
     Then "crm-skill" should reply with dialog from "ask-create-contact.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "biden"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "joe"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "new president"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing"
     Then "crm-skill" should reply with dialog from "ask-what-remind.dialog"
     And the user says "super party"
     Then "crm-skill" should reply with dialog from "ask-when-remind.dialog"
     And the user says "25 december"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderDate.dialog"
     And "crm-skill" should reply with dialog from "ask-repeat-task-reminder.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"

  Scenario: add 2 new reminders to an existing contact
    Given an english speaking user
     When the user says "remind me something"
     Then "crm-skill" should reply with dialog from "ask-about-whom.dialog"
     And the user says "elon musk"
     Then "crm-skill" should reply with dialog from "ask-what-remind.dialog"
     And the user says "go to the mall"
     Then "crm-skill" should reply with dialog from "ask-when-remind.dialog"
     And the user says "tomorrow"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderTomorrow.dialog"
     And "crm-skill" should reply with dialog from "ask-repeat-task-reminder.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-what-remind.dialog"
     And the user says "pizza at home"
     Then "crm-skill" should reply with dialog from "ask-when-remind.dialog"
     And the user says "18 september"
     Then "mycroft-reminder" should reply with dialog from "SavingReminderDate.dialog"
     And "crm-skill" should reply with dialog from "ask-repeat-task-reminder.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"


     