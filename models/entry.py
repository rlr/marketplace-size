from google.appengine.ext import db


class Entry(db.Model):
    time = db.DateTimeProperty(required=True)
    size = db.IntegerProperty(required=True)
    domain = db.StringProperty(required=True)
    with_assets = db.IntegerProperty(required=True)
    size_css = db.IntegerProperty(required=False)
    size_js = db.IntegerProperty(required=False)
    commit = db.StringProperty(required=False)
