from datetime import datetime, timezone
from .constants import *

contacts = [
    {
        "id": 0,
        "name": "michael",
        "surname": "jordan",
        "nickname": "",
        "birth_date": "",
        "activities": [
            {"activity": "bar", "date": datetime(2021, 4, 5, 21, 0, tzinfo=timezone.utc)},
            {"activity": "nada", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 3, 26, tzinfo=timezone.utc)}
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
            {"activity": "cannelloni", "date": datetime(2021, 4, 2, tzinfo=timezone.utc)},
            {"activity": "tennis", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "bungee jumping", "date": datetime(2021, 3, 8, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 2, 28, tzinfo=timezone.utc)},
            {"activity": "new year's eve", "date": datetime(2021, 1, 1, tzinfo=timezone.utc)},
        ],
        "reminders": [],
        "relationships": set()
    }
]


def add_contact(name: str, surname: str, nickname=""):
    """Create new contact with the given name and surname"""
    contacts.append({
        "id": len(contacts),
        "name": name,
        "surname": surname,
        "nickname": nickname,
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


def get_all_name_surname_nick(string: str) -> list:
    """Returns (raw) all the contacts which name or surname or nickname (or a combination of them) matches
    the given string """
    lis = string.split(" ")
    if len(lis) == 1:
        return [["", "", lis[0]], ["", lis[0], "" ], [lis[0], "", ""]]

    half = len(lis) // 2
    part1 = get_all_name_surname_nick(" ".join(lis[:half]))
    part2 = get_all_name_surname_nick(" ".join(lis[half:]))
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


def get_all_contacts(string: str) -> list:
    """Wraps all_name_surname_nick"""
    list_contacts = []
    lis = get_all_name_surname_nick(string)
    for item in lis:
        list_contacts += get_contact(name=item[0], surname=item[1], nickname=item[2])
    return list_contacts


def add_reminder(contact: dict, act: str, date: datetime):
    """Adds the given activity and date to the given contact"""
    contact["reminders"].append({
        "activity": act,
        "date": date
    })


def add_relationship(id1, id2, rp):
    """Adds a relationship between contact with id1 and contact with id2 and vice versa."""
    contact1 = get_contact_by_id(id1)
    contact2 = get_contact_by_id(id2)
    contact1["relationships"].add(rp)
    contact2["relationships"].add(RP_INVERSE[rp])
