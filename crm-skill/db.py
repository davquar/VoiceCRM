from datetime import datetime, timezone
from .constants import *

contacts = [
    {
        "id": 0,
        "name": "michael",
        "surname": "jordan",
        "nickname": "jordie",
        "birth_date": "",
        "activities": [
            {"activity": "bar", "date": datetime(2021, 4, 5, 21, 0, tzinfo=timezone.utc)},
            {"activity": "phone call to discuss finances", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 3, 26, tzinfo=timezone.utc)}
        ],
        "reminders": [],
        "relationships": set()
    },
    {
	"id": 2,
        "name": "michael",
        "surname": "scott",
        "nickname": "",
        "birth_date": "",
        "activities": [
            {"activity": "paper sales pitch", "date": datetime(2021, 2, 5, 15, 0, tzinfo=timezone.utc)},
            {"activity": "pizza","date": datetime(2021, 4, 1, tzinfo=timezone.utc)}
        ],
        "reminders": [],
        "relationships": set()
    },
    {
        "id": 1,
        "name": "elon",
        "surname": "musk",
        "nickname": "rocket guy",
        "birth_date": "",
        "activities": [
            {"activity": "pizza", "date": datetime(2021, 4, 5, tzinfo=timezone.utc)},
            {"activity": "studying", "date": datetime(2021, 4, 2, tzinfo=timezone.utc)},
            {"activity": "tennis", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "bungee jumping", "date": datetime(2021, 3, 8, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 2, 28, tzinfo=timezone.utc)},
            {"activity": "new year's eve", "date": datetime(2021, 1, 1, tzinfo=timezone.utc)},
        ],
        "reminders": [],
        "relationships": set()
    }
]

last_actions = []

def remove_contact(contact: dict):
    """Remove the contact from the contacts list"""
    index_contact = contacts.index(contact)
    for relationship in contacts[index_contact]["relationships"]:
        other_contact = get_contact_by_id(relationship[0])
        index_other_contact = contacts.index(other_contact)
        for relationship_other_contact in contacts[index_other_contact]["relationships"]:
            if contact['id'] == relationship_other_contact[0]:
                contacts[index_other_contact]['relationships'].remove(relationship_other_contact)
                break
    contacts.remove(contact)
    last_actions.pop(-1)

def remove_activity(contact: dict, index: int):
    """Remove the activty from the activities list"""
    index_contact = contacts.index(contact)
    contacts[index_contact]['activities'].pop(index)
    last_actions.pop(-1)

def remove_reminder(contact: dict):
    """Remove the reminder from the reminders list"""
    index_contact = contacts.index(contact)
    contacts[index_contact]['reminders'].pop(-1)
    last_actions.pop(-1)

def remove_relationship(contact: dict, contact2: dict, found_relationship: str, last_act: bool):
    """Remove the relationship from the relationships lists of contact and contact2"""
    index_contact = contacts.index(contact)
    for relationship in contacts[index_contact]['relationships']:
        if contact2['id'] == relationship[0] and found_relationship == relationship[1]:
            contacts[index_contact]['relationships'].remove(relationship)
            break
    index_contact2 = contacts.index(contact2)
    for relationship in contacts[index_contact2]['relationships']:
        if contact['id'] == relationship[0] and RP_INVERSE[found_relationship] == relationship[1]:
            contacts[index_contact2]['relationships'].remove(relationship)
            break
    if last_act:
        last_actions.pop(-1)

def add_contact(name: str, surname: str, nickname=""):
    """Create new contact with the given name and surname"""
    contacts.append({
        "id": len(contacts),
        "name": name,
        "surname": surname,
        "nickname": nickname,
        "birth_date": "",
        "gender": "",
        "activities": [],
        "reminders": [],
        "relationships": set()
    })

def get_contact_by_id(contact_id: int) -> dict:
    """Returns the (first/only) contact with the given id"""
    for item in contacts:
        if item["id"] == contact_id:
            return item
    return None


def get_contact_by_nickname(nickname: str) -> dict:
    """Returns the (first/only) contact with the given nickname"""
    for item in contacts:
        if item["nickname"] == nickname:
            return item
    return None


def get_contact(name: str, surname: str, nickname: str) -> list:
    """Returns all the contacts with the given name, surname and nickname
    An empty argument means that it should not be considered in the search"""
    return list(
        filter(
            lambda contact: (contact["name"] == name or name == "") and
            (contact["surname"] == surname or surname == "") and
            (contact["nickname"] == nickname or nickname == ""), contacts))


def get_all_name_surname_nick(tokens: list) -> list:
    """Returns (raw) all the contacts which name or surname or nickname (or a combination of them) matches
    the given list of tokens (words from the utterance)"""
    if len(tokens) == 1:
        return [["", "", tokens[0]], ["", tokens[0], "" ], [tokens[0], "", ""]]

    half = len(tokens) // 2
    part1 = get_all_name_surname_nick(tokens[:half])
    part2 = get_all_name_surname_nick(tokens[half:])
    res = []
    for elem1 in part1:
        for elem2 in part2:
            app = []
            flag = -1
            if elem2[0] != "" and elem1[0] != "":
                app.append(elem1[0] + " " + elem2[0])
                flag = 0
            elif elem1[0] != "":
                app.append(elem1[0])
            else:
                app.append(elem2[0])
            if elem2[1] != "" and elem1[1] != "":
                app.append(elem1[1] + " " + elem2[1])
                flag = 1
            elif elem1[1] != "":
                app.append(elem1[1])
            else:
                app.append(elem2[1])
            if elem2[2] != "" and elem1[2] != "":
                app.append(elem1[2] + " " + elem2[2])
                flag = 2
            elif elem1[2] != "":
                app.append(elem1[2])
            else:
                app.append(elem2[2])
            if flag >- 1:
                splitted_elem2 = elem2[flag].split(" ")
                for i in range(len(splitted_elem2)):
                    if " ".join(splitted_elem2[i+1:]) == "":
                        word = " ".join(splitted_elem2[:i+1]) + " " + elem1[flag] + " ".join(splitted_elem2[i+1:])
                    else:
                        word = " ".join(splitted_elem2[:i+1]) + " " + elem1[flag] + " " + " ".join(splitted_elem2[i+1:])
                    app2 = app.copy()
                    app2[flag] = word
                    res.append(app2)
            res.append(app)
    return res


def get_all_contacts(string: str, mycroft) -> (list, str):
    """Wraps all_name_surname_nick.
    Returns both the list of contacts that match the given search string (utterance),
    and the "cleaned" utterance without possible stopwords.
    If the cleaned utterance is empty, return it as is."""
    list_contacts = []
    tokens = remove_stopwords(string.split(" "), mycroft)
    if len(tokens) == 0:
        return list_contacts, string
    result = get_all_name_surname_nick(tokens)
    for item in result:
        list_contacts += get_contact(name=item[0], surname=item[1], nickname=item[2])
    return list_contacts, " ".join(tokens)


def remove_stopwords(tokens: list, mycroft) -> list:
    stopwords_path = mycroft.find_resource("stopwords.voc", "vocab")
    with open(stopwords_path) as file:
        stopwords = file.readlines()
        for idx, word in enumerate(stopwords):
            stopwords[idx] = word[:-1]
        file.close()
    return list(filter(lambda token: token not in stopwords, tokens))


def add_reminder(contact: dict, act: str, date: datetime):
    """Adds the given activity and date to the given contact"""
    contact["reminders"].append({
        "activity": act,
        "date": date
    })


def add_relationship(id1: str, id2: str, rp: str):
    """Adds a relationship between contact with id1 and contact with id2 and vice versa."""
    contact1 = get_contact_by_id(id1)
    contact2 = get_contact_by_id(id2)
    contact1["relationships"].add((id2, rp))
    contact2["relationships"].add((id1, RP_INVERSE[rp]))


def can_add_relationship(id1: str, id2: str, rp: str) -> str:
    """Gets wether this relationship can be added, by returning the possible old relationship if exists.
    The only case that we ban is the addition of another family relationship
    to a contact for which an existing family relationship exists, with the same person.
    For example, A and B cannot be both siblings and cousins"""
    if rp not in RP_INCOMPATIBLES:
        return None

    contact1 = get_contact_by_id(id1)
    contact2 = get_contact_by_id(id2)

    for relationship in contact1["relationships"]:
        if relationship[0] == id2 and relationship[1] in RP_INCOMPATIBLES:
            return relationship[1]
    for relationship in contact2["relationships"]:
        if relationship[0] == id1 and relationship[1] in RP_INCOMPATIBLES:
            return relationship[1]

    return None
