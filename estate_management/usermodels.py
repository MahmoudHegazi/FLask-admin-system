from estate_management import db, login_manager, getMeLoggedUser
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)


class Estate(db.Model, UserMixin):
    __tablename__ = 'estates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False, default='A Estate')
    address = db.Column(db.String, nullable=False, default='')
    city = db.Column(db.String, nullable=False, default='')
    user_estate = db.relationship('User', cascade="all,delete", backref='user_estate', lazy='dynamic')
    code_estate = db.relationship('Code', cascade="all,delete", backref='code_estate', lazy='dynamic')
    street_estate = db.relationship('StreetsMetadata', cascade="all,delete", backref='street_estate', lazy='dynamic')

    def __init__(self, name, address, city):
        self.name = name
        self.name = address
        self.name = city

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


    def format(self):
        return {
        'id': self.id,
        'name': self.name,
        }

    def __repr__(self):
        return f"{self.name}"



class Role(db.Model, UserMixin):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, nullable=False, primary_key=True)
    name = db.Column(db.String, nullable=False)
    # cascade means if you delete parent delete child note this crtical here if you deleted role you may delete all users take care
    user_role = db.relationship('User', cascade="all,delete", backref='user_role', lazy='dynamic')
    code_role = db.relationship('Code', cascade="all,delete", backref='code_role', lazy='dynamic')

    def __init__(self, name):
        self.name = name

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


    def format(self):
        return {
        'name': self.name,
        }

    def __repr__(self):
        return f"{self.name}"


class StreetsMetadata(db.Model, UserMixin):
    __tablename__ = 'streets_metadata'

    id = db.Column(db.Integer, primary_key=True)
    streetname = db.Column(db.String, nullable=False)
    min = db.Column(db.Integer, nullable=False)
    max = db.Column(db.Integer, nullable=False)
    excluded = db.Column(db.String, nullable=True, default='')
    estate_id = db.Column(db.Integer, db.ForeignKey('estates.id'))


    def __init__(self, streetname, min, max, excluded, estate_id):
        self.streetname = streetname
        self.min = min
        self.max = max
        self.excluded = excluded
        self.estate_id = estate_id

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


    def format(self):
        return {
        'id': self.id,
        'streetname': self.streetname,
        'min': self.min,
        'max': self.max,
        'excluded': self.excluded,
        'estate_id': self.estate_id,
        }

    def __repr__(self):
        return f"Street: {self.streetname} Range:{self.min}-{self.max}"


class User(db.Model, UserMixin):
    __tablename__ = 'users'
    # this can be db.PrimaryKeyConstraint if you want it to be a primary key
    __table_args__ =  (db.UniqueConstraint('username'),db.UniqueConstraint('telephone'), db.PrimaryKeyConstraint('id'),)
    id = db.Column(db.Integer, primary_key=True)
    profile_image = db.Column(db.String(20), nullable=False, default='default_profile.png')
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    dateofbirth = db.Column(db.DateTime, nullable=False)
    # better to set this to unique
    username = db.Column(db.String, nullable=False, unique=True)
    password_hash = db.Column(db.String, nullable=False)
    # text can accept integer
    streetname = db.Column(db.Text, nullable=False)
    housenumber = db.Column(db.String, nullable=False)
    flatnumber = db.Column(db.String, nullable=True, default=None)
    gender = db.Column(db.String, nullable=False)
    telephone = db.Column(db.Text, nullable=False, unique=True)
    registration_date = db.Column(db.DateTime(), nullable=False, default=datetime.now())
    estate = db.Column(db.Integer, db.ForeignKey('estates.id'))
    role = db.Column(db.Integer, db.ForeignKey('roles.id'))
    guests = db.relationship('Guest', backref='host', lazy='dynamic')
    staffs = db.relationship('Staff', backref='boss', lazy='dynamic')
    services = db.relationship('Service', backref='requester', lazy='dynamic')
    enquiries = db.relationship('Enquiry', backref='asker', lazy='dynamic')
    subscriptions = db.relationship('Subscription', backref='subscriber', lazy='dynamic')
    news = db.relationship('Publication', back_populates='users')

    def __init__(self, firstname, lastname, dateofbirth, username, password_hash, streetname, housenumber, flatnumber, gender, telephone, role, estate):
        self.firstname = firstname
        self.lastname = lastname
        self.dateofbirth = dateofbirth
        self.username = username
        self.password_hash = generate_password_hash(password_hash)
        self.streetname = streetname
        self.housenumber = housenumber
        self.flatnumber = flatnumber
        self.gender = gender
        self.telephone = telephone
        self.role = role
        self.estate = estate


    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return f"NAME: {self.firstname} {self.lastname}, DATE OF BIRTH: {self.dateofbirth}, GENDER: {self.gender}, PHONE NUMBER: +234{self.telephone}, ADDRESS: {self.flatnumber}, number {self.housenumber}, {self.streetname}"

    def check_password(self,password):
        return check_password_hash(self.password_hash,password)

    def validate_username(self, data):
        # self.username and data are the same object
        if username.data[0].isdigit():  # Check whether the first digit is a number
            raise ValidationError('Username Cannot start with a number')
    """
    def validate_phone(self, data):
        '''Regular verification of mobile phone number'''
        phone = telephone.data
        if not re.search(r'^234\d{10}$', phone):
            raise ValidationError('Mobile phone number format is incorrect')
    """

    def has_role(self, role):
        # db is your database session.
        query = db.query(Role).filter(Role.name == role).first()
        if query:
            if query.name in self.roles:
                return True
        return False

    def format(self):
        return {
        'firstname': self.firstname,
        'lastname': self.lastname,
        'dateofbirth': self.dateofbirth,
        'username': self.username,
        'streetname': self.streetname,
        'housenumber': self.housenumber,
        'flatnumber': self.flatnumber,
        'gender': self.gender,
        'telephone': self.telephone,
        'role': self.role
        }

class Guest(db.Model):
    __tablename__ = 'guests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    visit_date = db.Column(db.DateTime, default=datetime.utcnow)
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    gender = db.Column(db.String, nullable=False)
    telephone = db.Column(db.Text, nullable=False)

    def __init__(self, user_id, visit_date, firstname, lastname, gender, telephone):
        self.user_id = user_id
        self.visit_date = visit_date
        self.firstname = firstname
        self.lastname = lastname
        self.gender = gender
        self.telephone = telephone

    def __repr__(self):
        return f"Name: {self.firstname} {self.lastname}, Sex: {self.gender}, Phone Number: +234{self.telephone}, Date: {self.visit_date}, Host: {self.user_id}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Staff(db.Model):
    __tablename__ = 'staffs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    firstname = db.Column(db.String, nullable=False)
    lastname = db.Column(db.String, nullable=False)
    dateofbirth = db.Column(db.DateTime, nullable=False)
    gender = db.Column(db.String, nullable=False)
    telephone = db.Column(db.String, nullable=False)
    jobdescription = db.Column(db.String, nullable=False)


    def __init__(self, user_id, firstname, lastname, dateofbirth, gender, telephone, jobdescription):
        self.user_id = user_id
        self.firstname = firstname
        self.lastname = lastname
        self.dateofbirth = dateofbirth
        self.gender = gender
        self.telephone = telephone
        self.jobdescription = jobdescription

    def __repr__(self):
        return f"Name: {self.firstname} {self.lastname}, Date of birth: {self.dateofbirth}, Sex: {self.gender}, Phone Number: +234{self.telephone}, Job description: {self.jobdescription}, Boss: {self.user_id}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Code(db.Model):
    __tablename__ = "codes"
    id = db.Column(db.Integer, primary_key=True)
    requested_for = db.Column(db.String, nullable=False)
    gen_code = db.Column(db.Text, nullable=False)
    gen_date = db.Column(db.DateTime(), nullable=False, default=datetime.utcnow)
    unused = db.Column(db.Boolean, nullable=True, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), default=getMeLoggedUser(), nullable=False)
    user_role = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    user_estate = db.Column(db.Integer, db.ForeignKey('estates.id'), nullable=False)

    def __init__(self, requested_for, user_role, user_estate, gen_date, gen_code):
        self.requested_for = requested_for
        self.user_role = user_role
        self.user_estate = user_estate
        self.gen_date = gen_date
        self.gen_code = gen_code

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()



class Service(db.Model):

    __tablename__ = 'services'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    service_requested = db.Column(db.String, nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, service_requested, request_date):
        self.user_id = user_id
        self.service_requested = service_requested
        self.request_date = request_date

    def __repr__(self):
        return f"{self.service_requested} requested on {self.request_date}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class Enquiry(db.Model):

    __tablename__ = 'enquiries'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    enquiry = db.Column(db.Text, nullable=False)
    enquiry_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, enquiry, enquiry_date):
        self.user_id = user_id
        self.enquiry = enquiry
        self.enquiry_date = enquiry_date

    def __repr__(self):
        return f"Enquiry: {self.enquiry}.... Submitted on {self.enquiry_date}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()


class Publication(db.Model):

    __tablename__ = 'publications'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    publication = db.Column(db.Text, nullable=False)
    news_date = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', back_populates='news')

    def __init__(self, reporter_id, news_date):
        self.user_id = user_id
        self.publication = publication
        self.news_date = news_date

    def __repr__(self):
        return f"{self.publication}.... Written on {self.news_date}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()



class Subscription(db.Model):

    __tablename__ = 'subscriptions'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    subscription = db.Column(db.String, nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    subscription_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, user_id, subscription, amount, subscription_date):
        self.user_id = user_id
        self.subscription = subscription
        self.amount = amount
        self.subscription_date = subscription_date

    def __repr__(self):
        return f"{self.amount} naira {self.subscription} was purchased on {self.news_date}"

    def insert(self):
        db.session.add(self)
        db.session.commit()

    def update(self):
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

# clear and rebuild database comment in proudction



# add the roles for the app
"""
     uncomment this lines below if you uncommented drop_app and create_all and add superadmin
"""
"""
db.drop_all()
db.create_all()

n = User(firstname='super', lastname='admin', dateofbirth=datetime.now(), username='admin', password_hash='admin', streetname='streetx', housenumber='1', flatnumber='2', gender='male', telephone=4454545454, role=1, estate=1)
n.insert()
"""
if Role.query.count() is None or Role.query.count() == 0:
    superAdminRole = Role(name='superadmin')
    estateAdminRole = Role(name='estateadmin')
    GuardRole = Role(name='guard')
    occupationRole = Role(name='occupant')
    guestRole = Role(name='guest')
    developerRole = Role(name='developer')
    tempRole = Role(name='temp')


    db.session.add(superAdminRole)
    db.session.add(estateAdminRole)
    db.session.add(GuardRole)
    db.session.add(occupationRole)
    db.session.add(guestRole)
    db.session.add(developerRole)
    db.session.add(tempRole)
    db.session.commit()
