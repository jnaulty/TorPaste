#!bin/python
# -*- coding: utf-8 -*-

from flask import *
from hashlib import sha256
from datetime import datetime
import os, time, json
from os import getenv
app = Flask(__name__)

VERSION = "0.5"
COMPATIBLE_BACKENDS = ["filesystem"]

@app.route('/')
def index():
    return render_template(
		"index.html",
		title = WEBSITE_TITLE,
		version = VERSION,
		page = "main"
	)

@app.route("/new", methods=["GET", "POST"])
def newpaste():
	if(request.method == "GET"):
		return render_template(
			"index.html",
			title = WEBSITE_TITLE,
			version = VERSION,
			page = "new"
		)
	else:
		if(request.form['content']):
			try:
				PasteID = str(sha256(request.form['content'].encode('utf-8')).hexdigest())
			except:
				return render_template(
					"index.html",
					title = WEBSITE_TITLE,
					version = VERSION,
					page = "new",
					error = "An issue occured while handling the paste. Please try again later. If the problem persists, try notifying a system administrator."
				)

			if ( len(request.form['content'].encode('utf-8')) > MAX_PASTE_SIZE ):
				return render_template(
					"index.html",
					title = WEBSITE_TITLE,
					version = VERSION,
					page = "new",
					error = "The paste sent is too large. This TorPaste instance has a maximum allowed paste size of " + formatSize(MAX_PASTE_SIZE) + "."
				)

			try:
				b.newPaste(PasteID, request.form['content'])
			except b.e.ErrorException as errmsg:
				return render_template(
					"index.html",
					title = WEBSITE_TITLE,
					version = VERSION,
					page = "new",
					error = errmsg
				)

			try:
				b.updatePasteMetadata(
					PasteID,
					{
						"date": unicode(int(time.time()))
					}
				)
			except b.e.ErrorException as errmsg:
				return render_template(
					"index.html",
					title = WEBSITE_TITLE,
					version = VERSION,
					page = "new",
					error = errmsg
				)

			return redirect("/view/" + PasteID)
		else:
			return Response(
				render_template(
					"index.html",
					title = WEBSITE_TITLE,
					version = VERSION,
					error = "Please enter some text to include in the paste.",
					page = "new"
				),
				400
			)

@app.route("/view/<pasteid>")
def viewpaste(pasteid):
	if(not pasteid.isalnum()):
		return Response(
			render_template(
				"index.html",
				title = WEBSITE_TITLE,
				version = VERSION,
				error = "Invalid Paste ID. Please check the link you used or use Pastes button above.",
				page = "new"
			),
			400
		)
	if(len(pasteid) < 6):
		return Response(
			render_template(
				"index.html",
				title = WEBSITE_TITLE,
				version = VERSION,
				error = "Paste ID too short. Usually Paste IDs are longer than 6 characters. Please make sure the link you clicked is correct or use the Pastes button above.",
				page = "new"
			),
			400
		)
	if ( not b.doesPasteExist(pasteid) ):
		return Response(
			render_template(
				"index.html",
				title = WEBSITE_TITLE,
				version = VERSION,
				error = "A paste with this ID could not be found. Sorry.",
				page = "new"
			),
			404
		)

	try:
		PasteContent = b.getPasteContents(pasteid)
	except b.e.ErrorException as errmsg:
		return render_template(
			"index.html",
			title = WEBSITE_TITLE,
			version = VERSION,
			error = errmsg,
			page = "new"
		)

	try:
		PasteDate = b.getPasteMetadataValue(pasteid, "date")
	except b.e.ErrorException as errmsg:
		return render_template(
			"index.html",
			title = WEBSITE_TITLE,
			version = VERSION,
			error = errmsg,
			page = "new"
		)
	except b.e.WarningException as errmsg:
		return render_template(
			"index.html",
			title = WEBSITE_TITLE,
			version = VERSION,
			warning = errmsg,
			page = "new"
		)

	PasteDate = datetime.fromtimestamp(int(PasteDate) + time.altzone + 3600).strftime("%H:%M:%S %d/%m/%Y")
	PasteSize = formatSize(len(PasteContent.encode('utf-8')))
	return render_template(
		"view.html",
		content = PasteContent,
		date = PasteDate,
		size = PasteSize,
		pid = pasteid,
		title = WEBSITE_TITLE,
		version = VERSION,
		page = "view"
	)

@app.route("/raw/<pasteid>")
def rawpaste(pasteid):
	if(not pasteid.isalnum()):
		return "No such paste", 404
	if(len(pasteid) < 6):
		return "No such paste", 404
	if ( not b.doesPasteExist(pasteid) ):
		return "No such paste", 404
	try:
		PasteContent = b.getPasteContents(pasteid)
	except b.e.ErrorException as errmsg:
		return Response(
			errmsg,
			500
		)
	return Response(
		PasteContent,
		mimetype = "text/plain"
	)

@app.route("/list")
def list():
	try:
		PasteList = b.getAllPasteIDs()
	except b.e.ErrorException as errmsg:
		return render_template(
			"index.html",
			title = WEBSITE_TITLE,
			version = VERSION,
			page = "new",
			error = errmsg
		)

	if ( PasteList[0] == 'none' ):
		return render_template(
			"list.html",
			pastes = ['none'],
			title = WEBSITE_TITLE,
			version = VERSION,
			page = "list"
		)
	return render_template(
		"list.html",
		pastes = PasteList,
		title = WEBSITE_TITLE,
		version = VERSION,
		page = "list"
	)

@app.route("/about")
def aboutTorPaste():
	return render_template(
		"about.html",
		title = WEBSITE_TITLE,
		version = VERSION,
		page = "about"
	)

# API Routes
@app.route('/api/v1')
def apiMain():
	return Response('TorPaste API ' + VERSION, mimetype='text/plain')

@app.route('/api/v1/status')
def apiStatus():
	return Response(
		json.dumps(
			{
				"success": "true",
				"error": "none",
				"errorid": "none",
				"version": VERSION,
				"status": "enabled",
				"config": {
					"max_paste_size_bytes": MAX_PASTE_SIZE,
					"title": WEBSITE_TITLE
				}
			}
		),
		mimetype = "application/json"
	)

@app.route('/api/v1/paste/new', methods=["POST"])
def apiNewPaste():
	try:
		_ = request.form['content']
	except:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "No paste content set",
					"errorid": "E_EMPTY_PASTE",
					"paste_id": "none",
					"paste_link": "none"
				}
			),
			mimetype = "application/json"
		)

	try:
		PasteID = str(sha256(request.form['content'].encode('utf-8')).hexdigest())
	except:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "An error occured while handling the paste.",
					"errorid": "E_PASTE_HANDLING_ERROR",
					"paste_id": "none",
					"paste_link": "none"
				}
			),
			mimetype = "application/json"
		)

	if ( len(request.form['content'].encode('utf-8')) > MAX_PASTE_SIZE ):
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "The paste sent is too large.",
					"errorid": "E_PASTE_TOO_LARGE",
					"paste_id": "none",
					"paste_link": "none"
				}
			),
			mimetype = "application/json"
		)

	try:
		b.newPaste(PasteID, request.form['content'])
	except b.e.ErrorException as errmsg:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": errmsg,
					"errorid": "E_SERVER_ERROR",
					"paste_id": "none",
					"paste_link": "none"
				}
			),
			mimetype = "application/json"
		)

	try:
		b.updatePasteMetadata(
			PasteID,
			{
				"date": unicode(int(time.time()))
			}
		)
	except b.e.ErrorException as errmsg:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": errmsg,
					"errorid": "E_SERVER_ERROR",
					"paste_id": "none",
					"paste_link": "none"
				}
			),
			mimetype = "application/json"
		)

	return Response(
		json.dumps(
			{
				"success": "true",
				"error": "none",
				"errorid": "none",
				"paste_id": PasteID,
				"paste_link": "/".join(request.url_root.split("/")[0:3]) + "/view/" + PasteID
			}
		),
		mimetype = "application/json"
	)

@app.route("/api/v1/paste/get/<pasteid>")
def apiGetPaste(pasteid):
	if ( not pasteid.isalnum() ):
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "The Paste ID supplied is invalid.",
					"errorid": "E_INVALID_PASTE_ID",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)

	if ( len(pasteid) < 6 ):
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "The Paste ID supplied is invalid.",
					"errorid": "E_INVALID_PASTE_ID",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)

	if ( not b.doesPasteExist(pasteid) ):
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": "There is no paste with this Paste ID.",
					"errorid": "E_NO_PASTE",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)

	try:
		PasteContent = b.getPasteContents(pasteid)
	except b.e.ErrorException as errmsg:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": errmsg,
					"errorid": "E_SERVER_ERROR",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)

	try:
		PasteDate = b.getPasteMetadataValue(pasteid, "date")
	except b.e.ErrorException as errmsg:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": errmsg,
					"errorid": "E_SERVER_ERROR",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)
	except b.e.WarningException as errmsg:
		return Response(
			json.dumps(
				{
					"success": "false",
					"error": errmsg,
					"errorid": "E_SERVER_ERROR",
					"paste": {
						"content": "none",
						"date_unix": 0,
						"date_formatted": "none",
						"size_bytes": 0,
						"size_formatted": "none"
					}
				}
			),
			mimetype = "application/json"
		)

	PD = datetime.fromtimestamp(int(PasteDate) + time.altzone + 3600).strftime("%H:%M:%S %d/%m/%Y")
	PasteSize = len(PasteContent.encode('utf-8'))
	PS = formatSize(PasteSize)

	return Response(
		json.dumps(
			{
				"success": "true",
				"error": "none",
				"errorid": "none",
				"paste": {
					"content": PasteContent,
					"date_unix": int(PasteDate),
					"date_formatted": PD,
					"size_bytes": PasteSize,
					"size_formatted": PS
				}
			}
		),
		mimetype = "application/json"
	)

# Functions
def formatSize(size):
	scales = ["bytes", "kB", "MB", "GB", "TB", "EB"]
	count = 0
	while(1==1):
		if(size > 1024.0):
			size = size / 1024.0
			count = count + 1
		else:
			break
	return str(round(size,1)) + " " + scales[count]

# Required Initialization Code
## Handle Environment Variables (for configuration)
### Web App <title>
WEBSITE_TITLE = getenv("TP_WEBSITE_TITLE")
try:
	WEBSITE_TITLE += ""
except:
	WEBSITE_TITLE  = "Tor Paste"

### Backend Used
BACKEND = getenv("TP_BACKEND")
try:
	BACKEND += ""
except:
	BACKEND  = "filesystem"
if ( BACKEND in COMPATIBLE_BACKENDS ):
	if ( BACKEND == "filesystem" ):
		import backends.filesystem as b
else:
	print("Configured backend (" + BACKEND + ") is not compatible with current version.")
	exit(1)

### Maximum Paste Size
MAX_PASTE_SIZE = getenv("TP_PASTE_MAX_SIZE")
try:
	MAX_PASTE_SIZE += ""
except:
	MAX_PASTE_SIZE  = "1 P"

if ( MAX_PASTE_SIZE[0] == "0" ):
	MAX_PASTE_SIZE = "1 P"

MAX_PASTE_SIZE = MAX_PASTE_SIZE.split(" ")

try:
	AMOUNT = int(MAX_PASTE_SIZE[0])
	UNIT = MAX_PASTE_SIZE[1]
except:
	print("Invalid TP_PASTE_MAX_SIZE: " + " ".join(MAX_PASTE_SIZE))
	exit(1)

orders = ["B", "k", "M", "G", "T", "P"]

if ( not UNIT in orders ):
	print("Invalid Unit Size: " + UNIT)

try:
	MAX_PASTE_SIZE = AMOUNT * 1024**orders.index(UNIT)
except:
	print("An unknown error occured while determining max paste size.")
	exit(1)

## Initialize Backend
try:
	b.initializeBackend()
except:
	print("Failed to initialize backend")
	exit(1)

if __name__ == '__main__':
    app.run(host="0.0.0.0")
