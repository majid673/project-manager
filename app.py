import os
from flask import Flask, request, render_template, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_restful import Api, Resource
from datetime import datetime, date
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash

# Load environment variables
load_dotenv()

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.path.dirname(__file__), 'instance', 'database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'
api = Api(app)

# Database models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Viewer')
    projects = db.relationship('Project', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(50), nullable=True, default='General')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    tasks = db.relationship('Task', backref='project', lazy=True)

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    deadline = db.Column(db.Date, nullable=False)
    priority = db.Column(db.String(20), nullable=False, default='Medium')
    status = db.Column(db.String(20), nullable=False, default='Pending')
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)

class ProjectRole(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Viewer')
    user = db.relationship('User', backref='project_roles')
    project = db.relationship('Project', backref='project_roles')

# User login management
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))  # Updated from User.query.get

# Email sending function
def send_reminder(task, old_task=None, email_to="majid_0280@yahoo.com", days_before=0, is_new=False):
    email_from = os.getenv('EMAIL_FROM', 'arashar905@gmail.com')
    password = os.getenv('EMAIL_PASSWORD', 'maym ugmc dytw mbkm')
    
    if is_new:
        reminder_text = "New Task Notification:\n\n"
        reminder_text += f"- Title: {task.title}\n"
        reminder_text += f"- Deadline: {task.deadline}\n"
        reminder_text += f"- Priority: {task.priority}\n"
        reminder_text += f"- Status: {task.status}\n\n"
        if days_before == 0:
            reminder_text += f"Today: This task is due today ({task.deadline}) with priority {task.priority}."
        elif days_before == 1:
            reminder_text += f"Tomorrow: This task is due tomorrow ({task.deadline}) with priority {task.priority}."
        elif days_before == 2:
            reminder_text += f"2 Days Left: This task is due in 2 days ({task.deadline}) with priority {task.priority}."
        subject = f"New Task & Reminder: {task.title} ({days_before} day(s) left)"
    else:
        reminder_text = "Task Update Notification:\n\n"
        reminder_text += "Previous Task Details:\n"
        reminder_text += f"- Title: {old_task.title}\n"
        reminder_text += f"- Deadline: {old_task.deadline}\n"
        reminder_text += f"- Priority: {old_task.priority}\n"
        reminder_text += f"- Status: {old_task.status}\n\n"
        reminder_text += "Updated Task Details:\n"
        reminder_text += f"- Title: {task.title}\n"
        reminder_text += f"- Deadline: {task.deadline}\n"
        reminder_text += f"- Priority: {task.priority}\n"
        reminder_text += f"- Status: {task.status}\n\n"
        if days_before == 0:
            reminder_text += f"Today: This task is due today ({task.deadline}) with priority {task.priority}."
        elif days_before == 1:
            reminder_text += f"Tomorrow: This task is due tomorrow ({task.deadline}) with priority {task.priority}."
        elif days_before == 2:
            reminder_text += f"2 Days Left: This task is due in 2 days ({task.deadline}) with priority {task.priority}."
        subject = f"Task Update & Reminder: {task.title} ({days_before} day(s) left)"

    msg = MIMEText(reminder_text)
    msg['Subject'] = subject
    msg['From'] = email_from
    msg['To'] = email_to

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(email_from, password)
            server.send_message(msg)
        print(f"Reminder sent for {'new' if is_new else 'updated'} task: {task.title} ({days_before} day(s) before deadline) to {email_to}")
    except Exception as e:
        print(f"Error sending reminder for {'new' if is_new else 'updated'} task '{task.title}': {e}")
        print(f"Debug - Email details: From={email_from}, To={email_to}, Subject={subject}")

# Routes and API
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    if current_user.role == 'Viewer':
        # Viewers can see all projects
        projects = Project.query.all()
    else:
        # Managers and Editors can only see their own projects
        projects = Project.query.filter_by(user_id=current_user.id).all()
    return render_template('index.html', projects=projects)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            if user.role != role:  # Only for testing, you can remove this
                user.role = role
                db.session.commit()
            login_user(user)
            return redirect(url_for('index'))
        return "Invalid credentials", 401
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    print("Register route accessed!")
    if request.method == 'POST':
        print("POST request received!")
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        print(f"Received data: username={username}, role={role}")
        if not User.query.filter_by(username=username).first():
            new_user = User(username=username)
            new_user.set_password(password)
            new_user.role = role
            db.session.add(new_user)
            db.session.commit()
            login_user(new_user)
            print("User registered and logged in successfully!")
            return redirect(url_for('index'))
        print("Username already exists!")
        return "Username already exists", 400
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/project/<int:project_id>')
@login_required
def project(project_id):
    project = db.session.get(Project, project_id)  # Updated from Project.query.get
    if not project:
        return "Project not found", 404
    # Allow Viewers to see any project, but Managers/Editors can only see their own projects
    if project.user_id != current_user.id and current_user.role != 'Viewer':
        return "Unauthorized", 403
    tasks = Task.query.filter_by(project_id=project_id).all()
    return render_template('project.html', project=project, tasks=tasks)

@app.route('/project/new', methods=['POST'])
@login_required
def new_project():
    if current_user.role not in ['Manager']:
        return "Unauthorized: Only Managers can create projects", 403
    name = request.form['name']
    category = request.form.get('category', 'General')
    project = Project(name=name, category=category, user_id=current_user.id)
    db.session.add(project)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/task/new/<int:project_id>', methods=['POST'])
@login_required
def new_task(project_id):
    project = db.session.get(Project, project_id)  # Updated from Project.query.get
    if not project:
        return "Project not found", 404
    if current_user.role not in ['Manager', 'Editor']:
        return "Unauthorized: Only Managers and Editors can create tasks", 403
    if project.user_id != current_user.id:
        return "Unauthorized", 403
    title = request.form['title']
    deadline_str = request.form['deadline']
    deadline = datetime.strptime(deadline_str, '%Y-%m-%d').date()
    priority = request.form.get('priority', 'Medium')
    task = Task(title=title, deadline=deadline, priority=priority, status='Pending', project_id=project_id)
    db.session.add(task)
    db.session.commit()
    today = date.today()
    days_diff = (task.deadline - today).days
    if days_diff in [0, 1, 2]:
        send_reminder(task, task, "majid_0280@yahoo.com", days_diff, is_new=True)
    return redirect(url_for('project', project_id=project_id))

@app.route('/task/edit/<int:task_id>', methods=['POST'])
@login_required
def edit_task(task_id):
    task = db.session.get(Task, task_id)  # Updated from Task.query.get
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    project = db.session.get(Project, task.project_id)  # Updated from Project.query.get
    if not project:
        return jsonify({"status": "error", "message": "Project not found"}), 404
    if current_user.role not in ['Manager', 'Editor']:
        return jsonify({"status": "error", "message": "Unauthorized: Only Managers and Editors can edit tasks"}), 403
    if project.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    data = request.get_json()
    old_task = db.session.get(Task, task_id)  # Updated from Task.query.get
    task.title = data.get('title', task.title)
    task.deadline = datetime.strptime(data.get('deadline', task.deadline.isoformat()), '%Y-%m-%d').date()
    task.priority = data.get('priority', task.priority)
    task.status = data.get('status', task.status)
    db.session.commit()
    print(f"Task edited at ID {task_id}: {task}")
    today = date.today()
    days_diff = (task.deadline - today).days
    print(f"Debug - Days difference: {days_diff}")
    print(f"Debug - Deadline: {task.deadline}")
    print(f"Debug - Old Deadline: {old_task.deadline}")
    print(f"Debug - Priority: {task.priority}")
    print(f"Debug - Old Priority: {old_task.priority}")
    print(f"Debug - Deadline changed: {task.deadline != old_task.deadline}")
    print(f"Debug - Priority changed: {task.priority != old_task.priority}")
    if days_diff in [0, 1, 2]:
        if task.deadline != old_task.deadline or task.priority != old_task.priority:
            send_reminder(task, old_task, "majid_0280@yahoo.com", days_diff)
    tasks = Task.query.filter_by(project_id=project.id).all()
    return jsonify({
        "status": "success",
        "task": {
            "id": task.id,
            "title": task.title,
            "deadline": task.deadline.isoformat(),
            "priority": task.priority,
            "status": task.status
        },
        "tasks": [{"id": t.id, "title": t.title, "deadline": t.deadline.isoformat(), "priority": t.priority, "status": t.status} for t in tasks]
    })

@app.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    task = db.session.get(Task, task_id)  # Updated from Task.query.get
    if not task:
        return jsonify({"status": "error", "message": "Task not found"}), 404
    project = db.session.get(Project, task.project_id)  # Updated from Project.query.get
    if not project:
        return jsonify({"status": "error", "message": "Project not found"}), 404
    if current_user.role not in ['Manager']:
        return jsonify({"status": "error", "message": "Unauthorized: Only Managers can delete tasks"}), 403
    if project.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403
    db.session.delete(task)
    db.session.commit()
    print(f"Task deleted at ID {task_id}")
    tasks = Task.query.filter_by(project_id=project.id).all()
    return jsonify({
        "status": "success",
        "tasks": [{"id": t.id, "title": t.title, "deadline": t.deadline.isoformat(), "priority": t.priority, "status": t.status} for t in tasks]
    })

# API for task management
class TaskList(Resource):
    @login_required
    def get(self):
        project_id = request.args.get('project_id', type=int)
        if project_id:
            tasks = Task.query.filter_by(project_id=project_id).all()
        else:
            tasks = Task.query.all()
        return [{"id": t.id, "title": t.title, "deadline": t.deadline.isoformat(), "priority": t.priority, "status": t.status} for t in tasks]

class TaskDetail(Resource):
    @login_required
    def get(self, task_id):
        task = db.session.get(Task, task_id)  # Updated from Task.query.get
        if not task:
            return {"status": "error", "message": "Task not found"}, 404
        return {
            "id": task.id,
            "title": task.title,
            "deadline": task.deadline.isoformat(),
            "priority": task.priority,
            "status": task.status
        }

class UserRole(Resource):
    @login_required
    def get(self):
        return {"role": current_user.role}

@app.route('/test', methods=['GET', 'POST'])
def test():
    print("Test route accessed!")
    if request.method == 'POST':
        print("POST request received for test route!")
        test_input = request.form['testInput']
        print(f"Received test input: {test_input}")
        return "Test form submitted successfully!"
    return render_template('test.html')

api.add_resource(TaskList, '/api/tasks')
api.add_resource(TaskDetail, '/api/tasks/<int:task_id>')
api.add_resource(UserRole, '/api/user/role')

# Create database when the app runs
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username='user').first():
        default_user = User(username='user')
        default_user.set_password('pass')
        default_user.role = 'Manager'
        db.session.add(default_user)
        db.session.commit()
        print("Default user 'user' with password 'pass' (hashed) and role 'Manager' created in database.")

from datetime import timedelta  # Add this to imports at the top

@app.route('/reports', methods=['GET'])
@login_required
def reports():
    today = date.today()
    week_later = today + timedelta(days=7)
    date_range = [today + timedelta(days=i) for i in range(8)]  # 8 days including today

    # Dictionary to store tasks by date
    tasks_by_date = {d: [] for d in date_range}
    task_counts = {d: 0 for d in date_range}  # For chart data

    # For Managers and Editors, get tasks from their own projects
    if current_user.role in ['Manager', 'Editor']:
        projects = Project.query.filter_by(user_id=current_user.id).all()
        project_ids = [project.id for project in projects]
        tasks = Task.query.filter(Task.project_id.in_(project_ids), Task.deadline.between(today, week_later)).all()
    # For Viewers, get tasks from all projects
    else:
        tasks = Task.query.filter(Task.deadline.between(today, week_later)).all()

    # Categorize tasks by date
    for task in tasks:
        if task.deadline in tasks_by_date:
            tasks_by_date[task.deadline].append(task)
            task_counts[task.deadline] += 1

    # Prepare chart data
    chart_labels = [d.strftime('%Y-%m-%d') for d in date_range]
    chart_data = [task_counts[d] for d in date_range]

    return render_template('reports.html', tasks_by_date=tasks_by_date, date_range=date_range, chart_labels=chart_labels, chart_data=chart_data)

if __name__ == '__main__':
    app.run(debug=True)