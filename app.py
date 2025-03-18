from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_cors import CORS
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_login import UserMixin, LoginManager, login_user, login_required, logout_user, current_user
from flask_bcrypt import Bcrypt
from flask_admin import AdminIndexView
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})  # Cache for 5 minutes

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your_default_secret_key')
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB limit
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}

# Admin credentials from .env
ADMIN_USERNAME = os.getenv('ADMIN_USERNAME')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD')

login_manager = LoginManager(app)
login_manager.login_view = 'login'
bcrypt = Bcrypt(app)

# Database setup
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Social media API credentials
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Models

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = bcrypt.generate_password_hash(password).decode('utf-8')

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class AdminModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    def inaccessible_callback(self, name, **kwargs):
        flash("You must be an admin to access this page.", "danger")
        return redirect(url_for('login'))
    
class MyAdminIndexView(AdminIndexView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin
    
    def inaccessible_callback(self, name, **kwargs):
        flash("You need to log in as an admin to access this page.", "danger")
        return redirect(url_for('login'))


class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    document = db.Column(db.String(255))

class News(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    event_date = db.Column(db.DateTime, nullable=False)
    description = db.Column(db.Text)

# Flask-Admin setup
admin = Admin(app, name='Admin Panel', template_mode='bootstrap4', index_view=MyAdminIndexView())

# Admin views
admin.add_view(AdminModelView(Job, db.session))
admin.add_view(AdminModelView(News, db.session))
admin.add_view(AdminModelView(Event, db.session))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def save_uploaded_file(file):
    if file and allowed_file(file.filename):
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        return unique_filename
    return None


@app.route("/")
def home():
    upcoming_events = Event.query.filter(Event.event_date >= datetime.utcnow()).order_by(Event.event_date).limit(3).all()
    return render_template("index.html", events=upcoming_events)

# Login route with .env credentials
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = User.query.filter_by(username=username).first()
            if not user:
                user = User(username=username, is_admin=True)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()

            login_user(user)
            flash("Login successful!", "success")
            return redirect(url_for("admin.index"))
        else:
            flash("Invalid username or password", "danger")

    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route('/create_admin', methods=['POST'])
def create_admin():
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return "Username and password required!", 400

    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        return "Admin already exists!", 400

    admin_user = User(username=username, is_admin=True)
    admin_user.set_password(password)
    db.session.add(admin_user)
    db.session.commit()
    return "Admin user created!"


@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/board")
def board():
    return render_template("board.html")

@app.route("/career")
def career():
    return render_template("career.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/faq")
def faq():
    return render_template("faq.html")

@app.route("/service")
def service():
    return render_template("service.html")

@app.route("/service/single-service")
def single_service():
    return render_template("single_service.html")

@app.route("/team")
def team():
    return render_template("team.html")

@app.route("/testimonial")
def testimonial():
    return render_template("testimonial.html")


@app.route('/admin/jobs', methods=['GET', 'POST'])
def manage_jobs():
    if request.method == 'POST':
        title = request.form['title']
        location = request.form['location']
        description = request.form['description']
        file = request.files.get('document')
        filename = save_uploaded_file(file) if file else None

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)

        new_job = Job(title=title, location=location, description=description, document=filename)
        db.session.add(new_job)
        db.session.commit()
        flash('Job posted successfully!', 'success')
        return redirect(url_for('manage_jobs'))


    jobs = Job.query.all()
    return render_template('admin_jobs.html', jobs=jobs)

@app.route('/events')
def events():
    upcoming_events = Event.query.filter(Event.event_date >= datetime.utcnow()).order_by(Event.event_date).all()
    return render_template('events.html', events=upcoming_events)


@app.route('/jobs')
def jobs():
    jobs = Job.query.all()
    return render_template('jobs.html', jobs=jobs)

@app.route('/admin/jobs/delete/<int:id>', methods=['POST'])
def delete_job(id):
    job = Job.query.get_or_404(id)
    if job.document:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], job.document)
        if os.path.exists(file_path):
            os.remove(file_path)
    db.session.delete(job)
    db.session.commit()
    flash('Job deleted successfully!', 'success')
    return redirect(url_for('manage_jobs'))

@app.route('/api/social-media', methods=['GET'])
@cache.cached(timeout=300, query_string=True)
def fetch_social_media_content():
    platform = request.args.get('platform')
    page_token = request.args.get('page', '')

    platforms = {
        "twitter": fetch_twitter_posts,
        "instagram": fetch_instagram_posts,
        "youtube": fetch_youtube_videos
    }

    if platform not in platforms:
        return jsonify({"error": "Invalid platform specified"}), 400

    try:
        posts, next_token = platforms[platform](page_token)
        return jsonify({"posts": posts, "next_page_token": next_token})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": "Failed to fetch posts."}), 500

def fetch_twitter_posts(page_token):
    if not TWITTER_BEARER_TOKEN:
        raise ValueError("Twitter Bearer Token is missing.")

    username = "ten_met"
    user_url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"}

    user_response = requests.get(user_url, headers=headers)
    user_response.raise_for_status()
    user_id = user_response.json()['data']['id']

    tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
    params = {"pagination_token": page_token} if page_token else {}

    tweets_response = requests.get(tweets_url, headers=headers, params=params)
    tweets_response.raise_for_status()
    tweets = tweets_response.json()

    posts = [{"url": f"https://x.com/{username}/status/{t['id']}", "text": t['text']} for t in tweets.get('data', [])]
    return posts, tweets.get('meta', {}).get('next_token')

def fetch_instagram_posts(page_token):
    if not INSTAGRAM_ACCESS_TOKEN:
        raise ValueError("Instagram Access Token is missing.")

    url = f"https://graph.instagram.com/me/media?fields=id,caption,media_url,permalink&access_token={INSTAGRAM_ACCESS_TOKEN}"
    response = requests.get(url)
    response.raise_for_status()
    posts = response.json().get('data', [])

    formatted_posts = [{"url": p["permalink"], "image": p["media_url"], "caption": p.get("caption", "")} for p in posts]
    return formatted_posts, None

def fetch_youtube_videos(page_token):
    if not YOUTUBE_API_KEY:
        raise ValueError("YouTube API Key is missing.")

    url = f"https://www.googleapis.com/youtube/v3/search?key={YOUTUBE_API_KEY}&channelId=UCg3xPZvGFCf9zW6fFNb-MNA&part=snippet&type=video&order=date&maxResults=5"
    if page_token:
        url += f"&pageToken={page_token}"

    response = requests.get(url)
    response.raise_for_status()
    videos = response.json()

    posts = [{"url": f"https://www.youtube.com/watch?v={v['id']['videoId']}", "title": v["snippet"]["title"], "thumbnail": v["snippet"]["thumbnails"]["high"]["url"]} for v in videos.get('items', [])]
    return posts, videos.get('nextPageToken')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
