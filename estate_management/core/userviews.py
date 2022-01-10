from flask import render_template,json, request, flash, redirect, url_for, Blueprint, session, current_app, jsonify
from flask_login import login_user, current_user, logout_user, login_required
from estate_management.core.userforms import UserForm, GuestForm, StaffForm, ServiceForm, LoginForm, EnquiryForm, NewsForm, SubscriptionForm, UpdateUserForm, CodeForm, GeneratorForm, ResetPassword, UpdatePassword
from estate_management.usermodels import User, Guest, Staff, Service, Enquiry, Publication, Subscription, Code, StreetsMetadata, Handymen, HandyMenNotfications, ServiceMetaData, ServiceType, ResetPasswordTokens
from estate_management.core.picture_handler import add_profile_pic
from estate_management.core.guardCodeGenerator import code_generator, strpool, unique_code_generator1, strpool
from estate_management import giveMeAllHousesList, getValidExclude, app
from estate_management.core.twilio_sms import valdiate_phone, did_you_send_notification
from estate_management.core.easy_encrypt import encrypt, decrypt, give_me_valid_object
from wtforms.validators import AnyOf, ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from estate_management import db, stripe_key, super_admin_permission, super_admin_permission, estate_admin_permission, guard_permission, create_dynamic_url, mail, Message, Mail
from flask_principal import Principal, Identity, AnonymousIdentity, \
     identity_changed
import sys
import datetime
import time
import random


core = Blueprint('core',__name__, template_folder='templates')


# create url with query paremeters or without
def dynamic_endpointurl(path, url_data):
    the_base_url = str(request.base_url.split("/")[0] + "//" + request.host + "/" + path + "" +  "")
    return the_base_url + str(url_data)

# function to display all possible unique error wtf forms to flash after redirect

def getErrorMessages(errors):
    error_messages = []
    for key in errors:
        if len(errors[key]) > 0:
            current_errors = errors[key]
            for message in current_errors:
                error_message = "!Error In {} field: {}".format(key, message)
                if error_message not in error_messages and errors[key] != '':
                    error_messages.append(error_message)
    return error_messages
################################################################################

#OCCUPANTS HOME PAGE
@core.route('/')
def index():
    return render_template('index.html')

################################################################################

#GUARDS HOME PAGE
@core.route('/guardindex')
def guardindex():
    return render_template('guardindex.html')

#CODE GENERATOR TO BE USED BY ADMIN TO GENERATE REGISTRATION CODES FOR NEW OCCUPANTS
@core.route('/gencode', methods=['GET','POST'])
def gencode():

    form = GeneratorForm()

    if form.validate_on_submit():

        code = Code(user_id=current_user.id, requested_for=form.requested_for.data, gen_date=form.gen_date.data, gen_code=code_generator(strpool))
        db.session.add(code)
        db.session.commit()
        return redirect(url_for("core.codelist"))
    return render_template("gencode.html", form=form)

#LIST OF GENERATED CODES AND CORESPONDING OCCUPANTS
@core.route('/codelist')
def codelist():
    codes = Code.query.all()
    return render_template('codelist.html', codes=codes)

################################################################################

#ESTATE INFORMATION PAGE
@core.route('/info')
def info():
    return render_template('info.html')

#
@core.route('/allinfo')
def allinfo():
    return render_template('allinfo.html')

################################################################################

#USER LOGIN PAGE
@core.route('/login', methods=['GET', 'POST'])
def login():

    form = LoginForm()

    if form.validate_on_submit():
        submited_username = "%s" %str(request.form['username']).strip().lower()
        session['username'] = submited_username
        user = User.query.filter_by(username=submited_username).first()

        if user == None:
            flash("User is not registered! Please register!")
            return redirect(url_for('core.createUser'))

        # enable remeber me part
        is_remeberme_checked = form.remeber_me.data == True
        if user.check_password(form.password.data) and user is not None:
            remeber_user = is_remeberme_checked
            # set the remeber to the value of check box input form.remeber_me.data default by user now
            login_user(user, remember=is_remeberme_checked, duration=datetime.timedelta(days=5))
            flash('Logged in successfully.')

            # Tell Flask-Principal the identity changed
            identity_changed.send(current_app._get_current_object(),
                                  identity=Identity(user.id))

            admin_roles = ['superadmin', 'estateadmin']
            next = request.args.get('next')
            if next == None or not next[0]=='/':
                if user.user_role.name == 'guard':
                    next = url_for('admin.index')
                elif user.user_role.name == "superadmin":
                    next = url_for('user.index_view')
                elif user.user_role.name == 'estateadmin':
                    #next = url_for('admin.index')
                    next = url_for('/estate-admin/users.index_view')
                else:
                    next = url_for('core.index')

                return redirect(next)

        else:
            flash('Invalid credentials')

    return render_template('login.html', form=form)


################################################################################

@core.route("/logout")
def logout():
    session.pop('username', current_user)
    logout_user()

    # Remove session keys set by Flask-Principal
    for key in ('identity.name', 'identity.auth_type'):
        session.pop(key, None)

    # Tell Flask-Principal the user is anonymous
    identity_changed.send(current_app._get_current_object(),
                          identity=AnonymousIdentity())
    return redirect(url_for('core.index'))

################################################################################

# REGISTRATION PAGE FOR BOTH OCCUPANTS AND GUARDS
@core.route("/createUser", methods=["GET", "POST"])
def createUser():
    form = CodeForm()
    user_form = UserForm()
    # first Form
    if form.validate_on_submit() and user_form.validate_on_submit() != True:
        valid_form = True
        # import inspect print(inspect.getmembers(form, lambda a:not(inspect.isroutine(a))))
        # SEARCH FOR REGISTRATION CODE GIVEN BY THE ADMIN
        form_gen_code = str(form.registrationCode.data).upper()

        registrationCode = Code.query.filter_by(gen_code=form_gen_code).first()

        # CHECK IF REGISTRATION CODE MATCHES THE GIVEN NAME ON THE DATABASE
        if not registrationCode:
            flash("INVALID REGISTRATION CODE!!!")
            valid_form = False
            return render_template('codeconfirmation.html', form=form)

        if registrationCode and registrationCode.requested_for != form.fullName.data:
            flash("INVALID NAME!!!")
            valid_form = False

        if registrationCode and registrationCode.unused == False:
            flash("Expired REGISTRATION CODE!!!")
            valid_form = False


        if valid_form == False:
            return render_template('codeconfirmation.html', form=form)
        else:
            # here the code is valid and passed checks
            # OPEN REGISTRATION FORM IF REGISTRATION CODE AND NAMES ARE VALID
            # user_form.streetname.choices =

            if 'streetname' in user_form and 'choices' in vars(user_form.streetname) and 'housenumber' in user_form and 'choices' in vars(user_form.housenumber):

                current_streets = StreetsMetadata.query.filter_by(estate_id=registrationCode.user_estate).all()
                if len(current_streets) > 0:
                    street_houses = giveMeAllHousesList(current_streets[0].excluded, current_streets[0].min, current_streets[0].max)
                    user_form.streetname.choices = [street.streetname for street in current_streets]
                    user_form.housenumber.choices = street_houses
                    # I closed valdaiton until add my choices and turn on again to reduce any chance for errors
                    user_form.streetname.validate_choice = True
                else:
                    flash("There are no street and house names in the app, and you won't be able to create a user. Please contact the administrator to add streets")
                    if "streetname" in user_form and user_form.streetname.validate_choice is not None:
                        # in case no strrets and housenumber inform the user and return the valdation on to not let him pass
                        user_form.streetname.validate_choice = True
                    if "housenumber" in user_form and user_form.housenumber.validate_choice is not None:
                        user_form.housenumber.validate_choice = True

                    user_form.streetname.validate_choice = True
            code_submit = {'code': form_gen_code, 'name': form.fullName.data}

            return render_template('user.html', form=user_form, code_submit=code_submit)
    # Second Form
    elif user_form.validate_on_submit():
        registrationCode = Code.query.filter_by(gen_code=user_form.code.data).first()
        if not registrationCode:
            flash("Your request cannot be processed. invalid registration Code Make sure not to edit form hidden data")
            return render_template('codeconfirmation.html', form=form)
        elif registrationCode.requested_for != user_form.code_fullname.data:
            flash("Your request cannot be processed. invalid request fullname Make sure not to edit form hidden data")
            return render_template('codeconfirmation.html', form=form)
        else:
            # here we have valid code and valid user in same route with 1 time form for each request
            user = User(firstname=user_form.firstname.data, lastname=user_form.lastname.data, dateofbirth=user_form.dateofbirth.data, username=user_form.username.data,
                        password_hash=user_form.password.data, streetname=user_form.streetname.data, housenumber=user_form.housenumber.data, flatnumber=user_form.flatnumber.data,
                        gender=user_form.gender.data, estate=registrationCode.user_estate, telephone=user_form.telephone.data, role=registrationCode.code_role.id)
            user.insert()
            check_added = User.query.filter_by(username=user_form.username.data).first()
            if check_added:
                # if user added change the code to used
                registrationCode.unused = False
                registrationCode.update()
                flash("Added User Successfully")
                return redirect(url_for('core.login'))
            else:
                flash("An unknown error occurred while processing your request, please contact support")
                return render_template('codeconfirmation.html', form=form)
    elif form.validate_on_submit() == False and form.registrationCode.data != '' and form.registrationCode.data is not None:
        errors = getErrorMessages(form.errors)
        for err in errors:
            flash(err)
        return render_template('codeconfirmation.html', form=form)

    elif user_form.validate_on_submit() == False and user_form.code.data and user_form.code_fullname.data:
        code_submit = {'code': user_form.code.data, 'name': user_form.code_fullname.data}
        registrationCode = Code.query.filter_by(gen_code=user_form.code.data).first()
        # display user form errors return all errors at once better UX
        session.pop('_flashes', None)
        errors = getErrorMessages(user_form.errors)
        for err in errors:
            flash(err)
        if 'streetname' in user_form and 'choices' in vars(user_form.streetname) and 'housenumber' in user_form and 'choices' in vars(user_form.housenumber):
            current_streets = StreetsMetadata.query.filter_by(estate_id=registrationCode.user_estate).all()
            street_houses = giveMeAllHousesList(current_streets[0].excluded, current_streets[0].min, current_streets[0].max)
            user_form.streetname.choices = [street.streetname for street in current_streets]
            user_form.housenumber.choices = street_houses
        return render_template('user.html', form=user_form, code_submit=code_submit)
    else:
        # display the code form
        return render_template('codeconfirmation.html', form=form)

'''
        if registrationCode:
            fullName = Code.query.filter_by(requested_for=form.fullName.data).first()

            if fullName:
                form = UserForm()

                if form.validate_on_submit():
                    user = User(firstname=form.firstname.data, lastname=form.lastname.data, dateofbirth=form.dateofbirth.data, username=form.username.data,
                                password=form.password.data, streetname=form.streetname.data, housenumber=form.housenumber.data, flatnumber=form.flatnumber.data,
                                gender=form.gender.data, telephone=form.telephone.data, role=form.role.data)
                    db.session.add(user)
                    db.session.commit()
                    flash("Added User Successfully")

                    #PHONE NUMBER CONFIRMATION SMS SHOULD COME BEFORE SHOWING THE LOGIN PAGE

                    return redirect(url_for("core.login"))

                else:
                    flash('Please fill all fields appropriately')
                return render_template("user.html", form=form)

            else:
                flash("INVALID NAME!!")

        else:
            flash("INVALID REGISTRATION CODE!!")

    return render_template("codeconfirmation.html", form=form)
'''

#OCCUPANTS PROFILE
@core.route("/profile", methods=['GET','POST'])
@login_required
def profile():

    form = UpdateUserForm()

    if form.validate_on_submit():
        print(form)
        if form.picture.data:
            username = current_user.username
            pic = add_profile_pic(form.picture.data,username)
            current_user.profile_image = pic

        current_user.telephone = form.telephone.data
        db.session.commit()
        flash('User Account Updated')
        return redirect(url_for('core.profile'))

    elif request.method == 'GET':
        form.telephone.data = current_user.telephone

    else:
        flash('Please fill form appropriately')

    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('profile.html', profile_image=profile_image, form=form)


#GUARDS PROFILE
@core.route("/guardprofile/", methods=['GET','POST'])
@login_required
def guardprofile():

    form = UpdateUserForm()

    if form.validate_on_submit():
        print(form)
        if form.picture.data:
            username = current_user.username
            pic = add_profile_pic(form.picture.data,username)
            current_user.profile_image = pic

        current_user.telephone = form.telephone.data
        db.session.commit()
        flash('User Account Updated')
        return redirect(url_for('core.guardprofile'))

    elif request.method == 'GET':
        form.telephone.data = current_user.telephone

    else:
        flash('Please fill form appropriately')

    profile_image = url_for('static', filename='profile_pics/' + current_user.profile_image)
    return render_template('guardprofile.html', profile_image=profile_image, form=form)


#GUARD'S VIEW OF OCCUPANTS PROFILE
@core.route("/viewprofile/<int:user_id>", methods = ['GET','POST'])
@login_required
def viewprofile(user_id):
    user = User.query.filter_by(id=user_id)
    return render_template('viewprofile.html', user=user)

#ADMIN'S VIEW. UPDATING OF OCCUPANT'S AND GUARD'S PROFILE
@core.route("/updateUser/<int:user_id>", methods=["GET", "POST"])
@login_required
def updateUser(user_id):
    user = User.query.get(user_id)
    form = UserForm(request.form, obj=user)
    if form.validate_on_submit():
        form.populate_obj(user)
        db.session.commit()
        flash("Updated User Successfully")
        return redirect(url_for("core.login"))
    return render_template("user.html", form=form, users=User.query.all())


#ADMIN'S VIEW. DELETING OF OCCUPANT'S AND GUARD'S PROFILE
@core.route("/deleteUser/<int:user_id>", methods=["GET", "POST"])
@login_required
def deleteUser(user_id):
    user = User.query.get(user_id)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for("core.login"))


#ADMIN'S VIEW OF ALL OCCUPANTS
@core.route('/alluserlist')
@login_required
def alluserlist():
    users = User.query.filter_by(role='occupant')
    return render_template('alluserlist.html', users=users)

#ADMIN'S VIEW OF ALL GUARDS
@core.route('/allguardlist')
@login_required
def allguardlist():
    users = User.query.filter_by(role='guard')
    return render_template('allguardlist.html', users=users)


################################################################################

#BOOKING OF GUESTS BY OCCUPANTS. ACCESS CODES SHOULD BE GENERATED AND SENT AS SMS TO THE GUEST.
@core.route("/guest", methods=["GET", "POST"])
@login_required
def createGuest():
    form = GuestForm(request.form)
    guests = Guest.query.all()
    if form.validate_on_submit():
        is_valid_phone = valdiate_phone(form.telephone.data)
        if is_valid_phone == False:
            flash("Invalid phone number")
            return render_template("guest.html", form=form, guests=guests)

        gencode = unique_code_generator1(strpool, [guest.guest_code for guest in guests])
        new_guest = Guest(user_id=current_user.id, visit_date=form.visit_date.data, firstname=form.firstname.data, lastname=form.lastname.data, gender=form.gender.data, telephone=form.telephone.data, guest_code=gencode)
        db.session.add(new_guest)
        if "firstname" in form:
            try:
                message = "hi {} your guest code is: {}".format(form.firstname.data, gencode)
                message_sent = did_you_send_notification(str(form.telephone.data), message, ['code', 'guest'])
                if message_sent['sent']:
                    new_guest.notification_sent = True
                    db.session.commit()
                    flash(message_sent['message'])
                    flash("Added Guest Successfully")
                    return redirect(url_for("core.guestlist"))
                else:
                    # if message could not be sent not let him pass
                    flash(message_sent['message'])
            except Exception as e:
                raise ValidationError("We were unable to send a notice to the guest Make sure it's a valid number, error: {}".format(str(e)))
    else:
        flash('Fill all fields')
    return render_template("guest.html", form=form, guests=guests)

#UPDATING GUEST INFORMATION
@core.route("/updateGuest/<int:guest_id>", methods=["GET", "POST"])
@login_required
def updateGuest(guest_id):
    telephone = None
    guest = Guest.query.get(guest_id)
    if guest:
        telephone = guest.telephone
    form = GuestForm(request.form, obj=guest)
    if form.validate_on_submit():
        # valdaite phone if changed
        if telephone:
            if str(request.form['telephone']) != str(telephone):
                is_valid_phone = valdiate_phone(request.form['telephone'])
                if is_valid_phone == False:
                    flash("Invalid phone number")
                    return render_template("guest.html", form=form, guests=Guest.query.all())

        form.populate_obj(guest)
        db.session.commit()
        flash("Updated Guest Successfully")
        return redirect(url_for("core.guestlist"))
    return render_template("guest.html", form=form, guests=Guest.query.all())

#CANCELING GUEST ACCESS REQUEST
@core.route("/deleteGuest/<int:guest_id>", methods=["GET", "POST"])
@login_required
def deleteGuest(guest_id):
    guest = Guest.query.get(guest_id)
    db.session.delete(guest)
    db.session.commit()
    return redirect(url_for("core.guestlist"))

#OCCUPANTS VIEW OF THEIR GUEST LIST.
@core.route('/guestlist')
@login_required
def guestlist():
    user_id = request.args.get('id')
    guests = Guest.query.filter_by(user_id=current_user.id).all()
    return render_template('guestlist.html', guests=guests)

#GUARDS VIEW OF THE OVERALL GUESTLIST
@core.route('/allguestlist')
@login_required
def allguestlist():
    guests = Guest.query.all()
    return render_template('allguestlist.html', guests=guests)

################################################################################

#OCCUPANT'S STAFF REGISTRATION
@core.route("/staff", methods=["GET", "POST"])
@login_required
def createStaff():
    form = StaffForm(request.form)
    staffs = Staff.query.all()
    if form.validate_on_submit():
        staff = Staff(user_id=current_user.id, firstname=form.firstname.data, lastname=form.lastname.data, dateofbirth=form.dateofbirth.data, gender=form.gender.data, telephone=form.telephone.data, jobdescription=form.jobdescription.data)
        db.session.add(staff)
        db.session.commit()
        flash("Added Staff Successfully")
        return redirect(url_for("core.stafflist"))
    return render_template("staff.html", form=form, staffs=staffs)

#OCCUPANT'S STAFF PROFILE UPDATE
@core.route("/updateStaff/<int:staff_id>", methods=["GET", "POST"])
@login_required
def updateStaff(staff_id):
    staff = Staff.query.get(staff_id)
    form = StaffForm(request.form, obj=staff)
    if form.validate_on_submit():
        form.populate_obj(staff)
        db.session.commit()
        flash("Updated Staff Successfully")
        return redirect(url_for("core.stafflist"))
    return render_template("staff.html", form=form, staffs=Staff.query.all())

#OCCUPANTS DELETING OF REGISTERED STAFF
@core.route("/deleteStaff/<int:staff_id>", methods=["GET", "POST"])
@login_required
def deleteStaff(staff_id):
    staff = Staff.query.get(staff_id)
    db.session.delete(staff)
    db.session.commit()
    return redirect(url_for("core.stafflist"))

#OCCUPANTS VIEW OF ALL STAFFS
@core.route('/stafflist')
@login_required
def stafflist():
    user_id = request.args.get('id')
    staffs = Staff.query.filter_by(user_id=current_user.id).all()
    return render_template('stafflist.html', staffs=staffs)

##GUARDS VIEW OF OVERALL STAFF LIST
@core.route('/allstafflist')
@login_required
def allstafflist():
    staffs = Staff.query.all()
    return render_template('allstafflist.html', staffs=staffs)

################################################################################

#OCCUPANTS PAGE FOR REQUESTING A HANDYMAN (ELECTRICAIN, PLUMBER, CARPENTER, CAR WASH, ETC)
@core.route("/service", methods=["GET", "POST"])
@login_required
def createService():
    form = ServiceForm(request.form)
    # service is what client request like task has it own data and send notifcation to handyman when created
    # service type is the category of the serveice each cateogry has his own handymens and send it own notifcation
    serivce_types = [(type.id, type.service) for type in ServiceType.query.all()]
    services = Service.query.all()
    form.serivce_type.choices = serivce_types
    form.serivce_type.validate_choice = True
    if form.validate_on_submit():

        service = Service(user_id=current_user.id, service_requested=form.service_requested.data, request_date=form.request_date.data)
        db.session.add(service)
        service.service_type = form.serivce_type.data

        #
        gencode = unique_code_generator1(strpool, [serv.code for serv in Service.query.all()])
        service_salt = random.randint(10000000, 99999999)

        current_service_id = service.id
        #current_service_type = form.service.data
        service.code = gencode
        service.salt = service_salt
        type_id = form.serivce_type.data
        all_handymen = Handymen.query.filter_by(service_type=type_id, estate_id=current_user.estate).all()
        message_sent_count = 0
        message_unsent_count = 0
        handymen_error = ""
        # here we have all data send message to handyman
        for handyman in all_handymen:
            if handyman.rate < 4:
                continue
            try:
                notification_handy_code = unique_code_generator1(strpool, [noti.code for noti in HandyMenNotfications.query.all()])
                new_notification = HandyMenNotfications(code=notification_handy_code, message='', service_id=service.id, handyman_id=handyman.id)

                db.session.add(new_notification)
                db.session.flush()
                # db.session.rollback()
                notification_id = new_notification.id
                notification_code = new_notification.code
                data = "apply?sid={}&data=".format(current_service_id)
                data += encrypt("hid={},nid={},hcode={},scode={}".format(handyman.id,notification_id, notification_code,service.code), service_salt)
                message = "new service, {} apply: ".format(service.service_requested) + create_dynamic_url(data)
                message_sent = did_you_send_notification(handyman.telephone, message, ['notification', 'handyman'])
                new_notification.message = message
                flash(message)
                # update cus it commit only we added also insert work but we use what we need only to avoid unexpected errors
                new_notification.update()
                if message_sent['sent']:
                    #Service.notification_sent = True
                    flash(message_sent['message'])
                    message_sent_count += 1
                else:
                    # if message could not be sent not let him pass
                    message_unsent_count += 1
                    handymenError = message_sent['message']
                    continue
            except Exception as e:
                if service:
                    service.delete()
                db.session.rollback()
                flash("We were unable to send a notice to the one of the handyman due to technical error, error: {}".format(str(e)))


        if len(all_handymen) > 0 and message_sent_count == 0 and len(all_handymen) != 1:
            if message_unsent_count > 0:
                flash(handymen_error + ", notification failure to {} handymen".format(message_unsent_count))
                return render_template("service.html", form=form, services=services, services_types=serivce_types)

            else:
                db.session.rollback()
                flash("unexpected error contact support")
                return render_template("service.html", form=form, services=services, services_types=serivce_types)


        if len(all_handymen) > 0 and message_sent_count == 0 and len(all_handymen) == 1:
            flash("We have no handyman With 5 stars to get the service please try again later")
        else:
            db.session.rollback()
            flash("We have sent a notification to {} of our most skilled workers".format(message_sent_count))

        db.session.add(service)
        db.session.commit()
        flash("Added Service Successfully")
        return redirect(url_for("core.servicelist"))
    return render_template("service.html", form=form, services=services, services_types=serivce_types)

#OCCUPANT'S PAGE TO UPDATE THE REQUESTED SERVICE
@core.route("/updateService/<int:service_id>", methods=["GET", "POST"])
@login_required
def updateService(service_id):
    service = Service.query.get(service_id)
    inital_service_requested = service.service_requested
    inital_service_date = service.request_date
    service_type = ServiceType.query.get(service.service_type)
    form = ServiceForm(request.form, obj=service)
    form.serivce_type.choices = [(service_type.id, service_type.service)]
    form.serivce_type.description = "Service Type Can not changed as we sent SMS already and may one of handyman accepted and on his way to you if you need new type create new task, and avoid confirm service without need it"
    form.serivce_type.validators = []
    form.serivce_type.validate_choice = False

    form.serivce_type.render_kw = {'disabled': True, 'required': False}
    if form.validate_on_submit():
        form.populate_obj(service)
        service_updated  = inital_service_requested != form.service_requested.data
        request_date_update = inital_service_date != form.request_date.data
        changes_deteacted = False
        if service_updated:
            service.service_requested = "%s" %form.service_requested.data
            changes_deteacted = True
        if request_date_update:
            service.request_date = "%s" %form.request_date.data
            changes_deteacted = True

        if changes_deteacted:
            service.update()
            flash("Updated Service Successfully")
        else:
            flash("No New Changes Detacted")
        return redirect(url_for("core.servicelist"))

    return render_template("service.html", form=form, services=Service.query.all())

#OCCUPANTS DELETION OF REQUESTED SERVICE
@core.route("/deleteService/<int:service_id>", methods=["GET", "POST"])
@login_required
def deleteService(service_id):
    service = Service.query.get(service_id)
    service_title = service.service_requested
    db.session.delete(service)
    db.session.commit()
    flash("Successfully Deleted {}".format(service_title))
    return redirect(url_for("core.servicelist"))

#OCCUPANTS VIEW OF ALL REQUESTED LISTS
@core.route('/servicelist')
@login_required
def servicelist():
    user_id = request.args.get('id')
    services = Service.query.filter_by(user_id=current_user.id).all()
    return render_template('servicelist.html', user_id=user_id, services=services)

#GUARDS VIEW OF OVERALL SERVICES REQUESTED
@core.route('/allservicelist')
@login_required
def allservicelist():
    services = Service.query.all()
    return render_template('allservicelist.html', services=services)

################################################################################

#OCCUPANTS PAGE FOR PAYING BILLS (ESTATE DUES, ELECTRICITY, WATER BILLS)
@core.route('/buySubscription', methods=['GET','POST'])
@login_required
def buySubscription():
    form = SubscriptionForm()
    if form.validate_on_submit():
        subscription = Subscription(user_id=current_user.id, subscription=form.subscription.data, amount=form.amount.data, subscription_date=form.subscription_date.data)
        db.session.add(subscription)
        db.session.commit()
        flash("Proceeding to next page for payment")
        return redirect(url_for('core.subscription'))
    return render_template('buysubscription.html', form=form)

#
@core.route('/subscription')
@login_required
def subscription():
    return render_template('subscription.html', stripe_key=stripe_key)

#THANK YOU PAGE THAT SHOWS AFTER SUCCESSFUL PAYMENT
@core.route('/thankyou')
@login_required
def thankyou():
    flash("Your payment was successful")
    return render_template('thankyou.html')

#OCCUPANTS LIST OF ALL SUBSCRIPTIONS
@core.route('/subscriptionlist')
@login_required
def subscriptionlist():
    user_id = request.args.get('id')
    subscriptions = Subscription.query.filter_by(user_id=current_user.id).all()
    return render_template('subscriptionlist.html',subscriptions=subscriptions)

#SUBSCRIPTION PAYMENT PAGE
@core.route('/payment', methods=['POST'])
@login_required
def payment():

    # CUSTOMER INFORMATION
    customer = stripe.Customer.create(email=request.form['stripeEmail'], source=request.form['stripeToken'])

    # CHARGE/PAYMENT INFORMATION
    charge = stripe.Charge.create(customer=customer.id, amount=1, currency='usd', description='Donation')

    return redirect(url_for('core.thankyou'))

################################################################################

#OCCUPANTS ENQUIRIES PAGE
@core.route('/createEnquiry', methods=['GET','POST'])
@login_required
def createEnquiry():
    form = EnquiryForm()
    enquiries = Enquiry.query.all()
    if form.validate_on_submit():
        enquiry = Enquiry(user_id=current_user.id, enquiry=form.enquiry.data, enquiry_date=form.enquiry_date.data)
        db.session.add(enquiry)
        db.session.commit()
        flash("Enquiry/Complaint added successfully!")
        return redirect(url_for("core.enquirylist"))

    return render_template('enquiry.html', form=form, enquiries=enquiries)

#OCCUPANTS PAGE TO UPDATE THEIR ENQUIRIES
@core.route("/updateEnquiry/<int:enquiry_id>", methods=["GET", "POST"])
@login_required
def updateEnquiry(enquiry_id):
    enquiry = Enquiry.query.get(enquiry_id)
    form = EnquiryForm(request.form, obj=enquiry)
    if form.validate_on_submit():
        form.populate_obj(enquiry)
        db.session.commit()
        flash("Updated Enquiry/Complaint Successfully")
        return redirect(url_for("core.enquirylist"))
    return render_template("enquiry.html", form=form, enquiry=Enquiry.query.all())

#OCCUPANTS PAGE TO DELETE AN ENQUIRY
@core.route("/deleteEnquiry/<int:enquiry_id>", methods=["GET", "POST"])
@login_required
def deleteEnquiry(enquiry_id):
    enquiry = Enquiry.query.get(enquiry_id)
    db.session.delete(enquiry)
    db.session.commit()
    return redirect(url_for("core.enquirylist"))

#OCCUPANTS PAGE TO VIEW ALL ENQUIRIES
@core.route('/enquirylist')
@login_required
def enquirylist():
    user_id = request.args.get('id')
    enquiries = Enquiry.query.filter_by(user_id=current_user.id).all()
    return render_template('enquirylist.html', enquiries=enquiries)

#GUARDS VIEW OF OVERALL ENQUIRIES
@core.route('/allenquirylist')
@login_required
def allenquirylist():
    enquiries = Enquiry.query.all()
    return render_template('allenquirylist.html', enquiries=enquiries)

################################################################################

#ADMIN'S PAGE TO CREATE ESTATE NEWS
@core.route('/createNews', methods=['GET','POST'])
@login_required
def createNews():
    form = NewsForm()
    if current_user.role in [1,2]:

        if form.validate_on_submit():
            publication = Publication(user_id=current_user.id, publication=form.publication.data, news_date=form.news_date.data)
            if current_user.role != 1:
                publication.users = current_user
            db.session.add(publication)
            db.session.commit()
            flash("News published successfully!")
            return redirect(url_for("core.newslist"))
        else:
            return render_template('community_news.html', form=form)
    else:
        flash("Sorry You have no premssion to create news")
        return redirect(url_for("core.newslist"))

#ADMIN'S PAGE TO UPDATE POSTED NEWS
@core.route("/updateNews/<int:publication_id>", methods=["GET", "POST"])
@login_required
def updateNews(publication_id):
    publication = Publication.query.get(publication_id)
    if current_user.role == 1 or current_user.id == publication.user_id:
        form = NewsForm(request.form, obj=publication)
        if form.validate_on_submit():
            try:
                form.populate_obj(publication)
                db.session.commit()
                flash("Updated News Successfully")
                return redirect(url_for("core.newslist"))
            except:
                flash("Updated News Failed")
                return redirect(url_for("core.newslist"))
        return render_template("community_news.html", form=form, publication=Publication.query.all())
    else:
        flash("You have no premssion to updateNews")
        return redirect(url_for("core.newslist"))
#ADMIN'S NEWS TO DELETE POSTED NEWS
@core.route("/deleteNews/<int:publication_id>", methods=["GET", "POST"])
@login_required
def deleteNews(publication_id):
    form = NewsForm(request.form)
    publication = Publication.query.get(publication_id)
    if current_user.role == 1 or current_user.id == publication.user_id:
        try:
            db.session.delete(publication)
            db.session.commit()
            flash("Deleted news successfully")
        except Exception as e:
            flash("could not delete new: {}".format(str(e)))
    else:
        flash("sorry you have no premssion to delete news {}".format(current_user.role==1))
    return redirect(url_for("core.newslist"))

#OCCUPANTS PAGE TO VIEW NEWS.
@core.route('/newslist')
@login_required
def newslist():

    user_id = request.args.get('id')
    getuser = User.query.filter_by(id=current_user.id).first()
    publications = db.session.query(Publication.id,Publication.id, Publication.user_id, Publication.publication, Publication.news_date, User.estate).join(User, Publication.user_id == User.id).filter(User.estate==current_user.estate).all()
    return render_template('newslist.html',news=publications)


#ADMIN'S VIEW OF ALL POSTED NEWS
@core.route('/allnewslist')
@login_required
def allnewslist():
    publications = Publication.query.all()
    return render_template('allnewslist.html', publications=publications)
# service_progresss.html


@core.route('/startcounter/<int:service_id>/<int:meta_id>', methods=['GET'])
def start_counter(service_id, meta_id):
    # wait 10 minutes and check can make smaller for more on time but in js update the serverUpdateIndex too
    serverUpdateIndex = 60
    for index in range(30):
        time.sleep(serverUpdateIndex)
        the_service = db.session.query(Service).filter_by(id=service_id).first()
        the_meta = db.session.query(ServiceMetaData).filter_by(id=meta_id).first()
        handyman = db.session.query(HandyMan).filter_by(the_meta=handyman_id).first()
        if not the_service or not the_meta or not handyman:
            return jsonify({'code': 404})

        print("wait index {}".format(index+1))
        if the_service.arrived == True:
            if the_service.handyman.id == the_meta.handyman_id:
                the_meta.completed = True
            else:
                the_meta.canceled = True
                if the_service.handyman.rating > 0:
                    the_service.handyman.rating -= 1
                    the_service.handyman.update()
            the_meta.in_progress = False
            the_meta.update()
    return jsonify({'code':200})

@core.route('/counter_update/<int:service_id>/<int:meta_id>', methods=['GET'])
def counter_updater(service_id, meta_id):
    the_service = db.session.query(Service).filter_by(id=service_id).first()
    the_meta = db.session.query(ServiceMetaData).filter_by(id=meta_id).first()
    if not the_service or not the_meta:
        return jsonify({'code':404, 'status': 'not_found', 'data': None})
    if the_meta.in_progress == True and the_meta.service.arrived == False:
        if the_meta.expire_date > datetime.datetime.utcnow():
            time_remaining = str(the_meta.expire_date - datetime.datetime.utcnow())
            time_remaining = time_remaining.split(".")
            if len(time_remaining) > 0:
                time_remaining = time_remaining[0].split(":")
                if len(time_remaining) > 1:
                    time_remaining = "{}.{}".format(time_remaining[1], time_remaining[2])
                    try:
                        time_remaining = float(time_remaining)
                        if int(time_remaining) > 0:
                            return jsonify({'code':200, 'status': 'in_progress', 'data': time_remaining})
                        else:
                            return jsonify({'code':200, 'status': 'time_over', 'data': time_remaining})
                    except:
                        pass
    else:
        the_service = db.session.query(Service).filter_by(id=service_id).first()
        the_meta = db.session.query(ServiceMetaData).filter_by(id=meta_id).first()
        if the_service.arrived == True:
            the_meta.in_progress = False
            the_meta.update()

            if the_service.handyman.id == the_meta.handyman_id:
                the_meta.completed = True
                the_meta.update()
                return jsonify({
                'data': None,
                'code': 200,
                'status': 'completed',
                'message': 'Service completed Thank you for keeping a good experience with our customers..',
                'data': None
                })
            else:
                the_meta.canceled = True
                the_meta.update()
                return jsonify({
                'data': None,
                'code': 200,
                'status': 'canceled',
                'message': 'You have canceled the service and lost 1 star rating avoid do that..',
                'data': None
                })
        else:
            the_meta.canceled = True
            the_meta.update()
            return jsonify({
            'data': None,
            'code': 200,
            'status': 'canceled',
            'message': 'You have canceled the service and lost 1 star rating avoid do that..',
            'data': None
            })

    return jsonify({'code':422, 'status': 'unkown', 'data': None})


@core.route('/service_counter', methods=['POST', 'GET'])
def wait_then_excute():
    request_data = request.json
    if not request_data:
        return jsonify({'code': 400, 'status': 'invalid', 'message': 'Invalid service Link..', 'data': None})

    if 'handyman' not in request_data or 'service_meta' not in request_data or 'service_id' not in request_data or 'service_code' not in request_data:
        return jsonify({
        'code': 422,
        'status': 'invalid',
        'message':
        'Required values are missing If this problem recurs, contact support again...',
        'data': None
        })


    service_meta = ServiceMetaData.query.filter_by(id=request_data['service_meta'], service_id=request_data['service_id'], handyman_id=request_data['handyman']).one_or_none()
    if not service_meta:
        return jsonify({
        'code': 404,
        'status': 'invalid',
        'message': 'Service is Not Found, Make sure not to edit the url',
        'data': None
        })

    elif service_meta.service.code != request_data['service_code']:
        return jsonify({
        'code': 403,
        'status': 'premssion_error',
        'message': 'You have no premssion to access this service status page',
        'data': None
        })

    elif service_meta.completed == True:
        return jsonify({
        'data': service_meta.completed,
        'code': 200,
        'status': 'completed',
        'message': 'Service completed Thank you for keeping a good experience with our customers..',
        'data': None
        })

    elif service_meta.canceled == True:
        return jsonify({
        'data': service_meta.canceled,
        'code': 200,
        'status': 'canceled',
        'message': 'You have canceled the service and lost 1 star rating avoid do that..',
        'data': None
        })

    elif service_meta.in_progress == True and service_meta.service.arrived == False:
        time_remaining = 0.00
        if service_meta.expire_date > datetime.datetime.utcnow():
            time_remaining = str(service_meta.expire_date - datetime.datetime.utcnow())
            time_remaining = time_remaining.split(".")
            if len(time_remaining) > 0:
                time_remaining = time_remaining[0].split(":")
                if len(time_remaining) > 1:
                    time_remaining = "{}.{}".format(time_remaining[1], time_remaining[2])
                    try:
                        time_remaining = float(time_remaining)
                        return jsonify({
                        'code': 200,
                        'status': 'in_progress',
                        'message': 'The service is in progress, please visit the customer quickly',
                        'data': time_remaining
                        })
                    except:
                        pass

    else:
        return jsonify({'code':404, 'status': 'no found', 'data1':service_meta.in_progress, 'message': 'task not found or expired'})




# apply for a service from link
@core.route('/apply')
def serviceapply():
    is_redirected = False

    if request.args.get("redirected"):
        is_redirected = True

    reuqest_service_id = request.args.get("sid")
    get_service = Service.query.get(reuqest_service_id)
    if not get_service:
        flash("Service Expired Or not found")
        return render_template("service_progresss.html")



    #return "{} {}".format(request.args.get("data"), get_service.salt)

    request_encrypted_data = request.args.get("data")
    request_decrypted_data = decrypt(request_encrypted_data, get_service.salt)
    request_data_object = give_me_valid_object(request_decrypted_data, ",")
    if "hcode" not in request_data_object or "hid" not in request_data_object or "nid" not in request_data_object or "scode" not in request_data_object:
        return "You provided invalid link"


    # first check notification code exist and not hacking link
    handy_notification = HandyMenNotfications.query.filter_by(code=request_data_object["hcode"]).one_or_none()
    valid_request = False
    # valdaite request data from database
    if not handy_notification:
        return "You provided invalid link 1"
    elif str(handy_notification.handyman_id) != request_data_object['hid']:
        return "You provided invalid link 2"
    elif str(handy_notification.id) != request_data_object['nid']:
        return "You provided invalid link 3"
    elif get_service.code != request_data_object['scode']:
        return "You provided invalid link 4"
    else:
        valid_request = True

    # if approved already

    is_second_apply = ServiceMetaData.query.filter_by(service_id=handy_notification.service_id, handyman_id=handy_notification.handyman_id).first()

    # now we have secure request and identitify the handyman securely
    db_service = handy_notification.service
    db_handyman = handy_notification.handyman
    new_service_meta = ServiceMetaData.query.filter_by(service_id=db_service.id, handyman_id=db_handyman.id).first()

    # repeat visit the link
    if is_second_apply and is_redirected == False:
        if is_second_apply.canceled == True:
            flash("You have canceled this service and we dudct 1 star from your rating")
            return render_template("service_progresss.html")

        if is_second_apply.canceled == False and is_second_apply.completed == False:
            flash("You have already accepted this task, quickly go to the customer.")
            final_data = {'handyman': db_handyman.id, 'service_meta': new_service_meta.id, 'service_id': db_service.id, 'service_code': db_service.code}
            return render_template("service_progresss.html", data=final_data, redirected=True)

        if is_second_apply.completed == True:
            flash("{} Thank you for visit the client fast you completed this task wait for others".format(new_service_meta.id))
            return render_template("service_progresss.html")

    # redirected
    if new_service_meta and new_service_meta.canceled == True and is_redirected == True:
        flash("You have canceled this service and we dudct 1 star from your rating")
        return render_template("service_progresss.html")

    if new_service_meta and new_service_meta.completed == True  and is_redirected == True:
        flash("{} Thank you for visit the client fast you completed this task wait for others".format(new_service_meta.id))

        return render_template("service_progresss.html")


    if new_service_meta and is_redirected == True:
        final_data = {'handyman': db_handyman.id, 'service_meta': new_service_meta.id, 'service_id': db_service.id, 'service_code': db_service.code}
        return render_template("service_progresss.html", data=final_data, redirected=True)

    new_service_meta = None
    try:
        approved_time = datetime.datetime.utcnow()
        expired_time_at = approved_time + datetime.timedelta(minutes=30)
        db_service.last_approve_date = approved_time
        db_service.approved = True
        db_service.asigned_to = handy_notification.handyman.id
        db_service.update()
        db_service = handy_notification.service
        new_service_meta = ServiceMetaData(service_id=db_service.id, handyman_id=db_handyman.id, expire_date=expired_time_at)
        new_service_meta.insert()
        new_service_meta.in_progress = True
        new_service_meta.update()
    except Exception as e:
        return "Unkown error Happend While approve your Request: {}".format(str(e))

    # the corn job or samilr here timedelta(minutes=n)
    final_data = {'handyman': db_handyman.id, 'service_meta': new_service_meta.id, 'service_id': db_service.id, 'service_code': db_service.code}
    flash("Congratulations on accepting this service, hurry up to the customer by {} or else you will lose 1 star from your rating".format(new_service_meta.expire_date))
    return render_template("service_progresss.html", data=final_data, redirected=True, start=True)



@core.route('/reset-confirm', methods=['GET', 'POST'])
def reset_confirm():
    if not current_user.is_anonymous:
        flash("You Are Logged In Already..")
        return redirect(url_for('core.index'))

    if 'uid' not in request.args or 'token' not in request.args or 'code' not in  request.args:
        flash("invalid or expired reset url used..")
        return redirect(url_for('core.reset_password'))



    request_userid = "%s" %request.args["uid"]
    request_tokenid = "%s" %request.args["token"]
    request_tokencode = "%s" %request.args["code"]

    is_vaid_token = ResetPasswordTokens.query.filter_by(id=request_tokenid, hash_code=request_tokencode, user_id=request_userid).first()


    if not is_vaid_token:
        # token id not exist and hash not exist


        flash("invalid or expired reset url used..")
        return redirect(url_for('core.reset_password'))

    get_user = User.query.filter_by(id=is_vaid_token.user_id).first()


    if not get_user:
        flash("invalid or expired reset url used..")
        return redirect(url_for('core.reset_password'))

    user_hash = get_user.password_hash
    last_5_words_hpass = user_hash[len(user_hash)-5:len(user_hash)]
    beforelast_5_words_hpass = user_hash[len(user_hash)-10:len(user_hash)-5]

    code = last_5_words_hpass + str(is_vaid_token.expiry_date) + str(get_user.id) + beforelast_5_words_hpass

    if str(code) != code:
        flash("invalid or expired reset url used..")
        return redirect(url_for('core.reset_password'))

    is_avail = is_vaid_token.expiry_date > datetime.datetime.utcnow()
    if is_avail:
        hash_level2 = generate_password_hash(str(is_vaid_token.hash_code) + str(datetime.datetime.utcnow()))
        is_vaid_token.hash_code = hash_level2
        is_vaid_token.update()
        flash("Congratulations You can reset your password now")
        # switch securly to update password with smart change to token key this need squence
        return redirect(url_for('core.update_password', uid=is_vaid_token.user_id, code=is_vaid_token.hash_code, token=is_vaid_token.id))
    else:
        flash("Sorry Url Expired reset password again")
        return redirect(url_for('core.reset_password'))

@core.route('/update-password', methods=['GET', 'POST'])
def update_password():
    uid = "%s" %request.args["uid"]
    token = "%s" %request.args["token"]
    code = "%s" %request.args["code"]

    is_vaid_token = ResetPasswordTokens.query.filter_by(id=token, hash_code=code, user_id=uid).first()

    if is_vaid_token.expiry_date < datetime.datetime.utcnow():
        flash("Sorry Url Expired reset password again")
        return redirect(url_for('core.reset_password'))

    if is_vaid_token:
        updateForm = UpdatePassword(request.form)
        if request.method == 'POST':
            if updateForm.validate_on_submit():
                if updateForm.password.data is not None:
                    is_vaid_token.user.password_hash = generate_password_hash(updateForm.password.data)
                    is_vaid_token.expired = True
                    is_vaid_token.user.update()
                    flash("You updated the password Successfully..")
                    return redirect(url_for('core.login'))
                else:
                    flash("Please enter a valid password")
                    return render_template('resetpass.html', form=updateForm, level=3)


        return render_template('resetpass.html', form=updateForm, level=3)
    else:
        flash("Sorry Invalid URL or Maybe Expired")
        return redirect(url_for('core.reset_password'))


@core.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if not current_user.is_anonymous:
        flash("You Are Logged In Already..")
        return redirect(url_for('core.index'))

    resetForm = ResetPassword(request.form)
    if request.method == 'POST':
        if resetForm.validate_on_submit():
            user = User.query.filter_by(username=resetForm.email.data).first()

            if not user:
                flash("This Email Is not exist")
                return render_template('resetpass.html', form=resetForm, level=1)

            user_active_tokens = ResetPasswordTokens.query.filter(ResetPasswordTokens.expiry_date > datetime.datetime.utcnow()).filter(ResetPasswordTokens.user_id==user.id).first()
            if user_active_tokens:
                remain = user_active_tokens.expiry_date - datetime.datetime.utcnow()
                remain_minutes = remain.seconds//60
                flash("We send you Already the reset link on your email please check your email, Link are still vaild for about {} Minute".format(remain_minutes))
                return render_template('resetpass.html', form=resetForm, level=2)

            # new request after expired

            try:
                # make old token expired
                old_tokens = ResetPasswordTokens.query.filter(ResetPasswordTokens.expiry_date < datetime.datetime.utcnow()).filter(ResetPasswordTokens.user_id==user.id).filter(ResetPasswordTokens.expired==False).all()
                if len(old_tokens) > 0:
                    for token in old_tokens:
                        token.expired = True
                        token.update()

                createdate = datetime.datetime.utcnow()
                expire_createdate = createdate + datetime.timedelta(minutes=5)
                last_5_words_hpass = user.password_hash[len(user.password_hash)-5:len(user.password_hash)]
                beforelast_5_words_hpass = user.password_hash[len(user.password_hash)-10:len(user.password_hash)-5]

                code = last_5_words_hpass + str(expire_createdate) + str(user.id) + beforelast_5_words_hpass
                unique_hash =  generate_password_hash(code)
                createnewToken = ResetPasswordTokens(hash_code=unique_hash, create_date=createdate, expiry_date=expire_createdate, user_id=user.id)
                createnewToken.insert()
                query_paremeters = "?uid={}&code={}&token={}".format(user.id, createnewToken.hash_code, createnewToken.id)
                reset_url = dynamic_endpointurl("reset-confirm", query_paremeters)
                user_email = createnewToken.user.username

                msg = Message(
                        subject='Reset Password URL',
                        recipients=[user_email],
                        sender='Admin Estate App')
                mail_message = 'To Reset Password Click On this link: \n %s' %reset_url
                msg.body = mail_message
                email_sent = mail.send(msg)
                flash("We Sent Reset Link On your Email %s Please click on this link"%user_email)
                return render_template('resetpass.html', form=resetForm, level=2)

            except:
                flash("unexpected error occurred while reset your password please contact us")
                return render_template('resetpass.html', form=resetForm, level=1)

        else:
            flash("Could not send data Reset request invalid email")
            return render_template('resetpass.html', form=resetForm, level=1)
    else:
        return render_template('resetpass.html', form=resetForm, level=1)




"""
# remeber me
@core.route('/cookie')
def remeber_me():
    cookie_id = 'as1'
    username = request.cookies.get(cookie_id)
    #cookie_key = request.cookies.get(cookie_id)
    #cookie_salt = request.cookies.get(cookie_id)
    data = {'cookie_id': cookie_id, 'username':username, 'message': 'create New cookie'}
    response = app.response_class(
            response=json.dumps(data),
            status=200,
            mimetype='application/json'
        )
    if username:
        return response
    else:
        username = 'newuser2'
        response.set_cookie(cookie_id, username)
        data = {'cookie_id': cookie_id, 'message': 'Created new cookie'}
        response.response = json.dumps(data)
    return response

"""
