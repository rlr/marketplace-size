from google.appengine.ext import db


class Entry(db.Model):
    time = db.DateTimeProperty(required=True)
    size = db.IntegerProperty(required=True)
    domain = db.StringProperty(required=True)
    with_assets = db.IntegerProperty(required=True)
