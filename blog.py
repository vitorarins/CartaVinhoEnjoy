#!/usr/bin/python
#coding: utf-8
import os
import re
import hmac
import logging
import json
import webapp2
import utils
import jinja2
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import flowables
import reportlab.rl_config
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime, timedelta
from google.appengine.api import memcache
from google.appengine.ext import db
from models import User, Wine, WineType, Country, Subregion, Grape

template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),
                               autoescape = True)

secret = 'dvamefFVAEWfdsnclaSFvjudfaVfnasfart'


def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())

def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val

class BlogHandler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a, **kw)

    def render_str(self, template, **params):
        params['user'] = self.user
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self, template, **kw):
        self.write(self.render_str(template, **kw))

    def render_json(self, d):
        json_txt = json.dumps(d)
        self.response.headers['Content-Type'] = 'application/json; charset=UTF-8'
        self.write(json_txt)

    def set_secure_cookie(self, name, val):
        cookie_val = make_secure_val(val)
        self.response.headers.add_header(
            'Set-Cookie',
            '%s=%s; Path=/' % (name, cookie_val))

    def read_secure_cookie(self, name):
        cookie_val = self.request.cookies.get(name)
        return cookie_val and check_secure_val(cookie_val)

    def login(self, user):
        self.set_secure_cookie('user_id', str(user.key().id()))

    def logout(self):
        self.response.headers.add_header('Set-Cookie', 'user_id=; Path=/')

    def initialize(self, *a, **kw):
        webapp2.RequestHandler.initialize(self, *a, **kw)
        uid = self.read_secure_cookie('user_id')
        self.user = uid and User.by_id(int(uid))

        if self.request.url.endswith('.json'):
            self.format = 'json'
        else:
            self.format = 'html'

class MainPage(BlogHandler):
    def get(self):
        wines,age = get_wines()
        if self.format == 'html':
            self.render("front.html",wines=wines,age=age_str(age))
        elif self.format == 'json':
            return self.render_json([p.as_dict() for p in wines])

##### blog stuff

        
def get_wines(update = False):
    q = Wine.all().order('-name').fetch(limit=10)
    mc_key = 'BLOGS'
    wines, age = age_get(mc_key)
    if update or wines is None:
        wines = list(q)
        age_set(mc_key,wines)
    return wines, age

def age_str(age):
    s = 'queried %s seconds ago'
    age = int(age)
    if age == 1:
        s = s.replace('seconds','second')
    return s % age

def age_set(key,val):
    save_time = datetime.utcnow()
    memcache.set(key,(val,save_time))

def age_get(key):
    r = memcache.get(key)
    if r:
        val, save_time = r
        age = (datetime.utcnow() - save_time).seconds
    else:
        val, age = None,0
    return val,age

def add_wine(wine):
    wine.put()
    get_wines(update=True)
    return str(wine.key().id())

def delete_wine(wine):
    db.delete(wine)
    get_wines(update=True)
    return str(wine.key().id())
    
class WinePage(BlogHandler):
    def get(self,entry_id):
        wine_key = 'WINE_' + entry_id
        key = db.Key.from_path('Wine',int(entry_id))
        wine = db.get(key)
        age_set(wine_key,wine)
        age=0
        if not wine:
            self.error(404)
            return
        if self.format == 'html':
            self.render("permalink.html", entry=wine,age=age_str(age))
        elif self.format == 'json':
            self.render_json(wine.as_dict())


class NewWine(BlogHandler):
    def get(self):
        if self.user:
            c = Country.all().order('-name')
            countries = list(c)
            s = Subregion.all().order('-name')
            subregion = list(s)
            wt = WineType.all().order('-name')
            wine_types = list(wt)
            g = Grape.all().order('-name')
            grapes = list(g)
            self.render("newwine.html",countries=countries,
                        subregions=subregion,
                        wine_types=wine_types,
                        grapes=grapes)
        else:
            self.redirect("/login")

    def post(self):
        if not self.user:
            self.redirect('/')

        country = self.request.get('country')
        if country:
            c = Country(name=country)
            
        subregion = self.request.get('subregion')
        if subregion:
            s = Subregion(name=subregion, country=c)
            
        wine_type = self.request.get('wine_type')
        if wine_type:
            wt = WineType(name=wine_type)
            
        grape = self.request.get('grape')
        if grape:
            g = Grape(name=grape)
            
        name = self.request.get('name')
        maker = self.request.get('maker')
        year = self.request.get('year')
        terroir = self.request.get('terroir')
        alc = self.request.get('alc')
        value = self.request.get('value')
        prize = self.request.get('prize')
        more_info = self.request.get('more_info')

        if name and wine_type:
            p = Wine(country=c,
                     subregion=s,
                     wine_type=wt,
                     grape=g,
                     name=name,
                     maker=maker,
                     year=year,
                     terroir=terroir,
                     alc=alc,
                     value=value,
                     prize=prize,
                     more_info=more_info)
            id = add_wine(p)
            self.redirect('/%s' % id)
        else:
            error = "É preciso adicionar ao menos o nome e um tipo de uva."
            self.render("newwine.html",
                        country=country,
                        subregion=subregion,
                        wine_type=wine_type,
                        grape=grape,
                        name=name,
                        maker=maker,
                        year=year,
                        terroir=terroir,
                        alc=alc,
                        value=value,
                        prize=prize,
                        more_info=more_info,
                        error=error)

class EditWine(BlogHandler):

    def post(self, wine_id):
        iden = int(wine_id)
        wine = db.get(db.Key.from_path('Wine', iden))

        country = self.request.get('country')
        if country:
            wine.country = Country(name=country)
    
        subregion = self.request.get('subregion')
        if subregion:
            wine.subregion = Subregion(name=subregion, country=c)
        
        wine_type = self.request.get('wine_type')
        if wine_type:
            wine.wine_type = WineType(name=wine_type)
            
        grape = self.request.get('grape')
        if grape:
            wine.grape = Grape(name=grape)
            
        wine.name = self.request.get('name')
        wine.maker = self.request.get('maker')
        wine.year = self.request.get('year')
        wine.terroir = self.request.get('terroir')
        wine.alc = self.request.get('alc')
        wine.value = self.request.get('value')
        wine.prize = self.request.get('prize')
        wine.more_info = self.request.get('more_info')

        id = add_wine(wine)
        self.redirect('/%s' % id)

    def get(self, wine_id):
        if not self.user:
            self.redirect('/login')
        wine_key = 'WINE_' + wine_id
        key = db.Key.from_path('Wine',int(wine_id))
        wine = db.get(key)
        age_set(wine_key,wine)
        age=0
        if not wine:
            self.error(404)
            return    
        self.render('newwine.html',
                    country=wine.country.name,
                    subregion=wine.subregion.name,
                    wine_type=wine.wine_type.name,
                    grape=wine.grape.name,
                    name=wine.name,
                    maker=wine.maker,
                    year=wine.year,
                    terroir=wine.terroir,
                    alc=wine.alc,
                    value=wine.value,
                    prize=wine.prize,
                    more_info=wine.more_info,                    
                    error="")

class DeleteWine(BlogHandler):
    def get(self, wine_id):
        if not self.user:
            self.redirect('/login')
        wine_key = 'WINE_' + wine_id
        wine,age = age_get(wine_key)
        if not wine:
            key = db.Key.from_path('Wine',int(wine_id))
            wine = db.get(key)
            age_set(wine_key,wine)
            age=0
        if not wine:
            self.error(404)
            return    
        delete_wine(wine)
        self.redirect('/')

USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(username):
    return username and USER_RE.match(username)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(password):
    return password and PASS_RE.match(password)

EMAIL_RE  = re.compile(r'^[\S]+@[\S]+\.[\S]+$')
def valid_email(email):
    return not email or EMAIL_RE.match(email)

class Signup(BlogHandler):
    def get(self):
        self.render("signup-form.html")

    def post(self):
        have_error = False
        self.username = self.request.get('username')
        self.password = self.request.get('password')
        self.verify = self.request.get('verify')
        self.email = self.request.get('email')

        params = dict(username = self.username,
                      email = self.email)

        if not valid_username(self.username):
            params['error_username'] = "That's not a valid username."
            have_error = True

        if not valid_password(self.password):
            params['error_password'] = "That wasn't a valid password."
            have_error = True
        elif self.password != self.verify:
            params['error_verify'] = "Your passwords didn't match."
            have_error = True

        if not valid_email(self.email):
            params['error_email'] = "That's not a valid email."
            have_error = True

        if have_error:
            self.render('signup-form.html', **params)
        else:
            self.done()

    def done(self):
        #make sure the user doesn't already exist
        u = User.by_name(self.username)
        if u:
            msg = 'That user already exists.'
            self.render('signup-form.html', error_username = msg)
        else:
            u = User.register(self.username, self.password, self.email)
            u.put()

            self.login(u)
            self.redirect('/welcome')

class Login(BlogHandler):
    def get(self):
        self.render('login-form.html')

    def post(self):
        username = self.request.get('username')
        password = self.request.get('password')

        u = User.login(username, password)
        if u:
            self.login(u)
            self.redirect('/welcome')
        else:
            msg = 'Invalid login'
            self.render('login-form.html', error = msg)

class Logout(BlogHandler):
    def get(self):
        self.logout()
        self.redirect('/')


class Welcome(BlogHandler):
    def get(self):
        if self.user:
            self.render('welcome.html', username=self.user.name)
        else:
            self.redirect('/signup')

class FlushHandler(BlogHandler):
    def get(self):
        memcache.flush_all()
        self.redirect('/')

reportlab.rl_config.warnOnMissingFontGlyphs = 0
        
class PDFHandler(BlogHandler):
  def get(self):
      pdfmetrics.registerFont(TTFont('AcmeSE', 'acmesa.TTF'))
      pdfmetrics.registerFont(TTFont('AcmeSEBd', 'acmesab.TTF'))
      pdfmetrics.registerFont(TTFont('AcmeSEIt', 'acmesai.TTF'))
      self.response.headers['Content-Type'] = 'application/pdf'
      self.response.headers['Content-Disposition'] = 'attachment; filename=my.pdf'
      c = canvas.Canvas(self.response.out, pagesize=A4)
      c.drawString(100, 100, "Vinhos")
      # image_data is a raw string containing a JPEG
      fn = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'images/vinhos.jpg')
      # Draw it in the bottom left, 2 inches high and 2 inches wide
      c.drawInlineImage(fn, 3*cm, 5*cm)
      c.showPage()
      text = c.beginText()
      text.setTextOrigin(1*cm, 5*cm)
      text.setFont("AcmeSE",20)
      text.textLine("Hello world!")
      text.textLine("Look ma, multiple lines!")
      c.drawText(text)
      c.showPage()
      c.save()

app = webapp2.WSGIApplication([('/?(?:.json)?', MainPage),
                               ('/([0-9]+)(?:.json)?', WinePage),
                               ('/flush', FlushHandler),
                               ('/newwine', NewWine),
                               ('/signup', Signup),
                               ('/login', Login),
                               ('/logout', Logout),
                               ('/delete/([0-9]+)', DeleteWine),
                               ('/edit/([0-9]+)', EditWine),
                               ('/pdf', PDFHandler),
                               ('/welcome', Welcome), ],
                              debug=True)
def main():
    app.run()

if __name__ == "__main__":
    main()
