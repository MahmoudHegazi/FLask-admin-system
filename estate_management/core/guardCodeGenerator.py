import random

strpool = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

def code_generator(string):
    confirmationCode = ''
    for i in range(6):
        confirmationCode += string[random.randint(0,len(string)-1)]
    return confirmationCode

def unique_code_generator1(string, banned_list=[]):
    confirmationCode = ''
    while confirmationCode in banned_list or confirmationCode == '':
        for i in range(6):
            confirmationCode += string[random.randint(0,len(string)-1)]
    return confirmationCode

#print(code_generator(strpool))
