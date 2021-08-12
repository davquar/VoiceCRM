from datetime import datetime, timezone

contacts = [
    {
        "name": "jo",
        "surname": "peter",
        "nickname": "baubau",
        "birth_date": "1996-01-01",
        "activities": [ 
            {"activity": "bar", "date": datetime(2021, 4, 5, 21, 0, tzinfo=timezone.utc)},
            {"activity": "nada","date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 3, 26, tzinfo=timezone.utc)}
        ],
        "reminders": []
    },
    {
        "name": "joe",
        "surname": "peter",
        "nickname": "bla bla bla",
        "birth_date": "1996-02-02",
        "activities": [
            {"activity": "pizza", "date": datetime(2021, 4, 5, tzinfo=timezone.utc)},
            {"activity": "cannelloni","date": datetime(2021, 4, 2, tzinfo=timezone.utc)},
            {"activity": "tennis", "date": datetime(2021, 4, 1, tzinfo=timezone.utc)},
            {"activity": "bungee jumping","date": datetime(2021, 3, 8, tzinfo=timezone.utc)},
            {"activity": "cinema", "date": datetime(2021, 2, 28, tzinfo=timezone.utc)},
            {"activity": "new year's eve", "date": datetime(2021, 1, 1, tzinfo=timezone.utc)},
        ],
        "reminders": []
    }
]

def add_contact(name: str, surname: str, nickname=''):
    """Create new contact with the given name and surname """
    contacts.append({
        "name": name,
        "surname": surname,
        "nickname": nickname,
    })

def get_contact_by_nickname(nickname: str) -> dict:
    """Returns the (first/only) contact with the given nickname"""
    for item in contacts:
        if item["nickname"] == nickname:
            return item
    return None

def get_contact(name: str, surname: str, nickname: str) -> list:
    """Returns all the contacts with the given name, surname and nickname
    An empty argument means that it should not be considered in the search"""
    return list(filter(lambda contact: (contact["name"] == name or name=='') and (contact["surname"] == surname or surname=='') and (contact["nickname"] == nickname or nickname==''), contacts))

def all_name_surname_nick(s: str) -> list:
    """Returns (raw) all the contacts which name or surname or nickname (or a combination of them) matches the given string"""
    lis=s.split(' ')
    if len(lis)==1:
        return [['','',lis[0]],['',lis[0],''],[lis[0],'','']]
    else:
        n=len(lis)//2
        a1=all_name_surname_nick(' '.join(lis[:n]))
        a2=all_name_surname_nick(' '.join(lis[n:]))
        res=[]
        for e1 in a1:
            for e2 in a2:
                app=[]
                flag = -1
                if e2[0]!='' and e1[0]!='':
                    app.append(e1[0]+' '+e2[0])
                    flag=0
                elif e1[0]!='':
                    app.append(e1[0])
                else:
                    app.append(e2[0])
                if e2[1]!='' and e1[1]!='':
                    app.append(e1[1]+' '+e2[1])
                    flag=1
                elif e1[1]!='':
                    app.append(e1[1])
                else:
                    app.append(e2[1])
                if e2[2]!='' and e1[2]!='':
                    app.append(e1[2]+' '+e2[2])
                    flag=2
                elif e1[2]!='':
                    app.append(e1[2])
                else:
                    app.append(e2[2])
                if flag>-1:
                    splittedE2 = e2[flag].split(' ')
                    for i in range(len(splittedE2)):
                        if ' '.join(splittedE2[i+1:])=='':
                            word=' '.join(splittedE2[:i+1])+' '+e1[flag]+' '.join(splittedE2[i+1:])
                        else:
                            word=' '.join(splittedE2[:i+1])+' '+e1[flag]+' '+' '.join(splittedE2[i+1:])
                        app2=app.copy()
                        app2[flag]=word
                        res.append(app2)
                res.append(app)
        return res

def get_all_contacts(s: str) -> list:
    """Wraps all_name_surname_nick"""
    list_contacts = []
    lis=all_name_surname_nick(s)
    for l in lis :  
        list_contacts += get_contact(l[0], l[1], l[2])
    return list_contacts

def add_reminder(contact: dict, act: str, date: datetime):
    """Adds the given activity and date to the given contact"""
    contact['reminders'].append({'activity':act,'date':date})