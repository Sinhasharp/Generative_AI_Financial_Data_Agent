import os
import json
from flask import Flask, request, render_template_string, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
import pymongo
from bson import json_util


from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user

from ingest_processor import process_file

print("--- Checkpoint 1: All imports successful. ---")

try:
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'a-very-secret-random-string-12345'
    UPLOAD_FOLDER = 'uploads'
    ALLOWED_EXTENSIONS = {'txt', 'pdf'}
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    print("--- Checkpoint 2: Flask App configured. ---")
except Exception as e:
    print(f"--- ERROR AT CHECKPOINT 2: {e} ---")
    exit()

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    print("--- Checkpoint 3: 'uploads' folder checked/created. ---")

try:
    login_manager = LoginManager()
    print("--- Checkpoint 4: LoginManager created. ---")
    login_manager.init_app(app)
    print("--- Checkpoint 5: LoginManager initialized with app. ---")
    login_manager.login_view = 'login'
    login_manager.login_message = 'You must be logged in to view this page.'
    login_manager.login_message_category = 'error'
    print("--- Checkpoint 6: LoginManager configured. ---")
except Exception as e:
    print(f"--- ERROR AT LOGIN SETUP (CP 4-6): {e} ---")
    exit()

class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

users = {
    1: User(1, "admin", "password123")
}
print("--- Checkpoint 7: User class and database created. ---")

@login_manager.user_loader
def load_user(user_id):
    return users.get(int(user_id))

HTML_UPLOAD_TEMPLATE = """
<!doctype html>
<title>Upload Bank Statement</title>
<style>
  body { font-family: sans-serif; padding: 20px; background-color: #f4f4f4; }
  h1 { color: #333; }
  .container { max-width: 800px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
  .flashes { list-style: none; padding: 0; margin: 0 0 20px 0; }
  .flashes li { padding: 10px; border-radius: 4px; }
  .flashes .error { background: #ffe0e0; border: 1px solid #f99; color: #c00; }
  .flashes .success { background: #e0ffe0; border: 1px solid #9f9; color: #060; }
  .navbar { text-align: right; margin-bottom: 20px; }
  .navbar a { text-decoration: none; color: #007bff; margin-left: 15px; }
  pre { background-color: #eee; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }
</style>

<div class="container">
  <div class="navbar">
    {% if current_user.is_authenticated %}
      Logged in as: <strong>{{ current_user.username }}</strong>
      <a href="{{ url_for('review') }}">Review Data</a>
      <a href="{{ url_for('logout') }}">Logout</a>
    {% else %}
      <a href="{{ url_for('login') }}">Login to Review Data</a>
    {% endif %}
  </div>

  <h1>Upload a New Bank Statement (.txt or .pdf)</h1>

  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <ul class=flashes>
      {% for category, message in messages %}
        <li class="{{ category }}">{{ message }}</li>
      {% endfor %}
      </ul>
    {% endif %}
  {% endwith %}

  <form method=post enctype=multipart/form-data>
    <input type=file name=file>
    <input type=submit value=Upload>
  </form>
</div>
"""

HTML_LOGIN_TEMPLATE = """
<!doctype html>
<title>Login</title>
<style>
  body { font-family: sans-serif; padding: 20px; background-color: #f4f4f4; }
  h1 { color: #333; }
  .container { max-width: 400px; margin: 50px auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
  .flashes { list-style: none; padding: 0; margin: 0 0 20px 0; }
  .flashes li { padding: 10px; border-radius: 4px; }
  .flashes .error { background: #ffe0e0; border: 1px solid #f99; color: #c00; }
  form { display: flex; flex-direction: column; }
  form div { margin-bottom: 15px; }
  form label { margin-bottom: 5px; font-weight: bold; }
  form input[type="text"], form input[type="password"] { padding: 8px; border: 1px solid #ccc; border-radius: 4px; }
  form input[type="submit"] { background: #007bff; color: white; padding: 10px; border: none; border-radius: 4px; cursor: pointer; }
  form input[type="submit"]:hover { background: #0056b3; }
  .navbar { text-align: right; }
  .navbar a { text-decoration: none; color: #007bff; }
</style>

<div class="container">
  <div class="navbar">
    <a href="{{ url_for('home') }}">Back to Upload</a>
  </div>

  <h1>Login</h1>
  
  {% with messages = get_flashed_messages(with_categories=true) %}
    {% if messages %}
      <ul class=flashes>
      {% for category, message in messages %}
        <li class="{{ category }}">{{ message }}</li>
      {% endfor %}
      </ul>
    {% endif %}
  {% endwith %}

  <form method=post>
    <div>
      <label for="username">Username:</label>
      <input type="text" id="username" name="username">
    </div>
    <div>
      <label for="password">Password:</label>
      <input type="password" id="password" name="password">
    </div>
    <input type="submit" value="Login">
  </form>
</div>
"""

HTML_REVIEW_TEMPLATE = """
<!doctype html>
<title>Review Ingested Data</title>
<style>
  body { font-family: sans-serif; padding: 20px; background-color: #f4f4f4; }
  h1 { color: #333; }
  h2 { color: #555; border-bottom: 2px solid #007bff; padding-bottom: 5px; }
  .container { max-width: 1200px; margin: 0 auto; background: #fff; padding: 20px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
  .navbar { text-align: right; margin-bottom: 20px; }
  .navbar a { text-decoration: none; color: #007bff; margin-left: 15px; }
  pre { background-color: #eee; padding: 10px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; border: 1px solid #ccc; }
  .bank-section { margin-bottom: 30px; }
</style>

<div class="container">
  <div class="navbar">
    Logged in as: <strong>{{ current_user.username }}</strong>
    <a href="{{ url_for('home') }}">Back to Upload</a>
    <a href="{{ url_for('logout') }}">Logout</a>
  </div>

  <h1>Review Ingested Data</h1>
  
  {% if all_bank_data %}
    {% for bank in all_bank_data %}
      <div class="bank-section">
        <h2>Bank: {{ bank.name }}</h2>
        {% if bank.documents %}
          {% for doc in bank.documents %}
            <pre>{{ doc }}</pre>
          {% endfor %}
        {% else %}
          <p>No documents found for this bank.</p>
        {% endif %}
      </div>
    {% endfor %}
  {% else %}
    <p>No data found in the 'bank_data' database.</p>
  {% endif %}
  
</div>
"""
print("--- Checkpoint 8: HTML templates defined. ---")

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part in request', 'error')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No selected file', 'error')
            return redirect(request.url)
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            try:
                file.save(file_path)
                print(f"File saved successfully: {file_path}")
                
                print("Calling ingest_processor...")
                success = process_file(file_path)
                
                if success:
                    flash(f"File '{filename}' processed successfully!", 'success')
                else:
                    flash(f"Error processing file '{filename}'. Check terminal.", 'error')

            except Exception as e:
                flash(f"An unexpected error occurred: {e}", 'error')
            
            return redirect(request.url)
            
        else:
            flash('Invalid file type. Only .txt and .pdf allowed.', 'error')
            return redirect(request.url)

    return render_template_string(HTML_UPLOAD_TEMPLATE)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('review')) 

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = users.get(1) # Get user 1
        if user and user.username == username and user.password == password:
            login_user(user)
            flash('Logged in successfully!', 'success')
            return redirect(url_for('review'))
        else:
            flash('Invalid username or password.', 'error')

    return render_template_string(HTML_LOGIN_TEMPLATE)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('home'))


@app.route('/review')
@login_required
def review():
    all_bank_data = []
    try:
        db_client = pymongo.MongoClient("mongodb://localhost:27018/", serverSelectionTimeoutMS=5000)
        db_client.server_info()
        db = db_client["bank_data"]
        
        collection_names = db.list_collection_names()
        
        if "sheets" in collection_names:
            collection_names.remove("sheets") 
            
        for bank_name in collection_names:
            bank = {"name": bank_name, "documents": []}
            collection = db[bank_name]
            for doc in collection.find():
                bank["documents"].append(json.dumps(doc, indent=2, default=json_util.default))
            all_bank_data.append(bank)
            
        db_client.close()
        
    except pymongo.errors.ServerSelectionTimeoutError:
        flash("Error: Could not connect to MongoDB. Is it running?", 'error')
    except Exception as e:
        flash(f"An error occurred: {e}", 'error')

    return render_template_string(HTML_REVIEW_TEMPLATE, all_bank_data=all_bank_data)

print("--- Checkpoint 9: All routes defined. ---")

if __name__ == '__main__':
    print("--- Checkpoint 10: Script is being run directly. ---")
    try:
        app.run(debug=True, port=5000)
        print("--- Server is running. ---") 
    except Exception as e:
        print(f"--- ERROR running app: {e} ---")
        
else:
    print("--- ERROR: Script is being imported, not run. ---")