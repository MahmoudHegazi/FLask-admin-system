from flask import render_template, request, flash, redirect, url_for, Blueprint, session, current_app
from flask_login import login_user, current_user, logout_user, login_required
from estate_management.core.userforms import UserForm, GuestForm, StaffForm, ServiceForm, LoginForm, EnquiryForm, NewsForm, SubscriptionForm, UpdateUserForm, CodeForm, GeneratorForm
from estate_management.usermodels import User, Guest, Staff, Service, Enquiry, Publication, Subscription, Code, StreetsMetadata
from estate_management.core.picture_handler import add_profile_pic
from estate_management.core.guardCodeGenerator import code_generator, strpool
from estate_management import giveMeAllHousesList, getValidExclude
from estate_management import db, stripe_key, super_admin_permission, super_admin_permission, estate_admin_permission, guard_permission
from flask_principal import Principal, Identity, AnonymousIdentity, \
     identity_changed
import sys


core = Blueprint('core',__name__, template_folder='templates')


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
        #session['username'] = request.form['username']
        user = User.query.filter_by(username=form.username.data).first()

        if user == None:
            flash("User is not registered! Please register!")
            return redirect(url_for('core.createUser'))

        if user.check_password(form.password.data) and user is not None:
            login_user(user)
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
    if form.validate_on_submit():
        valid_form = True
        # import inspect print(inspect.getmembers(form, lambda a:not(inspect.isroutine(a))))
        # SEARCH FOR REGISTRATION CODE GIVEN BY THE ADMIN
        registrationCode = Code.query.filter_by(gen_code=form.registrationCode.data).first()

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
                street_houses = giveMeAllHousesList(current_streets[0].excluded, current_streets[0].min, current_streets[0].max)
                user_form.streetname.choices = [street.streetname for street in current_streets]
                user_form.housenumber.choices = street_houses

            code_submit = {'code': form.registrationCode.data, 'name': form.fullName.data}
            return render_template('user.html', form=user_form, code_submit=code_submit)
    # Second Form
    elif user_form.validate_on_submit():
        print(user_form.code.data)
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
        guest = Guest(user_id=current_user.id, visit_date=form.visit_date.data, firstname=form.firstname.data, lastname=form.lastname.data, gender=form.gender.data, telephone=form.telephone.data)
        db.session.add(guest)
        db.session.commit()
        flash("Added Guest Successfully")
        return redirect(url_for("core.guestlist"))
    else:
        flash('Fill all fields')
    return render_template("guest.html", form=form, guests=guests)

#UPDATING GUEST INFORMATION
@core.route("/updateGuest/<int:guest_id>", methods=["GET", "POST"])
@login_required
def updateGuest(guest_id):
    guest = Guest.query.get(guest_id)
    form = GuestForm(request.form, obj=guest)
    if form.validate_on_submit():
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
    services = Service.query.all()
    if form.validate_on_submit():
        service = Service(user_id=current_user.id, service_requested=form.service_requested.data, request_date=form.request_date.data)
        db.session.add(service)
        db.session.commit()
        flash("Added Service Successfully")
        return redirect(url_for("core.servicelist"))
    return render_template("service.html", form=form, services=services)

#OCCUPANT'S PAGE TO UPDATE THE REQUESTED SERVICE
@core.route("/updateService/<int:service_id>", methods=["GET", "POST"])
@login_required
def updateService(service_id):
    service = Service.query.get(service_id)
    form = ServiceForm(request.form, obj=service)
    if form.validate_on_submit():
        form.populate_obj(service)
        db.session.commit()
        flash("Updated Service Successfully")
        return redirect(url_for("core.servicelist"))
    return render_template("service.html", form=form, services=Service.query.all())

#OCCUPANTS DELETION OF REQUESTED SERVICE
@core.route("/deleteService/<int:service_id>", methods=["GET", "POST"])
@login_required
def deleteService(service_id):
    service = Service.query.get(service_id)
    db.session.delete(service)
    db.session.commit()
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

    if form.validate_on_submit():
        publication = Publication(user_id=current_user.id, publication=form.publication.data, news_date=form.news_date.data)
        db.session.add(publication)
        db.session.commit()
        flash("News published successfully!")
        return redirect(url_for("core.newslist"))

    return render_template('community_news.html', form=form)

#ADMIN'S PAGE TO UPDATE POSTED NEWS
@core.route("/updateNews/<int:news_id>", methods=["GET", "POST"])
@login_required
def updateNews(publication_id):
    publication = Publication.query.get(publication_id)
    form = NewsForm(request.form, obj=publication)
    if form.validate_on_submit():
        form.populate_obj(publication)
        db.session.commit()
        flash("Updated News Successfully")
        return redirect(url_for("core.newslist"))
    return render_template("community_news.html", form=form, publication=Publication.query.all())

#ADMIN'S NEWS TO DELETE POSTED NEWS
@core.route("/deleteNews/<int:news_id>", methods=["GET", "POST"])
@login_required
def deleteNews(publication_id):
    publication = Publication.query.get(publication_id)
    db.session.delete(publication)
    db.session.commit()
    return redirect(url_for("core.newslist"))

#OCCUPANTS PAGE TO VIEW NEWS.
@core.route('/newslist')
@login_required
def newslist():
    user_id = request.args.get('id')
    publications = Publication.query.filter_by(user_id=current_user.id).all()
    return render_template('newslist.html',publications=publications)

#ADMIN'S VIEW OF ALL POSTED NEWS
@core.route('/allnewslist')
@login_required
def allnewslist():
    publications = Publication.query.all()
    return render_template('allnewslist.html', publications=publications)
