# FLask-admin-system
The complete flask admin system is here, you can find anything you need in flask-admin, almost all parts are covered + some custom Python and javascript functions, admin area has 3 rules accessible, super admin can take any action, real estate admin can Take action on his property without adding super admins or other property managers, guardian who can only see guests and login to admin area, everything is protected by flask admin , flask principles and flask login you will find, 'phonenumbers' and 'intl-tel-input'  libraries added to create fancy phone number input, also validate numbers for valuation for any number in all countries and connected to flask admin without html customization to reduce redundancy and overrides of flask-admin and make it a full python admin area, 0 HTML code, only secured valid js added. (For security reasons, the administration area is separated from the main program) , also there is translation for  almost all languages  using flask_babelex (Babel) (The translation for all languages is on the main system components, any aditonal or html text can be added to flask babel but you need to select the language and define the translations by yourself, very easy step you will find examples of 4 languages)


# Main Libraries
1. Flask-admin
2. Flask-principles
3. Flask-login
4. Flask-WTF
5. phonenumbers
6. flask_babelex
7. sqlalchemy

# Database
* SQLite

# admin endpoint:
1. localhost:[port]/admin

# what I need to use this app
1. python 1+ year experince
2. Experience of JavaScript is required to customize or understand some views
3. sqlalchemy experince and SQLite
4. Flask-WTF

# new features
1. phone number library connected to flask admin and with it intl-tel-input also all this added by python and javascript not HTML which will not be found on google
2. custom housenumber exclude and range list professional way To reduce repetition which can with 1 database record define all house numbers for single street also it have multiselect input that allow to accept any excluded number also supported by python function to pass any errors like Letters, heighr than max, less than min, also it use javaScript and async to load the house numbers onload for edit, or when street changes and load the new house numbers added with checks using python and javaScript to ensure it run only in the right view.

## admin view 

(protect for super admin)
![image](https://user-images.githubusercontent.com/55125302/146686030-7577e500-088b-4339-a262-16765ae8ad5f.png)

![image](https://user-images.githubusercontent.com/55125302/146686979-ee7f9cbe-75c7-4fe8-beae-6658b9926a93.png)



#### Developed By Python King

