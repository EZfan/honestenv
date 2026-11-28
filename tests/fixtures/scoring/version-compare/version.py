from itertools import zip_longest

def cmp_version(left, right):
    for a, b in zip_longest(map(int, left.split('.')), map(int, right.split('.')), fillvalue=0):
        if a != b:
            return 1 if a > b else -1
    return 0
