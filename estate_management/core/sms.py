import requests




url = "https://d7sms.p.rapidapi.com/secure/send"

payload = "{\r\n    \"content\": \"Your entry code is {}\",\r\n    \"from\": \"Boris\",\r\n    \"to\": {guest.telephone}\r\n}"
headers = {
    'content-type': "application/json",
    'authorization': "Basic d3lzbjEwMzM6amlibHN5T1A=",
    'x-rapidapi-key': "054171df22msh5cc95a48a99828dp1dad02jsn20d65ecad36a",
    'x-rapidapi-host': "d7sms.p.rapidapi.com"
    }

response = requests.request("POST", url, data=payload, headers=headers)

print(response.text)
