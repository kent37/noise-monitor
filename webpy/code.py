# Simple web server to display logged noise measurements directly from the logging RPi
# Requires web.py, install with `sudo pip install web.py`

# Run with `nohup python code.py > /dev/null &`
# This will open a web server on port 8080.
# http://<rpi address>:8080 will list available dates
# Clicking on a date will show noise measurements for that date.

# Be patient, it can take a few seconds to display a day.

import os

import web
import config
import model

urls = (
    '/', 'index',
    '/data/(.*)', 'data',
    '/show/(.*)', 'show'
)

render = web.template.render('templates')

class index:
    def GET(self):
    	""" GET / shows all available dates """
        return render.index(model.dates())

class show:
	def GET(self, date):
		""" GET /show/<date> returns the display page for the date """
		return render.show_date(date)

class data:
	def GET(self, date):
		""" GET /data/<date> returns all the data for date in CSV format """
		web.header('Content-type','text/csv')
		return ''.join(model.date_data(date))

if __name__ == "__main__":
	# Start the server
    app = web.application(urls, globals())
    app.internalerror = web.debugerror
    app.run()