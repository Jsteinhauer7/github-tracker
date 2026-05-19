from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone
import os
import requests

app = Flask(__name__)
database_url = os.environ.get('DATABASE_URL', 'sqlite:///' + os.path.join(os.path.dirname(os.path.abspath(__file__)), 'github.db'))
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Repo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    github_id = db.Column(db.Integer, unique=True, nullable=False)
    name = db.Column(db.String(200))
    full_name = db.Column(db.String(200))
    description = db.Column(db.Text, default='')
    url = db.Column(db.String(500))
    stars = db.Column(db.Integer, default=0)
    forks = db.Column(db.Integer, default=0)
    language = db.Column(db.String(100), default='Unknown')
    repo_created_at = db.Column(db.String(50))
    first_seen = db.Column(db.DateTime, default=datetime.utcnow)
    last_seen = db.Column(db.DateTime, default=datetime.utcnow)

class FetchLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    repos_added = db.Column(db.Integer, default=0)
    repos_updated = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='success')
    message = db.Column(db.String(200), default='')

with app.app_context():
    db.create_all()

def _do_fetch():
    from datetime import timedelta
    headers = {'Accept': 'application/vnd.github.v3+json'}
    github_token = os.environ.get('GITHUB_TOKEN')
    if github_token:
        headers['Authorization'] = f'token {github_token}'

    since = (datetime.utcnow() - timedelta(days=30)).strftime('%Y-%m-%d')
    api_url = f'https://api.github.com/search/repositories?q=created:>{since}+stars:>10&sort=stars&order=desc&per_page=50'

    try:
        resp = requests.get(api_url, headers=headers, timeout=15)
        resp.raise_for_status()
        items = resp.json().get('items', [])
    except Exception as e:
        db.session.add(FetchLog(status='error', message=str(e)[:200]))
        db.session.commit()
        return

    added = updated = 0
    for item in items:
        existing = Repo.query.filter_by(github_id=item['id']).first()
        if existing:
            existing.stars = item['stargazers_count']
            existing.forks = item['forks_count']
            existing.last_seen = datetime.utcnow()
            updated += 1
        else:
            db.session.add(Repo(
                github_id=item['id'],
                name=item['name'],
                full_name=item['full_name'],
                description=item.get('description') or '',
                url=item['html_url'],
                stars=item['stargazers_count'],
                forks=item['forks_count'],
                language=item.get('language') or 'Unknown',
                repo_created_at=item['created_at'][:10],
            ))
            added += 1

    db.session.add(FetchLog(repos_added=added, repos_updated=updated))
    db.session.commit()

def scheduled_fetch():
    with app.app_context():
        _do_fetch()

# Background scheduler — runs every hour automatically
scheduler = BackgroundScheduler()
scheduler.add_job(scheduled_fetch, 'interval', hours=1, id='fetch_job')
scheduler.start()

@app.route('/')
def index():
    language = request.args.get('language', '')
    search = request.args.get('search', '')

    query = Repo.query
    if language:
        query = query.filter_by(language=language)
    if search:
        query = query.filter(
            db.or_(
                Repo.name.ilike(f'%{search}%'),
                Repo.description.ilike(f'%{search}%')
            )
        )
    repos = query.order_by(Repo.stars.desc()).all()

    total = Repo.query.count()

    # Language breakdown for chart
    lang_counts = {}
    for r in Repo.query.all():
        lang = r.language or 'Unknown'
        lang_counts[lang] = lang_counts.get(lang, 0) + 1
    top_languages = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:10]

    # Top repos for bar chart
    top_repos = Repo.query.order_by(Repo.stars.desc()).limit(10).all()

    # Last fetch log
    last_fetch = FetchLog.query.order_by(FetchLog.timestamp.desc()).first()

    # All languages for filter dropdown
    languages = sorted(set(r.language for r in Repo.query.all() if r.language))

    return render_template('index.html',
        repos=repos, total=total,
        top_languages=top_languages,
        top_repos=top_repos,
        last_fetch=last_fetch,
        languages=languages,
        selected_language=language,
        search=search
    )

@app.route('/fetch', methods=['POST'])
def manual_fetch():
    _do_fetch()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)
