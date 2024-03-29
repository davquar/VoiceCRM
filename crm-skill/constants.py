# TASK STATE
ACTION_STOP = "stop"
ACTION_BACK = "back"
ACTION_REPEAT = "repeat"
ACTION_SKIP = "skip"

# RELATIONSHIPS
RP_FRIEND = "friend"
RP_SPOUSE = "spouse"
RP_PARTNER = "partner"
RP_COLLEAGUE = "colleague"
RP_COLLABORATOR = "collaborator"
RP_SON = "son"
RP_PARENT = "parent"
RP_SIBLING = "sibling"
RP_COUSIN = "cousin"

RP_INVERSE = {
    RP_FRIEND: RP_FRIEND,
    RP_SPOUSE: RP_SPOUSE,
    RP_PARTNER: RP_PARTNER,
    RP_COLLEAGUE: RP_COLLEAGUE,
    RP_COLLABORATOR: RP_COLLABORATOR,
    RP_SON: RP_PARENT,
    RP_PARENT: RP_SON,
    RP_SIBLING: RP_SIBLING,
    RP_COUSIN: RP_COUSIN
}

RP_INCOMPATIBLES = [RP_SPOUSE, RP_PARENT, RP_SON, RP_PARENT, RP_SIBLING, RP_COUSIN]
