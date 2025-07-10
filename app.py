from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')

# データベース設定 - SQLiteのみ使用
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///season_calendar.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Flask-Login設定
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'このページにアクセスするにはログインが必要です。'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# データベースモデル
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    activities = db.relationship('SeasonActivity', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class SeasonActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    month = db.Column(db.Integer, nullable=False)
    season = db.Column(db.String(20), nullable=False)
    activity_type = db.Column(db.String(50), nullable=False)  # 一人、友達、家族、お年寄り
    category = db.Column(db.String(50), nullable=False)  # 外出、家、食事
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# データベース初期化関数
def init_db():
    """データベースとテーブルを初期化"""
    with app.app_context():
        db.create_all()
        print("データベーステーブルが作成されました")

# アプリケーション起動時にデータベースを初期化
init_db()

# 季節データ
SEASON_DATA = {
    1: {"name": "冬", "color": "#87CEEB", "activities": []},
    2: {"name": "冬", "color": "#87CEEB", "activities": []},
    3: {"name": "春", "color": "#90EE90", "activities": []},
    4: {"name": "春", "color": "#90EE90", "activities": []},
    5: {"name": "春", "color": "#90EE90", "activities": []},
    6: {"name": "夏", "color": "#FFB6C1", "activities": []},
    7: {"name": "夏", "color": "#FFB6C1", "activities": []},
    8: {"name": "夏", "color": "#FFB6C1", "activities": []},
    9: {"name": "秋", "color": "#DDA0DD", "activities": []},
    10: {"name": "秋", "color": "#DDA0DD", "activities": []},
    11: {"name": "秋", "color": "#DDA0DD", "activities": []},
    12: {"name": "冬", "color": "#87CEEB", "activities": []}
}

@app.route('/')
@login_required
def index():
    """ホームページ - 月別カレンダー表示"""
    current_month = datetime.now().month
    return render_template('index.html', 
                         season_data=SEASON_DATA, 
                         current_month=current_month)

@app.route('/login', methods=['GET', 'POST'])
def login():
    """ログインページ"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user)
            flash('ログインしました！', 'success')
            return redirect(url_for('index'))
        else:
            flash('ユーザー名またはパスワードが正しくありません。', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """ユーザー登録ページ"""
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # バリデーション
        if User.query.filter_by(username=username).first():
            flash('このユーザー名は既に使用されています。', 'error')
            return render_template('register.html')
        
        if User.query.filter_by(email=email).first():
            flash('このメールアドレスは既に使用されています。', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('パスワードが一致しません。', 'error')
            return render_template('register.html')
        
        # ユーザー作成
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('アカウントが作成されました！ログインしてください。', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    """ログアウト"""
    logout_user()
    flash('ログアウトしました。', 'info')
    return redirect(url_for('login'))

@app.route('/month/<int:month>')
@login_required
def month_detail(month):
    """月別詳細ページ"""
    if month < 1 or month > 12:
        return redirect(url_for('index'))
    
    # 現在のユーザーのアクティビティのみ取得
    activities = SeasonActivity.query.filter_by(month=month, user_id=current_user.id).all()
    season_info = SEASON_DATA[month]
    
    # アクティビティをカテゴリ別に整理
    categorized_activities = {
        '一人': [],
        '友達': [],
        '家族': [],
        'お年寄り': []
    }
    
    for activity in activities:
        if activity.activity_type in categorized_activities:
            categorized_activities[activity.activity_type].append(activity)
    
    return render_template('month_detail.html', 
                         month=month, 
                         season_info=season_info,
                         activities=categorized_activities)

@app.route('/add_activity', methods=['GET', 'POST'])
@login_required
def add_activity():
    """アクティビティ追加"""
    if request.method == 'POST':
        month = int(request.form['month'])
        activity_type = request.form['activity_type']
        category = request.form['category']
        title = request.form['title']
        description = request.form['description']
        
        new_activity = SeasonActivity(
            user_id=current_user.id,
            month=month,
            season=SEASON_DATA[month]['name'],
            activity_type=activity_type,
            category=category,
            title=title,
            description=description
        )
        
        db.session.add(new_activity)
        db.session.commit()
        
        flash('アイデアが追加されました！', 'success')
        return redirect(url_for('month_detail', month=month))
    
    return render_template('add_activity.html', season_data=SEASON_DATA)

@app.route('/edit_activity/<int:activity_id>', methods=['GET', 'POST'])
@login_required
def edit_activity(activity_id):
    """アクティビティ編集"""
    # 自分のアクティビティのみ編集可能
    activity = SeasonActivity.query.filter_by(id=activity_id, user_id=current_user.id).first_or_404()
    
    if request.method == 'POST':
        activity.month = int(request.form['month'])
        activity.activity_type = request.form['activity_type']
        activity.category = request.form['category']
        activity.title = request.form['title']
        activity.description = request.form['description']
        activity.season = SEASON_DATA[activity.month]['name']
        
        db.session.commit()
        
        flash('アイデアが更新されました！', 'success')
        return redirect(url_for('month_detail', month=activity.month))
    
    return render_template('edit_activity.html', 
                         activity=activity, 
                         season_data=SEASON_DATA)

@app.route('/delete_activity/<int:activity_id>')
@login_required
def delete_activity(activity_id):
    """アクティビティ削除"""
    # 自分のアクティビティのみ削除可能
    activity = SeasonActivity.query.filter_by(id=activity_id, user_id=current_user.id).first_or_404()
    month = activity.month
    db.session.delete(activity)
    db.session.commit()
    flash('アイデアが削除されました', 'info')
    return redirect(url_for('month_detail', month=month))

if __name__ == '__main__':
    app.run(debug=True) 