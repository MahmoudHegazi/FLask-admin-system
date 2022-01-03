from flask_wtf import FlaskForm
from flask_wtf import Form
from wtforms import TextField, BooleanField, TextAreaField
from wtforms.validators import Required, Length
from wtforms import SubmitField, HiddenField,StringField, TextField, IntegerField, DateTimeField, PasswordField, RadioField, SelectMultipleField, ValidationError,SelectField, widgets, FileField
from wtforms.validators import DataRequired, EqualTo, Regexp
from flask_wtf.file import FileField, FileAllowed
from estate_management.usermodels import User, Staff, Guest, Service, Enquiry, Publication, Subscription
from flask_login import current_user
from estate_management.core.guardCodeGenerator import code_generator
from datetime import datetime
import phonenumbers

class MultiCheckboxField(SelectMultipleField):
    widget = widgets.ListWidget(prefix_label=False)
    option_widget = widgets.CheckboxInput()


class GeneratorForm(FlaskForm):
    requested_for = StringField('Occupant name')
    user_id = IntegerField('Generating Guard')
    gen_date = DateTimeField('Generation Date', default=datetime.today, validators=[DataRequired()])
    submit = SubmitField('Generate code')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class CodeForm(FlaskForm):
    registrationCode = StringField('Registration code', validators=[DataRequired()])
    fullName = StringField('full name', validators=[DataRequired()])
    submit = SubmitField('Submit')

class UserForm(FlaskForm):
    #id = IntegerField()
    firstname = StringField('Firstname', validators=[DataRequired()])
    lastname = StringField('Lastname', validators=[DataRequired()])
    dateofbirth = DateTimeField('Date of Birth', format='%d/%m/%Y', validators=[DataRequired(message="Valid date of birth is required ex 01/01/1970")])
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    pass_confirm = PasswordField('Confirm Password', validators=[DataRequired(),EqualTo('password', message='Passwords must match')])
    streetname = SelectField('Street Name', validate_choice=False, validators=[DataRequired()])
    housenumber = SelectField('House Number', validate_choice=False, validators=[DataRequired(), Regexp(regex='^\d+$')])
    flatnumber = StringField('Flat Number', render_kw={'required': False}, validators=[Regexp(regex='^\d*$')])
    gender = SelectField('Gender', validators=[DataRequired()], choices = [('male','Male'),('female','Female')])
    # validators for phone number in nigira
    telephone = StringField('Telephone', validators=[DataRequired()])
    code = StringField('Code')
    code_fullname = StringField('CodeName')
    # role = SelectField('Role', validators=[DataRequired()], choices=[('occupant','occupant'),('guard','guard')])
    submit = SubmitField("Register")

    def validate_username(self, field):
        # Check if not None for that username!
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Sorry, that username is taken!')

    def validate_telephone(self, field):
        try:
            submitted_number = str(field.data)
            valdaite_num = phonenumbers.parse(submitted_number)
            if not phonenumbers.is_valid_number(valdaite_num):
                raise ValidationError("invalid phone number")
        except:
            raise ValidationError("invalid phone number")



class UpdateUserForm(FlaskForm):
    telephone = IntegerField('Telephone')
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg','png','jpeg'])])
    submit = SubmitField('Update')

    def validate_telephone(self, field):
        # Check if not None for that user telephone!
        if User.query.filter_by(telephone=field.data).first():
            raise ValidationError('Your telephone number has been registered already!')


'''
class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Old password', validators=[DataRequired()])
    password = PasswordField('New password', validators=[DataRequired(), EqualTo('password2', message='Passwords must match.')])
    password2 = PasswordField('Confirm new password', validators=[DataRequired()])
    submit = SubmitField('Update Password')
'''


class GuestForm(FlaskForm):
    #id = HiddenField()
    user_id = IntegerField('Host id')
    visit_date = DateTimeField('Visit Date', default=datetime.today, validators=[DataRequired()])
    firstname = StringField('Firstname', validators=[DataRequired()])
    lastname = StringField('Lastname', validators=[DataRequired()])
    gender = SelectField('Gender', validators=[DataRequired()], choices = [('male','Male'),('female','Female')])
    telephone = StringField('Telephone', validators=[DataRequired()])
    submit = SubmitField("Book Guest")


class StaffForm(FlaskForm):
    #id = HiddenField()
    user_id = IntegerField('Boss id')
    firstname = StringField('First Name',validators=[DataRequired()])
    lastname = StringField('Last Name',validators=[DataRequired()])
    dateofbirth = DateTimeField('Date of Birth', format='%d/%m/%Y', validators=[DataRequired(message="Please enter date of birth")])
    gender = SelectField('Gender',choices = [('male','Male'),('female','Female')],validators=[DataRequired()])
    telephone = IntegerField('Telephone', validators=[DataRequired()])
    jobdescription = StringField('Job Description', validators=[DataRequired()])
    submit = SubmitField('Register Worker!')

    def validate_worker(self, field):
        if Staff.query.filter_by(lastname=field.data).first():
            raise ValidationError('Sorry, this worker has already been registered!')


class ServiceForm(FlaskForm):
    #id = HiddenField()
    user_id = IntegerField('Requester id')
    service_requested = SelectField('Service Requested', validators=[DataRequired()], choices=[('carpentry','Carpentry'),('electrical','Electrical'),('fumigation','Fumigation'),('generator repair','Generator Repair'),('car wash','Mobile Car Wash'),('plumber','Plumber'),('welder','Welder')])
    request_date = DateTimeField('Request Date', default=datetime.today, validators=[DataRequired()])
    submit = SubmitField('Request Service')


class EnquiryForm(FlaskForm):
    #id = HiddenField()
    user_id = IntegerField('Asker id')
    enquiry = TextAreaField('Enquiry/Complaint', validators=[DataRequired()])
    enquiry_date = DateTimeField('Enquiry/Complaint Date', default=datetime.today, validators=[DataRequired()])
    submit = SubmitField('Submit')


class NewsForm(FlaskForm):
    id = HiddenField()
    user_id = IntegerField('Reporter id')
    publication = TextAreaField('News', validators=[DataRequired()])
    news_date = DateTimeField('News Date', default=datetime.today, validators=[DataRequired()])
    submit = SubmitField('Submit')


class SubscriptionForm(FlaskForm):
    #id = HiddenField()
    user_id = IntegerField('Subscriber id')
    subscription = SelectField("Subscription", validators=[DataRequired()], choices=[('energy','energy'),('water','water'),('security levy','security levy')])
    amount = IntegerField('Amount', validators=[DataRequired()])
    subscription_date = DateTimeField('Subscription Date', default=datetime.today, validators=[DataRequired()])
    submit = SubmitField('Submit')
