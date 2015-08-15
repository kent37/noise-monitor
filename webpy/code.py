import os

import web
import config
from view import dates, date_data

urls = (
    '/', 'index',
    '/data/(.*)', 'data',
    '/show/(.*)', 'show'
)

render = web.template.render('templates')

class index:
    def GET(self):
        return render.index(view.dates(config.base_path))

class show:
	def GET(self, date):
		return render.show_date(date)

class data:
	def GET(self, date):
		""" Get all the data for date."""
		return '\r\n'.join(view.date_data(date))

if __name__ == "__main__":
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()