from flask import Flask, request, jsonify, session, render_template
from flask_session import Session
from data_analysis import *
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import secrets

UPLOAD_FOLDER = '/Users/aaronma/Desktop/Netflix Wrapped/flask_server/uploads/'
ALLOWED_EXTENSIONS = {'csv'}

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}}, supports_credentials=True)
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True # set to True in production
app.config['SESSION_COOKIE_PATH'] = '/'  
Session(app)

app.secret_key = secrets.token_hex(16)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/upload", methods = ["POST"])
def upload_file():
    # check if the post request has the file part
    if 'csv_data' not in request.files:
        return jsonify({"error": "No csv_data file"}), 400
    file = request.files['csv_data']
    # If the user does not select a file, the browser submits an
    # empty file without a filename.
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        session['filename'] = filename
        # print(f"Session ID: {session.sid}")
        # print(f"Session data set: {session.get('filename')}")

        return jsonify(getUserYearsData(filename)), 200
    
    return jsonify({"error": "Invalid file type"}), 400
    
@app.route("/statistics", methods = ["POST"])
def upload_charts():
    filename = session.get('filename')
    # print(f"Session ID: {session.sid}")
    # print(f"Session data retrieved: {filename}")

    # if filename == '':
    #     return jsonify({"error": "filename not set"}), 400
    
    data = request.json
    user = data.get('user')
    year = data.get('year')

    return jsonify(getJsonGraphData(filename, user, year))

if __name__ == "__main__":
    app.run(debug = True)