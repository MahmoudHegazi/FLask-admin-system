import phonenumbers
from estate_management import twilio_sid, twilio_token, twilio_number, Client


def valdiate_phone(phone):
    valid_phone = True
    try:
        submitted_number = str(phone)
        valdaite_num = phonenumbers.parse(submitted_number)
        if phonenumbers.is_valid_number(valdaite_num) == False:
            valid_phone = False
    except:
        valid_phone = False
    finally:
        return valid_phone
    return valid_phone

def did_you_send_notification(phonenumber, message="We could not send the valid message for you contact support", extra=['code', 'guest']):
    try:
        client = Client(twilio_sid, twilio_token)
        phonenumber_parsed = phonenumbers.parse(phonenumber, None)
        check_before_send = phonenumbers.is_valid_number(phonenumber_parsed) and phonenumbers.is_possible_number(phonenumber_parsed)
        if check_before_send:
            thephonenumber = phonenumbers.format_number(phonenumbers.parse(str(phonenumber),None), phonenumbers.PhoneNumberFormat.E164)
            client.api.account.messages.create(
            to=thephonenumber,
            from_=twilio_number,
            body=message)
            return {'sent': True, 'message': 'The {} has been sent to the {} successfully'.format(extra[0], extra[1])}
        else:
            return {'sent': False, 'message': 'An error occurred while sending the notification to the {} (Twilio error code:002)'.format(extra[1])}
    except Exception as e:
        return {'sent': False, 'message': str(e)}
    return {'sent': False, 'message': 'An unexpected error occurred while sending a notification message to the {}'.format(extra[1])}
