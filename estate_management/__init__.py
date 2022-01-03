import os
from flask import Flask, url_for, redirect, session, flash, jsonify, request
from flask_login import current_user
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, current_user, logout_user, login_required
#from flask_security import Security, SQLAlchemyUserDatastore, \
#    UserMixin, RoleMixin, login_required, current_user
from flask_security.utils import encrypt_password
from .config import LANGUAGES
import flask_admin as estate_admin
import flask_admin as admin
from flask_admin.contrib.sqla import ModelView
from flask_admin import *
from flask_babelex import Babel, gettext
from flask_admin.contrib.fileadmin import FileAdmin
from flask_principal import Principal, Permission, RoleNeed, identity_loaded, UserNeed, AnonymousIdentity
import os.path as op
import stripe
from flask_admin import Admin
from twilio.rest import Client
import rncryptor

stripe_key = 'pk_test_6pRNASCoBOKtIshFeQd4XMUh'
stripe.api_key = "sk_test_BQokikJOvBiI2HlWgH4olfQ2"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
cryptor = rncryptor.RNCryptor()

# This required system variables to send messages
# note you have to setup this variables and export before start the server
# for the first time or restart the the server if u on cloud
twilio_sid = os.environ['TWILIO_SID']
twilio_token = os.environ['TWILIO_TOKEN']
twilio_number = os.environ['TWILIO_NUMBER']

print(twilio_sid)
print(twilio_token)

#app.config['SECURITY_RECOVERABLE'] = True
#app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024
#app.config['UPLOAD_EXTENSIONS'] = ['.jpeg', '.jpg', '.png']
#app.config['UPLOAD_FOLDER'] = '/static/profile_pics'

static_path = op.join(op.dirname(__file__), 'static')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///'+os.path.join(basedir,'data.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = True



db = SQLAlchemy(app)
#db.drop_all()

Migrate(app,db)


babel = Babel(app)

login_manager = LoginManager()
login_manager.init_app(app)
#babel.init_app(app)
login_manager.login_view = 'core.login'


admin = admin.Admin(name="adminapp")



# this test idea for default database value to add user dynamic
def getMeLoggedUser():
    if current_user and current_user.is_authenticated:
        return current_user.id
    else:
        return None

# Create a permission with a single Need, in this case a RoleNeed.

@login_manager.user_loader
def load_user(userid):
    # Return an instance of the User model
    return datastore.find_user(id=userid)

principals = Principal(app)
admin_permission = Permission(RoleNeed('admin'))
super_admin_permission = Permission(RoleNeed('superadmin'))
estate_admin_permission = Permission(RoleNeed('estateadmin'))
guard_permission = Permission(RoleNeed('guard'))



# this method work with auth to add the role to princple session
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    if not isinstance(identity, AnonymousIdentity):
        identity.provides.add(UserNeed(identity.id))

        # if user is anonymous or is is_authenticated can used too, we add role for it
        # this way to add multible rules for views only not controll app

        """ Note that all administrators have a default role which is the [admin]
            role does not really exist, but it was added at login so that any administrator
            can access the main admin area, but only user with the correct role can access
            the required view, all user has a role Only one main The other rules
            will be default
        """
        if current_user.is_anonymous == False:
            if current_user and current_user.user_role.name == 'superadmin':
                # super admin have all roles but he in main superadmin
                identity.provides.add(RoleNeed('admin'))
                identity.provides.add(RoleNeed('guard'))
                identity.provides.add(RoleNeed('estateadmin'))
                identity.provides.add(RoleNeed('superadmin'))

            if current_user and current_user.user_role.name == 'estateadmin':
                # estate admin can see guards views and will changed to esate next step
                identity.provides.add(RoleNeed('admin'))
                identity.provides.add(RoleNeed('guard'))
                identity.provides.add(RoleNeed('estateadmin'))

            if current_user and  current_user.user_role.name == 'guard':
                identity.provides.add(RoleNeed('admin'))
                identity.provides.add(RoleNeed('guard'))

            if current_user and current_user.user_role.name == 'occupant':
                identity.provides.add(RoleNeed('occupant'))

            if current_user and current_user.user_role.name == 'developer':
                identity.provides.add(RoleNeed('developer'))

            if current_user and current_user.user_role.name == 'temp':
                identity.provides.add(RoleNeed('temp'))







"""
@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    # Set the identity user object
    identity.user = current_user

    # Add the UserNeed to the identity
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))

    # Assuming the User model has a list of roles, update the
    # identity with the roles that the user provides
    if hasattr(current_user, 'roles'):
        theroles = ['superadmin', 'estateadmin', 'guard', 'occupant', 'developer', 'other']
        for role in range(theroles):
            print(role + "\n\n\n\n")
            identity.provides.add(RoleNeed(theroles[role]))
"""

@babel.localeselector
def get_locale():
    if request.args.get('lang'):
        session['lang'] = request.args.get('lang')
    # for automatic select LANGUAGE depend on browser request accept language
    #return request.accept_languages.best_match(list(LANGUAGES.keys()))
    # better to keep user set his own
    return session.get('lang', 'en')


@babel.timezoneselector
def get_timezone():
    user = getattr(g, 'user', None)
    if user is not None:
        return user.timezone


from estate_management.usermodels import User, Guest, Staff, Service, Enquiry, Publication, Subscription, Code

# admin views MVCs




"""

class MyModelView(ModelView):
    def __init__(self, model, session, name=None, category=None, endpoint=None, url=None, **kwargs):
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

        super(MyModelView, self).__init__(model, session, name=name, category=category, endpoint=endpoint, url=url)

    def is_accessible(self):
        # Logic
        return True

admin.add_view(MyModelView(User, session, list_columns=['id', 'name', 'foreign_key']))

class Users(BaseView):
    #def is_accessible(self):
    #    return current_user.is_authenticated
    @expose('/')
    def index(self):
        return self.render('adminusermanger.html')
# admin views MVCs
admin = Admin(app)
#admin.add_view(Users(name='Mange Users', endpoint='', category='Users'))
admin.add_view(ModelView(User, db.session))
"""
#admin.add_view(Users(name='Mange Occupants', endpoint='occupants', category='Users'))
#admin.add_view(Users(name='Mange Guests', endpoint='guests', category='Users'))

#admin.add_view(adminLogin(name='Login'))
#admin.add_view(adminLogOut(name='Logout'))


def getValidExclude(excluded, the_min, the_max):
    int_exclude_list = []
    real_exclude_list = []
    excluded_list = excluded.split(",")
    if len(excluded_list) == 0:
        return []
    for num in excluded_list:
        # professional check for num as python check very noob
        try:
            int(num)/3
            if int(num) not in int_exclude_list:
                int_exclude_list.append(int(num))
        except:
            continue
    for num1 in int_exclude_list:
        if num1 <= the_max and num1 >= the_min:
            real_exclude_list.append(num1)
    return real_exclude_list

# print("Exclude List {} min range {} max range {}".format(getValidExclude(excluded, 1, 3), 1,3))

def giveMeAllHousesList(excluded_string, the_min, the_max):
    result = []
    houses_min = 0
    houses_max = 0
    fixed = False
    try:
        int(the_max) - int(the_min)
    except:
        return []
    houses_min = the_min
    houses_max = the_max
    if houses_min > houses_max:
        houses_min = int(the_max)
        houses_max = int(the_min)
        fixed = True
    elif houses_min == houses_max:
        fixed = True
        return []
    else:
        fixed = False


    realExcludes = getValidExclude(excluded_string, houses_min, houses_max)
    for houseint in range(houses_min, houses_max+1):
        if houseint not in realExcludes:
            result.append(houseint)
            # print("House Number {}".format(houseint))
        else:
            continue
    return result



#admin.add_view(MyView(name='gaurds', endpoint='/gaurds', category='MyView'))

from estate_management.core.userviews import core
from estate_management.admin.adminviews import adminapp




app.register_blueprint(core)
app.register_blueprint(adminapp)




# if you need empty the DB uncomment this
# db.session.commit()   #<--- solution!
# db.drop_all()
# db.create_all()
