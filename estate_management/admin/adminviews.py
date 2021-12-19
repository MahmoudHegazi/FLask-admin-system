from flask import render_template,make_response,current_app,jsonify, request, flash, redirect, url_for, Blueprint, session
from flask_login import login_user, current_user, logout_user, login_required
from estate_management.core.userforms import UserForm, GuestForm, StaffForm, ServiceForm, LoginForm, EnquiryForm, NewsForm, SubscriptionForm, UpdateUserForm, CodeForm, GeneratorForm
from estate_management.usermodels import User,Role, Estate, Guest, Staff, Service, Enquiry, Publication, Subscription, Code, StreetsMetadata
from estate_management.core.picture_handler import add_profile_pic
from estate_management import db, stripe_key
from estate_management import babel as b
#from flask_babel import gettext, ngettext
from flask_babelex import gettext, ngettext
import stripe
import flask_admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.contrib import sqla
from flask_admin import BaseView, expose
from flask_admin.menu import MenuLink
from flask_admin import *
from estate_management import app, static_path, db, SQLAlchemy, babel
from datetime import date
from flask_admin.model import typefmt
from flask_admin.model.template import macro
from flask_wtf import FlaskForm
from flask_wtf import Form
from wtforms.widgets import TextArea, PasswordInput
from werkzeug.datastructures import MultiDict
from wtforms.fields.html5 import DateField
from wtforms import SubmitField, HiddenField,StringField, TextAreaField,BooleanField, TextField, IntegerField, DateTimeField, PasswordField, RadioField, SelectMultipleField, ValidationError,SelectField, widgets, FileField
from wtforms.validators import Required as required, Length, AnyOf, ValidationError
from flask_admin.form import SecureForm, rules
from estate_management.admin.code_gen import unique_code_generator, strpool
from flask_babel import lazy_gettext
from flask_admin.contrib.fileadmin import FileAdmin
from redis import Redis
from flask_admin.contrib import rediscli
import os.path as op
from flask_babelex import Babel
from werkzeug.security import generate_password_hash, check_password_hash
from estate_management import super_admin_permission, estate_admin_permission, admin_permission, guard_permission
from flask_admin.form import Select2Widget
from wtforms.utils import unset_value
from flask_admin.form.fields import Select2TagsField
from sqlalchemy import func
from flask_admin.model.template import TemplateLinkRowAction
from sqlalchemy import and_, or_, not_
import phonenumbers

"""Helper functions"""
# expose the main home view for admin page to control the page and add data protect it with admin premssion
# why this miror due to diffrent admin app has more admins and diffrent render instead of reapat all this it function
# and return final secure response can be used in any view render function **kwargs arugments needed access kwargs['key']
def render_miror(self, template, **kwargs):
    kwargs['admin_view'] = self
    kwargs['admin_base_template'] = self.admin.base_template
    kwargs['h'] = helpers
    kwargs['_gettext'] = gettext
    kwargs['_ngettext'] = ngettext
    kwargs['get_url'] = self.get_url
    kwargs['config'] = current_app.config
    kwargs.update(self._template_args)

    response = make_response(render_template(template, **kwargs), 200)
    # this to prevent logout user click back button and see logged admin data
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '-1'
    # Security headers
    # secure that tell browser remeber for 2 years that must accessed by https and subdomans
    response.headers['Strict-Transport-Security'] = 'max-age=63072000; includeSubDomains; preload'
    # enable x-xss filter to prevent XSS attack
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # enable excute inside frame even in current doman
    response.headers['x-frame-options'] = 'DENY'
    response.headers['x-api-version'] = 'F-F-VI'
    response.headers['x-cache-hits'] = '1, 1'
    return response



def getValidExclude(excluded, the_min, the_max):
    int_exclude_list = []
    real_exclude_list = []
    excluded_list = excluded.split(",")
    if len(excluded_list) == 0:
        return []
    for num in excluded_list:
        # professional check for num
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



class MyHomeView(AdminIndexView):
    def render(self, template, **kwargs):
        response = render_miror(self, template, **kwargs)
        return response

    @admin_permission.require(http_exception=403)
    @expose('/')
    def index(self):

        loggeduser = None
        if not current_user.is_anonymous:
            loggeduser = current_user.firstname
        return self.render('admin/index.html', name=loggeduser)

adminapp = Blueprint('adminapp',__name__, template_folder='templates.admin')
admin = Admin(app, name='Admin', template_mode='bootstrap4', index_view=MyHomeView())



def formatter(view, context, model, name):
    # `view` is current administrative view
    # `context` is instance of jinja2.runtime.Context
    # `model` is model instance
    # `name` is property name
    """
    return Markup(
        u"<a href='%s'>%s</a>" % (
            url_for('user.edit_view', id=model.users.id),
            model.user
        )
        ) if model.user else u""
    """
    pass

def type_formatter(view, value):
    # `view` is current administrative view
    # `value` value to format
    pass

def date_format(view, value):
    return value.strftime('%d.%m.%Y %H:%M:%S')

MY_DEFAULT_FORMATTERS = dict(typefmt.BASE_FORMATTERS)
MY_DEFAULT_FORMATTERS.update({
        type(None): typefmt.null_formatter,
        date: date_format
    })


from flask_admin.actions import action

class MyModelView(ModelView):
    column_type_formatters = dict()

class AdminModelView(sqla.ModelView):
    form_base_class = SecureForm
    # can_delete = False  # disable model deletion
    # page_size = 50  # the number of entries to display on the list view
    # the premssion (role) who can access
    # @super_admin_permission.require(http_exception=403)
    @admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        response = render_miror(self, template, **kwargs)
        return response

    @admin_permission.require(http_exception=403)
    def is_accessible(self):
        return current_user.is_authenticated
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('core.login', next=request.url))



class SuperAdminModelView(sqla.ModelView):
    form_base_class = SecureForm
    # can_delete = False  # disable model deletion
    # page_size = 50  # the number of entries to display on the list view
    # the premssion (role) who can access
    # @super_admin_permission.require(http_exception=403)
    # note is_accessible return is what important unlike render adding require_premssion will make it unaccessed in the system which will not open the app or may it not render function to have premssion and the role effect the main class itself
    #@super_admin_permission.require(http_exception=403)
    # note guard, estate-admin, superadmin all have admin rule others will not access the parent class

    def is_accessible(self):
        if current_user and current_user.is_anonymous:
            return False
        else:
            return current_user.user_role.name == 'superadmin'

    @super_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        if 'name' in vars(self):
            if str(self.name).lower() in ['guest', 'staff']:
                self.extra_js = [url_for("static", filename="admin/js/users.js"), url_for("static", filename="admin/js/phonenumbers.js"), "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/js/intlTelInput.min.js"]
                self.extra_css = ['https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/css/intlTelInput.css']
        response = render_miror(self, template, **kwargs)
        return response

    def on_model_change(self, form, User, is_created):
        # valdaite phone using phonenumbers library
        if 'name' in vars(self):
            if str(self.name).lower() in ['guest', 'staff']:
                if "telephone" in form and form.telephone.data is not None:
                    try:
                        submitted_number = str(form.telephone.data)
                        valdaite_num = phonenumbers.parse(submitted_number)
                        if not phonenumbers.is_valid_number(valdaite_num):
                            raise ValidationError("invalid number")
                    except:
                        raise ValidationError("invalid number")

    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    # what happend after inccessable user example not logged in or not superadmin for superadmin view
    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('core.login', next=request.url))



import os.path as op




"""
Super Admin Users
"""
@adminapp.after_request
def add_my_headers(response):
    if request.endpoint[:5] == 'admin':
        h = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
             }
        response.headers.extend(h)
        return response
    return response
# Admin Users View (Control Users AdminView)
class AdminUsersView(ModelView):
    search_placeholder = lambda a:'search by st, username, Tel, name'
    # update main view to render js file for any js tasks like toggle password
    # this function handle who will see that view if it return True ok else hide and not give premssion any way it premssion coverd useful for hide
    def is_accessible(self):
        if current_user and current_user.is_anonymous:
            return False
        else:
            return current_user.user_role.name == 'superadmin'
    #    return current_user.user_role.name == 'superadmin' hn5tr3 el zra b2a 3shan choices

    @super_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        """
        using extra js in render method allow use
        url_for that itself requires an app context
        """
        print(User.query.all()[0].telephone)
        # print(db.session.query(Publication).filter(Publication.users.in_(User.query.filter_by(id=1).all)).all())
        #print(db.session.query(Publication, User).filter(Publication.users.id==1).all())
        # solved By Python King
        if 'form' in kwargs and 'streetname' in kwargs['form'] and 'choices' in vars(kwargs['form'].streetname):
            kwargs['form'].streetname.choices = [street.streetname for street in db.session.query(StreetsMetadata).all()]
            kwargs.update(self._template_args)
        self.extra_js = [url_for("static", filename="admin/js/users.js"), url_for("static", filename="admin/js/phonenumbers.js"), "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/js/intlTelInput.min.js"]
        self.extra_css = ['https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/css/intlTelInput.css']
        response = render_miror(self, template, **kwargs)
        return response
        #return super(AdminUsersView, self).render(template, **kwargs)
    # Add Custom Functions To the model aprove or anything
    @action('approve', 'Approve', 'Are you sure you want to approve selected users?')
    def action_approve(self, ids):
        count = 0
        try:
            query = User.query.filter(User.id.in_(ids))
            for user in query.all():
                print(user)
                count += 1
            flash('User was successfully approved {} users were successfully approved'.format(count))

        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash('Failed to approve users. {}'.format(error))

    # edit types format like date
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    # add custom edit template
    edit_template = '/admin/test.html'
    list_template = '/admin/test1.html'

    # this means connect to columns when order so if order by firstname , lastname will ordered to
    # column_sortable_list = ('firstname','lastname', ('firstname', 'lastname'))
    # other example single sort mean s
    # column_sortable_list = ('firstname', 'lastname')
    # same ass order by when render so it will order by firstname click arrow to change
    # two sort
    column_default_sort = [('firstname', True), ('lastname', True)]
    column_sortable_list = ('firstname','lastname','registration_date','user_estate','flatnumber','housenumber','user_role','gender','username', 'dateofbirth')

    # create and edit model valdation
    def on_model_change(self, form, User, is_created):
        # valdaite phone using phonenumbers library
        if "telephone" in form and form.telephone.data is not None:
            try:
                submitted_number = str(form.telephone.data)
                valdaite_num = phonenumbers.parse(submitted_number)
                if not phonenumbers.is_valid_number(valdaite_num):
                    raise ValidationError("invalid number")
            except:
                raise ValidationError("invalid number")

        if 'password_hash' in form and form.password_hash.data is not None:
            User.password_hash = generate_password_hash(form.password_hash.data)

        if 'username' in form and form.username.data is not None:
            if form.username.data[0].isdigit():  # Check whether the first digit is a number
                raise ValidationError('Username Cannot start with a number: ({})'.format(form.username.data))
        """
        if 'telephone' in form and form.telephone.data is not None:
            print(str(form.telephone.data))
            if str(form.telephone.data)[0] != '0':
                raise ValidationError('The phone number is invalid, it must start with 0')
            if form.telephone.data and len(form.telephone.data) != 11:
                raise ValidationError('The phone number is invalid, it must be 11 digits long')
        """
           # del form.password
    # Form will now use all the other fields in the model

    # Add our own password form field - call it password2 idea 2 for js validate_choice=False
    form_extra_fields = {
        'streetname': SelectField(
            'streetname',
            coerce=str,
            choices=([street.streetname for street in db.session.query(StreetsMetadata).all()]),
            render_kw={'onchange': "myFunction()"},
            validate_choice=True
            ),
        }
    # inline editable fildes
    column_editable_list = ['firstname','gender','lastname', 'streetname', 'flatnumber', 'user_role', 'user_estate']

    # over ride inputs types
    form_overrides = {
        'housenumber': IntegerField,
        'dateofbirth': DateField,
        'role': SelectMultipleField,
        'telephone': StringField
    }

    # selectbox from strings good for role
    form_choices = {
    'gender': [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    }

    # wtf forms (required work here)
    form_args = {
            'profile_image': {
            'label': 'Profile Image',
            'validators': [required()]
            },
            'firstname': {
            'label': 'First Name',
            'validators': [required()]
            },
            'lastname': {
            'label': 'Last Name',
            'validators': [required()]
            },
            'dateofbirth': {
            'label': 'Date of Birth',
            'validators': [required(message="You need to enter your date of birth")]
            },
            'streetname': {
            'label': 'Streetname',
            'validators': [required()],
            },
            'username': {
            'label': 'Username',
            'description': 'Username Cannot start with a number',
            'validators': [required()]
            },
            # id used in user.js to add custom toggle
            'password_hash': {
            'label': 'Password',
            'id': 'user_password',
            'validators': [required()]
            },
            'streetname': {
            'label': 'Street name',
            'validators': [required()]
            },
            'housenumber': {
            'label': 'House number',
            'validators': [required(message="House Number Must Be INTEGER")]
            },
            'flatnumber': {
            'label': 'Flat number',
            'validators': []
            },
            'gender': {
            'label': 'Gender',
            'validators': [required()]
            },
            'telephone': {
            'label': 'Telephone',
            'validators': [required()]
            },
            'role': {
            'label': 'Role',
            'validators': [required()]
            },
            'estate': {
            'label': 'Estate',
            'validators': [required()]
            },
    }
    # style and control
    form_widget_args = {
    'streetname': {
        'rows': 1,
        'style': 'color: black'
    }
    }
    # remove these fileds from edit and create
    form_excluded_columns = ['guests', 'staffs', 'services', 'enquiries', 'news', 'subscriptions']
    # open bootstrap modal for create and edit
    # sort columns
    # which columns has filter for example contains gaurd
    column_filters = [User.role, User.estate, User.gender]
    # which columns can used for search
    column_searchable_list = [User.firstname, User.username, User.telephone, User.streetname]

    # Model Controllers
    can_create = True
    can_edit = True
    can_delete = True

    #column_formatters = dict(User.housenumber=macro('render_price'))
    #column_formatters = dict(User.password_hash=lambda v, c, m, p: generate_password_hash(m.password_hash))
    # which columns can be added in create list
    column_create_list = (User.firstname, User.lastname, User.dateofbirth, User.username, User.password_hash, User.streetname, User.housenumber, User.flatnumber, User.gender, User.telephone, User.role, User.estate)







class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()



class CustomBaseFileAdmin(FileAdmin):
    @super_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        """
        using extra js in render method allow use
        url_for that itself requires an app context
        """

        self.extra_js = [url_for("static", filename="admin/js/users.js")]
        response = render_miror(FileAdmin, template, **kwargs)
        return response

# custom view for fileAdmin with secure headers
class FileAdminView(FileAdmin):

    def is_accessible(self):
        if current_user and current_user.is_anonymous:
            return False
        else:
            return current_user.user_role.name == 'superadmin'

    @super_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        # render_miror return response with secure headers to prevent back button used by logout
        response = render_miror(self, template, **kwargs)
        return response
    column_sortable_list = ('name', 'size', 'date')
    rename_modal = True
    # this is default False but if we need modal bootstrap instead of page make it True
    mkdir_modal = False
    upload_modal = False

    # it's not good idea to allow any code files extensions maybe for remote server it usefull and developers work fast
    # allowed_extensions = (upload bat please and excute it and destory t)
    # which file you can edit with this fixed in update of flask_admin due to they not use rb and used r to open file b = binary
    # editable_extensions = tuple('js')

class AdminEstateView(SuperAdminModelView):
    form_excluded_columns = ['user_estate', 'code_estate', 'street_estate']


class AdminGuestsView(SuperAdminModelView):

    form_overrides = {
        'firstname': StringField,
        'telephone': StringField,
    }
    #IntegerField
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    column_filters = ['gender', 'visit_date']
    column_searchable_list = ['firstname', 'lastname', 'telephone']
    column_editable_list = ['firstname', 'lastname']

    column_default_sort = [('visit_date', True)]
    column_sortable_list = ('firstname','lastname', 'visit_date', 'gender', 'telephone')

    column_create_list = ('visit_date', 'firstname', 'lastname', 'gender', 'telephone')
    form_excluded_columns = ['users']
    column_list = ('host', 'visit_date', 'firstname', 'lastname', 'gender', 'telephone')
    """
    form_ajax_refs = {
    'users': {
        'fields': ['id', 'firstname'],
        'page_size': 10
    }
    }
    """
    form_args = {
            'visit_date': {
            'label': 'Visit Date',
            'validators': [required()]
            },
            'firstname': {
            'label': 'First Name',
            'validators': [required()]
            },
            'lastname': {
            'label': 'Last Name',
            'validators': [required()]
            },
            'gender': {
            'label': 'Gender',
            'validators': [required()]
            },
            'telephone': {
            'label': 'Telephone',
            'validators': [required()]
            },
    }
    form_choices = {
    'gender': [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    }


#on_form_prefill(form,id) @super_admin_permission.require(http_exception=403)

class AdminCodeGen(SuperAdminModelView):
    # take care is_created true if it create form so we need to check it to add valdation to create not edit
    def on_model_change(self, form, model, is_created):
        if not current_user.is_anonymous and is_created:
            model.user_id = current_user.id
        else:
            pass
    # sort by two columns first user_id then gendate
    # column_sortable_list = ('user_id','gen_date', ('user_id', 'gen_date'))
    # return the create form and control it before return using super(class, self).create_form
    def create_form(self):
        # (!VIP!) what happend here is intersting, this function called twice when render data
        # and when submit the form and we can add custom valdation if we need by check the gen data if None
        # so it create if not None and has value so it submit
        form = super(AdminCodeGen, self).create_form()
        banned_list = [co.gen_code for co in Code.query.all()]
        gencode = unique_code_generator(strpool, banned_list)
        if 'gen_code' in form and form.gen_code.data is None:
            form.gen_code.data = gencode
        return form
    # @super_admin_permission.require(http_exception=403)
    # return super(AdminCodeGen, self).render(template, **kwargs)
    # callback

    # view Customiztion
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    create_modal = True
    edit_modal = True
    column_filters = ['gen_date', 'user_id', 'gen_code', 'user_estate']
    column_sortable_list = ('id', 'requested_for', 'gen_code', 'gen_date', 'code_estate.id', 'user_id', 'unused')
    column_searchable_list = ['gen_code', 'requested_for', 'user_id', 'gen_date']
    column_editable_list = ['requested_for', 'gen_code', 'user_estate', 'user_role']
    column_create_list = ('requested_for', 'gen_code', 'gen_date', 'user_id', 'user_role')
    form_excluded_columns = ['id', 'unused', 'user']
    column_list = ('id', 'requested_for', 'gen_code', 'gen_date', 'code_role', 'code_estate', 'user_id', 'unused')

    """
    def filter_func():
        return db.session.query(Role).filter_by(name="applicant")

    form_args = {
    "roles": {
        "query_factory": filter_func
        }
    }
    form_choices while change it to string selectfield

    """
    """
    suggest_codes_list = []
    for i in range(5):
        suggest_codes_list.append((code_generator(strpool), code_generator(strpool)))
    form_choices = {"gen_code": suggest_codes_list}
    """
    form_overrides = {
      'gen_code': StringField,
    }

    form_args = {
            'requested_for': {
            'label': 'Requested For',
            'validators': [required()]
            },
            'gen_date': {
            'label': 'Generated Code Date',
            'validators': [required()]
            },
            'user': {
            'label': 'User (Creator)',
            'validators': [required()]
            },
            'code_role': {
            'label': 'User Role',
            'validators': [required()]
            },
            'gen_code': {
            'label': 'Gen Code',
            'validators': [required(), Length(min=6, max=6, message='Invalid code size must be 6')]
            },
            'code_estate': {
            'label': 'User Estate',
            'validators': [required()]
            },
    }




class AdminServiceView(SuperAdminModelView):
    #IntegerField
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    create_modal = True
    edit_modal = True
    column_filters = ['request_date', 'user_id', 'service_requested']
    column_searchable_list = ['id', 'user_id', 'request_date', 'service_requested']
    column_editable_list = ['service_requested', 'user_id', 'request_date']

    column_default_sort = [('request_date', True)]
    column_sortable_list = ('service_requested','user_id', 'request_date', 'request_date', 'id')


    column_create_list = ('service_requested', 'request_date')
    column_list = ('id','requester', 'service_requested', 'request_date')
    form_args = {
            'service_requested': {
            'label': 'Service Requested',
            'validators': [required()]
            },
            'request_date': {
            'label': 'Request Date',
            'id': 'req_date',
            'validators': [required()]
            }
    }



class AdminRoleView(SuperAdminModelView):
    can_delete = False


class AdminStreetMetadataView(SuperAdminModelView):
    form_excluded_columns = ['excluded']
    column_list = ['id','streetname', 'min', 'max', 'excluded', 'street_estate.name']
    column_sortable_list = ('id','streetname', 'min', 'max', 'street_estate.name')
    form_extra_fields = {
        'excluded': Select2TagsField(label='Excluded Numbers')
        }

class AdminSubscriptionView(SuperAdminModelView):
    form_excluded_columns = ['users']
    column_sortable_list = ('subscription','amount', 'subscription', 'subscription_date', 'subscriber')
    column_list = ['subscription','amount', 'subscription', 'subscription_date', 'subscriber']


class AdminStaffView(SuperAdminModelView):


    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    column_filters = ['id', 'user_id', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription']
    column_searchable_list = ['firstname', 'lastname', 'telephone', 'id']
    column_editable_list = ['firstname', 'lastname']
    column_sortable_list = ('id', 'user_id', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription')
    column_list = ('id', 'boss', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription')

    form_choices = {
    'gender': [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    }

admin.add_view(AdminUsersView(User, db.session))
admin.add_view(AdminGuestsView(Guest, db.session))
admin.add_view(AdminCodeGen(Code, db.session))
admin.add_view(AdminServiceView(Service, db.session))
admin.add_view(AdminSubscriptionView(Subscription, db.session))
admin.add_view(AdminStaffView(Staff, db.session))
admin.add_view(SuperAdminModelView(Publication, db.session))
admin.add_view(FileAdminView(static_path, name='Files', category='System'))
admin.add_view(SuperAdminModelView(Role, db.session, category='System'))
admin.add_view(AdminEstateView(Estate, db.session, category='System'))
admin.add_view(AdminStreetMetadataView(StreetsMetadata, db.session, name='Streets', category='System'))




#admin.add_view(rediscli.RedisCli(Redis()))

def formatter(view, context, model, name):
    # `view` is current administrative view
    # `context` is instance of jinja2.runtime.Context
    # `model` is model instance
    # `name` is property name
    pass

"""
Estate Admin Users
"""

"""

class EstateAdminModelView(sqla.ModelView):
    form_base_class = SecureForm
    #can_delete = False  # disable model deletion
    #page_size = 50  # the number of entries to display on the list view
    # the premssion (role) who can access

    def is_accessible(self):
        return current_user.is_authenticated
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('core.login', next=request.url))
"""



class AdminEstateModelView(sqla.ModelView):
    form_base_class = SecureForm
    #can_delete = False  # disable model deletion
    #page_size = 50  # the number of entries to display on the list view
    # the premssion (role) who can access
    def is_accessible(self):
        if current_user and current_user.is_anonymous:
            return False
        else:
            allowed_rules = ['superadmin', 'estateadmin']
            return current_user.user_role.name in allowed_rules

    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        if current_user.is_anonymous:
            flash("Please Login First")
            return redirect(url_for('core.login', next=request.url))
        else:
            super_admin_permission.require(http_exception=403)

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        response = render_miror(self, template, **kwargs)
        return response

""" extra things not used !!!!!
class MethodArgAjaxModelLoader(sqla.ajax.QueryAjaxModelLoader):
    def get_list(self, term):
        print("hi")
        query = self.session.query(self.model).filter_by(mid=term)
        return StreetsMetadata.query.all()

class CKTextAreaWidget(TextArea):
    def __call__(self, field, **kwargs):
        if kwargs.get('class'):
            kwargs['class'] += ' ckeditor'
        else:
            kwargs.setdefault('class', 'ckeditor')
        return super(CKTextAreaWidget, self).__call__(field, **kwargs)

class CKTextAreaField(TextAreaField):
    widget = CKTextAreaWidget()
extra things not used end !!!!! """

# Admin Users View (Control Users AdminView)
class EstateAdminView(AdminEstateModelView):
    # update main view to render js file for any js tasks like toggle password

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        #using extra js in render method allow use url_for that itself requires an app context
        # update the kwargs.data which is the data arugment sent to the list.html

        #cond = or_(*[self.model.query.user_role == person for person in people])
        # one_to_many filter by role (forgien key)
        if 'form' in kwargs and 'streetname' in kwargs['form'] and 'choices' in vars(kwargs['form'].streetname):
            kwargs['form'].streetname.choices = [street.streetname for street in StreetsMetadata.query.filter_by(estate_id=current_user.user_estate.id).all()]
        kwargs['data'] = self.model.query.filter_by(estate=current_user.estate).filter(not_(self.model.role.in_([1,2]))).all()
        self.extra_js = [url_for("static", filename="admin/js/users.js"), url_for("static", filename="admin/js/phonenumbers.js"), "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/js/intlTelInput.min.js"]
        self.extra_css = ['https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/css/intlTelInput.css']
        kwargs.update(self._template_args)
        response = render_miror(self, template,**kwargs)
        return response
        # return super(EstateAdminView, self).render(template, **kwargs)

    # form = TestForm
    # form_base_class = MyBaseForm
    column_hide_backrefs = False


    # this override user role to prevent estate admin from create superadmin user
    # I think that by use same name it override the orginal maybe
    # StreetsMetadata.query.with_entities(StreetsMetadata.streetname).all()
    # one way to return the options you need but will exclude the main field and by name this extra same name flask-admin will regonize it

    #x = lambda:giveMeAllHousesList(street.excluded, street.min, street.max)
    # Add Custom Functions To the model aprove or anything
    @action('approve', 'Approve', 'Are you sure you want to approve selected users?')
    def action_approve(self, ids):
        count = 0
        try:
            query = User.query.filter(User.id.in_(ids))
            for user in query.all():
                print(user)
                count += 1
            flash('User was successfully approved {} users were successfully approved'.format(count))

        except Exception as ex:
            if not self.handle_view_exception(ex):
                raise
            flash('Failed to approve users. {}'.format(error))


    # edit types format like date
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True

    """ Custom validation code that checks if estate admin try create super admin or edit it"""
    def validate_form(self, form):
        # Note This excuted twice when render or when submit so I check if password_hash
        # note empty also I depend on the password_hash is required so only when render it will empty
        if "user_role" in form and form.user_role.data is not None and current_user.user_role.name != 'superadmin' and form.user_role.data.name == 'superadmin':
            flash("Sorry, you cannot create a super admin user because you are not a super admin!")
        return super(EstateAdminView, self).validate_form(form)

    def on_model_change(self, form, User, is_created):
        allowed_rules = ['guard', 'occupant', 'guest', 'temp']

        if "password_hash" in form and form.password_hash.data is not None:
            # so the User is the new recored created we can override Submitted value for ex hash pass or may prevent superadmin role but need current_user.role
            User.password_hash = generate_password_hash(form.password_hash.data)

        if 'username' in form and form.username.data is not None:
            if form.username.data[0].isdigit():  # Check whether the first digit is a number
                raise ValidationError('Username Cannot start with a number: ({})'.format(form.username.data))

        if is_created and "user_role" in form and form.user_role.data is not None and current_user.user_role.name != 'superadmin' and form.user_role.data.name not in allowed_rules:
            raise ValidationError('Sorry, you cannot create a {} user because you are not a super admin!'.format(form.user_role.data.name))

        if is_created == False and "user_role" in form and form.user_role.data is not None and current_user.user_role.name != 'superadmin' and form.user_role.data.name not in allowed_rules:
            raise ValidationError('Sorry, you cannot create a {} user because you are not a super admin!'.format(form.user_role.data.name))
        if "telephone" in form and form.telephone.data is not None:
            try:
                submitted_number = str(form.telephone.data)
                valdaite_num = phonenumbers.parse(submitted_number)
                if not phonenumbers.is_valid_number(valdaite_num):
                    raise ValidationError("invalid number")
            except:
                raise ValidationError("invalid number")

        # last part on my custom code to valdaite the inputed value incase html inspect change while submit form
    # Form will now use all the other fields in the model

    # Add our own password form field - call it password2

    # inline editable fildes
    column_editable_list = ['firstname','lastname','gender','streetname', 'flatnumber']

    # over ride inputs types
    form_overrides = {
        'dateofbirth': DateField,
        'telephone': StringField,

    }

    # selectbox from strings good for role
    form_choices = {
    'gender': [
        ('male', 'Male'),
        ('female', 'Female'),
    ],
    }
    # wtf forms
    form_args = {
            'id': {
            'label': 'Id',
            'validators': []
            },
            'profile_image': {
            'label': 'Profile Image',
            'validators': [required()]
            },
            'firstname': {
            'label': 'First Name',
            'validators': [required()]
            },
            'lastname': {
            'label': 'Last Name',
            'validators': [required()]
            },
            'dateofbirth': {
            'label': 'Date of Birth',
            'validators': [required(message="You need to enter your date of birth")]
            },
            'streetname': {
            'label': 'Streetname',
            'validators': [required()],
            },
            # id used in user.js to add custom toggle
            'password_hash': {
            'label': 'Password',
            'id': 'user_password',
            'validators': [required()]
            },
            'username': {
            'label': 'Username',
            'description': 'Username Cannot start with a number',
            'validators': [required()]
            },
            'flatnumber': {
            'label': 'Flat number',
            'validators': []
            },
            'gender': {
            'label': 'Gender',
            'validators': [required(), AnyOf(['male', 'female'])]
            },
            'telephone': {
            'label': 'Telephone',
            'validators': [required()]
            },
    }
    # style and control
    form_widget_args = {
    'streetname': {
        'rows': 1,
        'style': 'color: black'
    }
    }

    form_extra_fields = {
        'user_role': sqla.fields.QuerySelectField(
            label='User role',
            query_factory= lambda:Role.query.filter(Role.name != 'superadmin').filter(Role.name != 'estateadmin').all(),
            widget=Select2Widget()
        ),
        'user_estate': sqla.fields.QuerySelectField(
            label='The Estate',
            query_factory= lambda:Estate.query.filter(Estate.id == current_user.user_estate.id).all(),
            widget=Select2Widget()
        ),
        'streetname': SelectField(
            'streetname',
            coerce=str,
            choices=([street.streetname for street in StreetsMetadata.query.all()]),
            render_kw={'onchange': "myFunction()"},
            validate_choice=False
            ),
    }
    # remove these fileds from edit and create
    form_excluded_columns = ['user_role','estate','guests', 'staffs', 'services', 'enquiries', 'news', 'subscriptions']
    # open bootstrap modal for create and edit
    column_default_sort = [('registration_date', True)]
    column_sortable_list = ('firstname','streetname', 'lastname','registration_date','user_estate','flatnumber','housenumber','user_role','gender','username', 'dateofbirth')

    create_modal = False
    edit_modal = False
    # which columns has filter for example contains gaurd
    column_filters = [User.estate, User.gender]
    # which columns can used for search
    column_searchable_list = [User.id, User.firstname, User.username, User.telephone, User.streetname]
    #column_formatters = dict(User.housenumber=macro('render_price'))
    #column_formatters = dict(User.password_hash=lambda v, c, m, p: generate_password_hash(m.password_hash))
    # which columns can be added in create list
    # form_create_rules more powerfull from column create in can remove fields
    form_create_rules = (rules.HTML('<h5 class="text-center p-2 mb-3 mt-2 bg-primary text-white">Personal information</h5>'), 'firstname', 'lastname','dateofbirth','gender', 'streetname', 'housenumber', 'flatnumber', 'user_estate','telephone', rules.HTML('<h5 class="text-center p-2 mb-3 mt-2 bg-secondary text-white">App information</h5>'),'username', 'password_hash', 'user_role', 'registration_date', 'profile_image')
    column_create_list = (User.firstname, User.lastname,User.user_estate,User.dateofbirth, User.username, User.password_hash,User.flatnumber, User.gender, User.telephone, User.housenumber)

# services

class EstateAdminServiceView(AdminEstateModelView):
    # return super(EstateAdminServiceView, self).render(template, **kwargs)
    #IntegerField
    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        # estate admin has right to view any service in his estate he responsble for that even created by superadmin
        # this query mean return all services that created by users whoes there estate-id equal to current estate-admin id
        kwargs['data'] = self.model.query.filter(self.model.user_id.in_([x.id  for x in User.query.filter_by(estate=current_user.estate).all()])).all()
        response = render_miror(self, template, **kwargs)
        return response


    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    create_modal = True
    edit_modal = True
    form_extra_fields = {
        'requester': sqla.fields.QuerySelectField(
            label='Requester',
            query_factory= lambda:User.query.filter_by(estate = current_user.estate).all(),
            widget=Select2Widget()
        ),
    }
    column_filters = ['request_date', 'user_id', 'service_requested']
    column_searchable_list = ['id', 'user_id', 'request_date', 'service_requested']
    column_editable_list = ['service_requested', 'user_id', 'request_date']

    column_default_sort = [('request_date', True)]
    column_sortable_list = ('service_requested','user_id', 'request_date', 'request_date', 'id')
    column_create_list = ('service_requested', 'request_date')
    column_list = ('id','requester', 'service_requested', 'request_date')
    form_args = {
            'service_requested': {
            'label': 'Service Requested',
            'validators': [required()]
            },
            'request_date': {
            'label': 'Request Date',
            'id': 'req_date',
            'validators': [required()]
            }
    }


class EstateAdminCodeGen(AdminEstateModelView):

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        #using extra js in render method allow use url_for that itself requires an app context
        # update the kwargs.data which is the data arugment sent to the list.html
        # user_role
        # query the codes that only related to estate-admin current logged estate and the roles not superadmin or estateadmin users
        kwargs['data'] = self.model.query.filter_by(user_estate=current_user.estate).filter(not_(self.model.user_role.in_([1,2]))).all()
        # kwargs['data'] = self.model.query.filter(self.model.user_estate == current_user.user_estate, not_(self.model.user_role.in_([1,2]))).all()
        self.extra_js = [url_for("static", filename="admin/js/users.js")]
        response = render_miror(self, template,**kwargs)
        return response

    # take care is_created true if it create form so we need to check it to add valdation to create not edit
    def on_model_change(self, form, model, is_created):
        if current_user and not current_user.is_anonymous and is_created:
            model.user_id = current_user.id
        else:
            pass

        if is_created and current_user and 'code_estate' in form and form.code_estate.data != current_user.user_estate:
            raise(ValidationError("! You are only allowed to create users on your properties that you manage (invalid estate id)"))
    # sort by two columns first user_id then gendate
    # column_sortable_list = ('user_id','gen_date', ('user_id', 'gen_date'))
    # return the create form and control it before return using super(class, self).create_form
    def create_form(self):
        # (!VIP!) what happend here is intersting, this function called twice when render data
        # and when submit the form and we can add custom valdation if we need by check the gen data if None
        # so it create if not None and has value so it submit
        form = super(EstateAdminCodeGen, self).create_form()
        banned_list = [co.gen_code for co in Code.query.all()]
        gencode = unique_code_generator(strpool, banned_list)
        if 'gen_code' in form and form.gen_code.data is None:
            form.gen_code.data = gencode
        return form


    # return super(AdminCodeGen, self).render(template, **kwargs)
    # callback
    # control options in form first step then valdaite
    # selectbox from strings good for role

    # view Customiztion
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    edit_modal = True
    column_filters = ['gen_date', 'user_id', 'gen_code', 'user_estate']
    column_sortable_list = ('id', 'requested_for', 'gen_code', 'gen_date', 'code_estate.id', 'user_id', 'unused')
    column_searchable_list = ['gen_code', 'requested_for', 'user_id', 'gen_date']
    column_editable_list = ['requested_for', 'gen_code', 'user_estate', 'user_role']
    column_create_list = ('requested_for', 'gen_code', 'gen_date', 'user_id', 'user_role')
    form_excluded_columns = ['id', 'unused', 'user']
    column_list = ('id', 'requested_for', 'gen_code', 'gen_date', 'code_role', 'code_estate', 'user_id', 'unused')

    # column_create_list = ('service_requested', 'request_date')

    form_extra_fields = {
        'code_estate': sqla.fields.QuerySelectField(
            label='Code Estate',
            query_factory= lambda:Estate.query.filter_by(id = current_user.user_estate.id).all(),
            widget=Select2Widget()
        ),
        'code_role': sqla.fields.QuerySelectField(
            label='User Role',
            query_factory= lambda:Role.query.filter(not_(Role.id.in_([1,2]))).all(),
            widget=Select2Widget()
        )
    }
    form_overrides = {
      'gen_code': StringField,
    }



class EstateAdminPublication(AdminEstateModelView):

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        # new ways for query now at least 4 ways to joining two or three tables and more at comments and other things not only join
        # print(db.session.query(Publication).all()[0].users.estate)select_from()
        # this will return all publications inside the current logged estate admin estate
        kwargs['data'] = db.session.query(self.model.id,self.model.id, self.model.user_id, self.model.publication, self.model.news_date, self.model.users, User.estate).join(User, self.model.user_id == User.id).filter(User.estate==current_user.estate).all()
        # un related comment to current class kwargs['data'] = self.model.query.filter(self.model.user_estate == current_user.user_estate, not_(self.model.user_role.in_([1,2]))).all()
        response = render_miror(self, template,**kwargs)
        return response
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    edit_modal = True
    column_filters = ['id', 'user_id', 'publication', 'news_date']
    column_searchable_list = ['id', 'user_id']
    column_editable_list = ['publication']
    column_sortable_list = ['id', 'user_id', 'publication', 'news_date']
    column_list = ('id', 'user_id', 'publication', 'news_date')
    # form_excluded_columns = ['code_role', 'id','estate','role', 'code_estate', 'unused', 'user', 'user_role']


class EstateAdminStaff(AdminEstateModelView):

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        """ !! this query was reusable as it work with all estate also for views not required protect admin data tables without change any line and will return the correct result we need"""
        kwargs['data'] = db.session.query(self.model.id,self.model.user_id, self.model.firstname, self.model.lastname, self.model.dateofbirth, self.model.gender, self.model.telephone, self.model.jobdescription, User.estate).join(User, self.model.user_id == User.id).filter(User.estate==current_user.estate).all()
        self.extra_js = [url_for("static", filename="admin/js/phonenumbers.js"), "https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/js/intlTelInput.min.js"]
        self.extra_css = ['https://cdnjs.cloudflare.com/ajax/libs/intl-tel-input/16.0.4/css/intlTelInput.css']
        response = render_miror(self, template,**kwargs)
        return response

    def on_model_change(self, form, model, is_created):
        if "telephone" in form and form.telephone.data is not None:
            try:
                submitted_number = str(form.telephone.data)
                valdaite_num = phonenumbers.parse(submitted_number)
                if not phonenumbers.is_valid_number(valdaite_num):
                    raise ValidationError("invalid number")
            except:
                raise ValidationError("invalid number")

    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    column_filters = ['id', 'user_id', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription']
    column_searchable_list = ['firstname', 'lastname', 'telephone', 'id']
    column_editable_list = ['firstname', 'lastname']
    column_sortable_list = ('id', 'user_id', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription')
    column_list = ('id', 'user_id', 'firstname', 'lastname', 'dateofbirth', 'gender', 'telephone', 'jobdescription')
    form_choices = {
    'gender': [
        ('male', 'Male'),
        ('female', 'Female'),
    ]
    }
admin.add_view(EstateAdminView(User, db.session, endpoint='/estate-admin/users', category='estate-admin'))
admin.add_view(EstateAdminServiceView(Service, db.session, endpoint='/estate-admin/services', category='estate-admin'))
admin.add_view(EstateAdminCodeGen(Code, db.session, endpoint='/estate-admin/codegen', category='estate-admin'))
admin.add_view(EstateAdminPublication(Publication, db.session, endpoint='/estate-admin/publications', category='estate-admin'))
admin.add_view(EstateAdminStaff(Staff, db.session, endpoint='/estate-admin/staff', category='estate-admin'))








"""
GUARD Admin Users
"""

class Roled(object):

    def is_accessible(self):
        roles_accepted = getattr(self, 'roles_accepted', None)
        return is_accessible(roles_accepted=roles_accepted, user=current_user)

    def _handle_view(self, name, *args, **kwargs):
        if current_user.is_anonymous:
            return redirect(url_for_security('login', next="/admin"))
        if not self.is_accessible():
            # return self.render("admin/denied.html")
            return "<p>Access denied</p>"


class GuardMainView(Roled, ModelView):
    can_create = False
    can_edit = False
    can_delete = False

    @guard_permission.require(http_exception=403)
    def is_accessible(self):
        if current_user and current_user.is_anonymous:
            return False
        else:
            allowed_rules = ['superadmin', 'estateadmin', 'guard']
            return current_user.user_role.name in allowed_rules

    def __init__(self, *args, **kwargs):
        self.roles_accepted = kwargs.pop('roles_accepted', list())
        super(GuardMainView, self).__init__(*args, **kwargs)

# Note Inhiret the class from the right view not modal view
class GuardAdminGuestsView(GuardMainView):
    @guard_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        # kwargs['data'] =
        # other query query.join(Customer.invoices) specify relationship from left to right
        # join query 1 with for loop 2 arugments (Complex query to get the guard guests in his estate)
        myGuests = []
        for u, g in db.session.query(User, self.model).filter(User.id == self.model.user_id).filter(User.user_estate == current_user.user_estate).all():
            myGuests.append(g)
            # print("You As Guard Can mange Guest {} Hosted By User {} in The estate {}".format(g.lastname, u.username, u.user_estate.id))

        # neededguests = db.session.query(User.guests, Guest.users, Guest.id, Guest.user_id, Guest.visit_date, Guest.firstname, Guest.lastname, Guest.gender, Guest.telephone).filter(User.user_estate==current_user.user_estate).all()
        # print(db.session.query(User.guests).filter(User.user_estate==current_user.user_estate).all())
        # print(myGuests)
        # print(db.session.query(Guest.id, Guest.user_id, Guest.visit_date, Guest.firstname, Guest.lastname, Guest.gender, Guest.telephone).join(User.guests).filter(User.user_estate == current_user.user_estate))
        # x = db.session.query(self.model , User).filter(self.model.user_id == User.id).filter(current_user.user_estate == User.user_estate).all()
        # print(x[0])
        kwargs['data'] = myGuests

        # print(self.model.query.filter(user_id=User.query().with_entities(id).filter(User.id==self.model.user_id).filter(User.user_estate==current_user.user_estate) ).all())
        # print(User.query.filter_by(user_estate = current_user.user_estate).all().guests.all())
        # User.query.filter(User.) guest.user_id
        response = render_miror(self, template, **kwargs)
        return response
        # return super(GuardAdminGuestsView, self).render(template, **kwargs)
    """
    form_extra_fields = {
        'host': sqla.fields.QuerySelectField(
            label='The Host',
            query_factory= lambda:User.query.filter_by(estate = current_user.estate).all(),
            widget=Select2Widget()
        ),
    }
    """
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    column_filters = ['gender', 'visit_date']
    column_searchable_list = ['firstname', 'lastname', 'telephone']
    column_default_sort = [('visit_date', True)]
    column_sortable_list = ('firstname','lastname', 'visit_date', 'gender', 'telephone')
    column_list = ('host', 'visit_date', 'firstname', 'lastname', 'gender', 'telephone')


class GuardPublicationView(GuardMainView):

    @estate_admin_permission.require(http_exception=403)
    def render(self, template, **kwargs):
        # new ways for query now at least 4 ways to joining two or three tables and more at comments and other things not only join
        # print(db.session.query(Publication).all()[0].users.estate)still super reusable
        # this will return all publications inside the current logged estate admin estate
        kwargs['data'] = db.session.query(self.model.id,self.model.id, self.model.user_id, self.model.publication, self.model.news_date, self.model.users, User.estate).join(User, self.model.user_id == User.id).filter(User.estate==current_user.estate).all()
        # un related comment to current class kwargs['data'] = self.model.query.filter(self.model.user_estate == current_user.user_estate, not_(self.model.user_role.in_([1,2]))).all()
        response = render_miror(self, template,**kwargs)
        return response

    # sort by two columns first id then news_date
    form_base_class = SecureForm
    column_type_formatters = MY_DEFAULT_FORMATTERS
    can_view_details = True
    edit_modal = True
    column_filters = ['id', 'user_id', 'publication', 'news_date']
    column_searchable_list = ['id', 'user_id']
    column_editable_list = ['publication']
    column_sortable_list = ['id', 'user_id', 'publication', 'news_date']
    column_list = ('id', 'user_id', 'publication', 'news_date')
    # form_excluded_columns = ['code_role', 'id','estate','role', 'code_estate', 'unused', 'user', 'user_role']

admin.add_view(GuardAdminGuestsView(Guest, db.session, endpoint='/guard/guests', roles_accepted=['superadmin','estateadmin','guard'], category='Guard'))
admin.add_view(GuardPublicationView(Publication, db.session, endpoint='/guard/news', roles_accepted=['superadmin','estateadmin','guard'], category='Guard'))


class LogoutLink(MenuLink):

    def is_accessible(self):
        return current_user.is_authenticated

admin.add_link(LogoutLink(name='Logout', url='/logout'))










import datetime

@admin_permission.require(http_exception=403)
@adminapp.route('/get_houses_numbers')
def gethouses():
    request_data = request.args
    if request_data and 'street' in request_data:
        street = StreetsMetadata.query.filter(StreetsMetadata.streetname == request_data['street']).one_or_none()
        if street:
            street_houses = lambda:giveMeAllHousesList(street.excluded, street.min, street.max)
            response = {'code': 200, 'houses': street_houses(), 'selected': 0}
            # this part for edit model will load the right housenumber
            if 'username' in request_data:
                getUserHouseNum = User.query.filter_by(username=request_data['username']).first()
                if getUserHouseNum:
                    response['selected'] = getUserHouseNum.housenumber
            return jsonify(response)
        else:
            return jsonify({'code': 404, 'houses': [], 'selected': 0})
    else:
        return jsonify({'code': 400, 'street': [], 'selected': 0})

"""
@super_admin_permission.require(http_exception=403)
@adminapp.route('/add')
def adduser():
    #newCode = Code(requested_for="me", user_role=1, user_estate=1, gen_date=datetime.datetime.utcnow(), gen_code='hinoob')
    #newCode.insert()
    # user = User(firstname="hi", lastname="bye", dateofbirth=datetime.datetime.now(), username='teadmin',
    #             password_hash='tpass', streetname=1, housenumber='1', flatnumber='2',
    #             gender='male',estate=1, telephone=24546642, role=2)
    # user.insert()
    #fullName = Code.query.first()

    # return query that not in the provided list
    # query = db.session.query(Estate).filter(Estate.id.notin_([1])).first()
    return jsonify({'data': request.args['street']})
    street = StreetsMetadata.query.first()
    x = lambda:giveMeAllHousesList(street.excluded, street.min, street.max)
    test = lambda:[str(street.streetname) for street in StreetsMetadata.query.all()]
    return str(test())


  {% macro render_price(model, column) %}
    {{ model.price * 2 }}
  {% endmacro %}
class UserView(ModelView):
        can_delete = False  # disable model deletion
        can_create = False
        can_edit = False
        can_delete = False

class PostView(ModelView):
        page_size = 50  # the number of entries to display on the list view
"""

"""
custom views
class Users(BaseView):
    #def is_accessible(self):
    #    return current_user.is_authenticated
    @expose('/')
    def index(self):
        return self.render('adminusers.html')

#admin.add_view(Users(name='Mange Users', endpoint='', category='Users'))
class Guests(BaseView):
    #def is_accessible(self):
    #    return current_user.is_authenticated
    @expose('/')
    def index(self):
        return self.render('adminguests.html')

#admin.add_view(Users(name='Mange Users', endpoint='', category='Users'))

class Codes(BaseView):
    #def is_accessible(self):
    #    return current_user.is_authenticated
    @expose('/')
    def index(self):
        return self.render('admincodes.html')
#admin.add_view(Users(name='Mange Users', endpoint='', category='Users'))
#admin.add_view(ModelView(Code, db.session, name='Code Generator'))

"""
