import random

strpool = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890'

def code_generator(string):
    confirmationCode = ''
    for i in range(6):
        confirmationCode += string[random.randint(0,len(string)-1)]
    return confirmationCode

#print(code_generator(strpool))
