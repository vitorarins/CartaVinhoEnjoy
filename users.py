import webapp2
from google.appengine.ext import db
import os

class MainPage(webapp2.RequestHandler):
    def get(self):
        users = db.GqlQuery("SELECT * FROM User")
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello world!')
        for u in users:
            self.response.out.write(u.get('name'))

app = webapp2.WSGIApplication([('/users',MainPage)], debug=True)

def main():
    app.run()

if __name__ == "__main__":
    main()

