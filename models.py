import os
import jinja2
from google.appengine.ext import db
import hashlib
import random
from string import letters

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

def render_str(template, **params):
    t = jinja_env.get_template(template)
    return t.render(params)

##### wine stuff
class Wine(db.Model):
    name = db.StringProperty(required = True)
    country = Country()
    subregion = Subregion()
    wine_type = WineType()
    grape = Grape()
    maker = db.StringProperty()
    year = db.StringProperty()
    terroir = db.StringProperty()
    alc = db.StringProperty()
    prize = db.StringProperty()
    value = db.StringProperty()
    more_info = db.TextProperty()

    def render(self):
        self._render_text = self.content.replace('\n', '<br>')
        return render_str("wine.html", p = self)

    def as_dict(self):
        d = {'name': self.name,
             'country': self.country,
             'subregion': self.subregion,
             'wine_type': self.wine_type,
             'grape': self.grape,
             'maker': self.maker,
             'year': self.year,
             'terroir': self.terroir,
             'alc': self.alc,
             'prize': self.prize,
             'more_info': self.more_info,             
             'value': self.value}
        return d

##### user stuff    
class User(db.Model):
    name = db.StringProperty(required = True)
    pw_hash = db.StringProperty(required = True)
    email = db.StringProperty()

    @classmethod
    def by_id(cls, uid):
        return User.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = User.all().filter('name =', name).get()
        return u

    @classmethod
    def register(cls, name, pw, email = None):
        pw_hash = make_pw_hash(name, pw)
        return User(parent = users_key(),
                    name = name,
                    pw_hash = pw_hash,
                    email = email)

    @classmethod
    def login(cls, name, pw):
        u = cls.by_name(name)
        if u and valid_pw(name, pw, u.pw_hash):
            return u
    
def make_salt(length = 5):
    return ''.join(random.choice(letters) for x in xrange(length))

def make_pw_hash(name, pw, salt = None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(name + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(name, password, salt)

def users_key(group = 'default'):
    return db.Key.from_path('users', group)

##### country stuff
class Country(db.Model):
    name = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return Country.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = Country.all().filter('name =', name).get()
        return u

##### subregion stuff
class Subregion(db.Model):
    name = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return Subregion.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = Subregion.all().filter('name =', name).get()
        return u

##### wine type stuff
class WineType(db.Model):
    name = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return WineType.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = WineType.all().filter('name =', name).get()
        return u

##### grape type stuff
class Grape(db.Model):
    name = db.StringProperty(required = True)

    @classmethod
    def by_id(cls, uid):
        return Grape.get_by_id(uid, parent = users_key())

    @classmethod
    def by_name(cls, name):
        u = Grape.all().filter('name =', name).get()
        return u
    
    
