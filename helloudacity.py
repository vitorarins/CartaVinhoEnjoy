import webapp2
import os
import jinja2
import hashlib
import hmac
import urllib2
import urllib
from xml.dom import minidom
from google.appengine.ext import db

template_dir = os.path.join(os.path.dirname(__file__),'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir),autoescape = True)

IP_URL = "http://api.hostip.info/?ip="
def get_coords(ip):
    url = IP_URL + ip
    content = None
    try:
        content = urllib2.urlopen(url).read()
    except URLError:
        return
    if content:
        d = minidom.parseString(content)
        coords = d.getElementsByTagName('gml:coordinates')
        if coords and coords[0].childNodes[0].nodeValue:
            x,y = coords[0].childNodes[0].nodeValue.split(',')
            return db.GeoPt(y,x)

GMAPS_URL = "http://maps.googleapis.com/maps/api/staticmap?size=380x263&sensor=false"
def gmaps_image(points):
    result = GMAPS_URL
    for p in points:
        result += '&markers=' + str(p.lat)+','+str(p.lon)
    return result

class Art(db.Model):
    title = db.StringProperty(required = True)
    art = db.TextProperty(required = True)
    created = db.DateTimeProperty(auto_now_add = True)
    coords = db.GeoPtProperty()

class Handler(webapp2.RequestHandler):
    def write(self, *a, **kw):
        self.response.out.write(*a,**kw)

    def render_str(self, template, **params):
        t = jinja_env.get_template(template)
        return t.render(params)

    def render(self,template, **kw):
        self.write(self.render_str(template, **kw))
    
class MainPage(Handler):
    def render_front(self, error = '', title='',art=''):
        arts = db.GqlQuery("SELECT * FROM Art ORDER BY created DESC LIMIT 10")
        arts = list(arts)
        points = filter(None, (a.coords for a in arts))
        img_url = None
        if points:
            img_url = gmaps_image(points)
        self.render('ascii.html',title=title,art=art,error=error,arts=arts,img_url=img_url)
    
    def get(self):
        return self.render_front()

    def post(self):
        title = self.request.get('title')
        art = self.request.get('art')
        if title and art:
            p = Art(title = title,art=art)
            coords = get_coords(self.request.remote_addr)
            if coords:
                p.coords = coords
            p.put()
            self.redirect('/')
        else:
            error = "We need both a title and some artwork!"
            self.render_front(error=error,title=title,art=art)
    
app = webapp2.WSGIApplication([('/', MainPage)], debug=True)

def main():
    app.run()

if __name__ == "__main__":
    main()
