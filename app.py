from flask import Flask, jsonify, request, render_template, redirect, url_for, flash
from flask_cors import CORS
from flask_caching import Cache
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.utils import secure_filename
from datetime import datetime
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)  # Enable CORS
cache = Cache(app, config={'CACHE_TYPE': 'SimpleCache', 'CACHE_DEFAULT_TIMEOUT': 300})  # Cache for 5 minutes

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///jobs.db'
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'docx'}
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Social media API credentials
TWITTER_BEARER_TOKEN = os.getenv('TWITTER_BEARER_TOKEN')
INSTAGRAM_ACCESS_TOKEN = os.getenv('INSTAGRAM_ACCESS_TOKEN')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    posted_date = db.Column(db.DateTime, default=datetime.utcnow)
    document = db.Column(db.String(255))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route("/")
def home():
    return render_template("index.html")

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
        filename = None

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
