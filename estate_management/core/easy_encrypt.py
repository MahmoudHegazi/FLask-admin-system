import random

def encrypt(data, salt):
    try:
        # generate salt here
        # salt = random.randint(10000000, 99999999)
        # for morse secuirty use same salt with any avail library to encrypt the full value
        lenstr = len(data)
        random_range = data[1:len(data) - 3]
        the_real_random =  int(random.choice(range(len(random_range))))
        string_list = list(data)
        dumy_value = random.randint(2, 1546458)
        fake_random = int(((lenstr * salt) / 2) + the_real_random)
        string_list.insert(the_real_random, str(dumy_value))
        string1 = "".join(string_list)
        splited_random_list = string1.split(str(dumy_value))
        part1 = splited_random_list[0]
        part2 = splited_random_list[0]
        encrypted = splited_random_list[0][::-1] + splited_random_list[1][::-1] + "--" + str(fake_random)
        return encrypted
    except:
        return None

def decrypt(req_parameter, salt):
    try:
        full_data = req_parameter.split("--")
        fake_random = int(full_data[1])
        lenstr = len(str(full_data[0]))
        formala_num = int((lenstr * salt) / 2)
        the_real_random = int(fake_random - formala_num)
        string_list = list(req_parameter.split("--")[0])
        dumy_value = random.randint(2, 1546458)
        string_list.insert(the_real_random, str(dumy_value))
        string1 = "".join(string_list)
        splited_random_list = string1.split(str(dumy_value))
        return splited_random_list[0][::-1] + splited_random_list[1][::-1]
    except:
        return None

# this dynamic function will get string and separator and convert to dict
# can used for other parts and dynamic and handle all errors
def give_me_valid_object(data, separator):
    try:
        if separator not in data:
            return {}
        data_splited = data.strip().split(separator)
        if len(data_splited) < 2:
            return {}
        new_object = {}
        for item in data_splited:
            item_splited = item.split("=")
            if len(item_splited) > 1:
                new_object[item_splited[0]] = item_splited[1]
        return new_object
    except:
        return {}
# print(decrypt(encrypt(), salt))
