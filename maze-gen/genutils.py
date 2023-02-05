import random

def remove_constraints(constraints, dc):
    curr = len(constraints)
    rm = (curr*(1-dc))/100 
    while rm > 0:
        r = random.choice(list(constraints.keys()))
        constraints.pop(r)
        rm -= 1

def coshuffle(list1,list2):
    temp = list(zip(list1,list2)) #shuffle groups and vars together
    random.shuffle(temp)
    r1, r2 = zip(*temp)
    return list(r1), list(r2)

def parse_transformations(t_type):
    transformations = t_type.split('_')
    shuffle = False
    dc = 0
    for t in transformations:
        if t == 'sh':
            shuffle = True
        if t.startswith('dc'):
            dc = int(t[2:])
    return {'sh': shuffle, 'dc': dc}
