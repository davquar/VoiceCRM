Feature: new-contact

  Scenario: add new contact with only basic info (name, surname and nick) 
    Given an english speaking user
     When the user says "add a new contact"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "white"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "walter"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "heisenberg"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "finishing.dialog"

  Scenario: add new contact with complete info 
    Given an english speaking user
     When the user says "add a new contact"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "thompson"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "jon"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "tommy"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-gender.dialog"
     And the user says "male"
     Then "crm-skill" should reply with dialog from "ask-birth-date.dialog"
     And the user says "8 April 1987"
	 Then "crm-skill" should reply with dialog from "end-new-contact.dialog"

   Scenario: add new contact with name and surname already in the contact list 
    Given an english speaking user
     When the user says "add a new contact"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "white"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "walter"
     Then "crm-skill" should reply with dialog from "similar-contacts-wname.dialog"
     And "crm-skill" should reply with dialog from "ask-disambiguate-contact.dialog"
     And the user says "no"
     Then "crm-skill" should reply with dialog from "ask-sure-another-person.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "boss"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-gender.dialog"
     And the user says "male"
     Then "crm-skill" should reply with dialog from "ask-birth-date.dialog"
     And the user says "4 March 1968"
	 Then "crm-skill" should reply with dialog from "end-new-contact.dialog"

   Scenario: add new contact with birthdate in the future
    Given an english speaking user
     When the user says "add a new contact"
     Then "crm-skill" should reply with dialog from "ask-surname.dialog"
     And the user says "mourinho"
     Then "crm-skill" should reply with dialog from "ask-name.dialog"
     And the user says "jose"
     Then "crm-skill" should reply with dialog from "ask-nickname.dialog"
     And the user says "special one"
     Then "crm-skill" should reply with dialog from "contact-added-ask-details.dialog"
     And the user says "yes"
     Then "crm-skill" should reply with dialog from "ask-gender.dialog"
     And the user says "male"
     Then "crm-skill" should reply with dialog from "ask-birth-date.dialog"
     And the user says "9 December 2102"
	 Then "crm-skill" should reply with dialog from "error-datetime-future.dialog"
	 And "crm-skill" should reply with dialog from "ask-birth-date.dialog"
	 And the user says "9 December 1982"
	 Then "crm-skill" should reply with dialog from "end-new-contact.dialog"

	 