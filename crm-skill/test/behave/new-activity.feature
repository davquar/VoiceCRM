Feature: new-activity

  Scenario: add new activity to an existing contact
    Given an english speaking user
     When the user says "add a new activity"
     Then "crm-skill" should reply with dialog from "ask-whit-whom.dialog"
     And the user says "elon musk"
     Then "crm-skill" should reply with dialog from "ask-activity.dialog"
     And the user says "walk on the moon"
     Then "crm-skill" should reply with dialog from "ask-nactivity-when.dialog"
     And the user says "yesterday"
     Then "crm-skill" should reply with dialog from "finishing.dialog"

  Scenario: add new activity to an existing ambiguous contact
    Given an english speaking user
     When the user says "add a new activity with michael jordan"
     Then "crm-skill" should reply with dialog from "similar-contacts-wname.dialog"
     And "crm-skill" should reply with dialog from "ask-disambiguate-contact.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "ask-disambiguate-contact.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-activity.dialog"
     And the user says "play basketball"
     Then "crm-skill" should reply with dialog from "ask-nactivity-when.dialog"
     And the user says "3 July"
     Then "crm-skill" should reply with dialog from "finishing.dialog"

  Scenario: add new activity to a new contact
    Given an english speaking user
     When the user says "add a new activity"
     Then "crm-skill" should reply with dialog from "ask-whit-whom.dialog"
     And the user says "barack obama"
     Then "crm-skill" should reply with dialog from "ask-create-contact.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "obama"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "barack"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "mister president"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"
     And "crm-skill" should reply with dialog from "ask-activity.dialog"
     And the user says "play golf"
     Then "crm-skill" should reply with dialog from "ask-activity-when.dialog"
     And the user says "8 July 2020"
     Then "crm-skill" should reply with dialog from "finishing.dialog"