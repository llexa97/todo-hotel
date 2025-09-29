from flask import Blueprint, jsonify, render_template, request, redirect, url_for, flash, abort, current_app
from datetime import datetime, timezone, timedelta
from sqlalchemy import func
import locale
from . import db
from .models import Task
from .utils import get_target_weekend, validate_task_data, parse_due_date, create_task_if_not_exists

# Configuration de la locale française
try:
    locale.setlocale(locale.LC_TIME, 'fr_FR.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'fr_FR')
    except locale.Error:
        try:
            locale.setlocale(locale.LC_TIME, 'French_France')
        except locale.Error:
            pass  # Fallback: keep default locale

def format_french_date(date_obj):
    """Format date in French manually if locale is not available."""
    days = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
    months = ['janvier', 'février', 'mars', 'avril', 'mai', 'juin',
              'juillet', 'août', 'septembre', 'octobre', 'novembre', 'décembre']
    
    day_name = days[date_obj.weekday()]
    month_name = months[date_obj.month - 1]
    
    return f"{day_name} {date_obj.day} {month_name} {date_obj.year}"

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """
    Main page with three views: all tasks, current weekend, completed tasks.
    """
    client_ip = request.remote_addr
    view = request.args.get('view', 'weekend')
    current_app.logger.info(f"🏠 GET / - Client: {client_ip}, Vue: {view}")
    
    try:
        # Get current date for display
        current_date = datetime.now()
        
        # Get target weekend dates
        friday, saturday, sunday = get_target_weekend()
        current_app.logger.debug(f"📅 Week-end cible calculé - Vendredi: {friday.strftime('%Y-%m-%d')}, Samedi: {saturday.strftime('%Y-%m-%d')}, Dimanche: {sunday.strftime('%Y-%m-%d')}")
        
        # Get view parameter (replaces old filter)
        # view = request.args.get('view', 'weekend')  # all, weekend, completed
        
        if view == 'all':
            # Show all tasks grouped by week
            return render_all_tasks(current_date)
        elif view == 'completed':
            # Show all completed tasks
            return render_completed_tasks(current_date)
        else:
            # Default: show current weekend
            return render_weekend_tasks(current_date, friday, saturday, sunday)
                             
    except Exception as e:
        flash(f'Error loading tasks: {str(e)}', 'error')
        current_date_now = datetime.now()
        return render_template('index.html', 
                             current_date=current_date_now,
                             current_date_french=format_french_date(current_date_now),
                             view='weekend',
                             friday_tasks=[],
                             saturday_tasks=[],
                             sunday_tasks=[],
                             friday_date=None,
                             saturday_date=None,
                             sunday_date=None)


def render_weekend_tasks(current_date, friday, saturday, sunday):
    """Render current weekend view (existing functionality)."""
    # Get tasks for target weekend
    tasks = Task.query.filter(
        Task.due_date.in_([friday, saturday, sunday])
    ).order_by(Task.is_done.asc(), Task.display_order.asc(), Task.due_date.asc(), Task.created_at.desc()).all()
    
    # Group tasks by day
    friday_tasks = [t for t in tasks if t.due_date == friday]
    saturday_tasks = [t for t in tasks if t.due_date == saturday]
    sunday_tasks = [t for t in tasks if t.due_date == sunday]
    
    return render_template('index.html', 
                         current_date=current_date,
                         current_date_french=format_french_date(current_date),
                         view='weekend',
                         friday_tasks=friday_tasks,
                         saturday_tasks=saturday_tasks,
                         sunday_tasks=sunday_tasks,
                         friday_date=friday,
                         saturday_date=saturday,
                         sunday_date=sunday)


def render_all_tasks(current_date):
    """Render all tasks grouped by week."""
    # Get all tasks ordered by due date descending, then by display order
    tasks = Task.query.order_by(Task.due_date.desc(), Task.is_done.asc(), Task.display_order.asc(), Task.created_at.desc()).all()
    
    # Group tasks by week
    weeks = {}
    for task in tasks:
        # Calculate the Friday of the week for this task
        task_date = task.due_date
        days_since_friday = (task_date.weekday() - 4) % 7  # Friday is 4
        if task_date.weekday() < 4:  # Monday to Thursday
            days_since_friday += 7
        friday_of_week = task_date - timedelta(days=days_since_friday)
        
        week_key = friday_of_week.strftime('%Y-%m-%d')
        if week_key not in weeks:
            weeks[week_key] = {
                'friday_date': friday_of_week,
                'saturday_date': friday_of_week + timedelta(days=1),
                'sunday_date': friday_of_week + timedelta(days=2),
                'friday_tasks': [],
                'saturday_tasks': [],
                'sunday_tasks': []
            }
        
        # Add task to appropriate day
        if task.due_date == friday_of_week:
            weeks[week_key]['friday_tasks'].append(task)
        elif task.due_date == friday_of_week + timedelta(days=1):
            weeks[week_key]['saturday_tasks'].append(task)
        elif task.due_date == friday_of_week + timedelta(days=2):
            weeks[week_key]['sunday_tasks'].append(task)
    
    # Sort weeks by date (most recent first)
    sorted_weeks = sorted(weeks.items(), key=lambda x: x[1]['friday_date'], reverse=True)
    
    return render_template('index.html',
                         current_date=current_date,
                         current_date_french=format_french_date(current_date),
                         view='all',
                         all_weeks=sorted_weeks)



def render_completed_tasks(current_date):
    """Render all completed tasks grouped by completion date."""
    # Get all completed tasks ordered by completion date, then by display order
    completed_tasks = Task.query.filter(
        Task.is_done == True,
        Task.done_at.isnot(None)
    ).order_by(Task.done_at.desc(), Task.display_order.asc()).all()
    
    # Group by completion date
    completed_by_date = {}
    for task in completed_tasks:
        # Convert UTC to local date for grouping
        completion_date = task.done_at.replace(tzinfo=timezone.utc).astimezone().date()
        date_key = completion_date.strftime('%Y-%m-%d')
        
        if date_key not in completed_by_date:
            completed_by_date[date_key] = {
                'date': completion_date,
                'tasks': []
            }
        completed_by_date[date_key]['tasks'].append(task)
    
    # Sort by date (most recent first)
    sorted_completed = sorted(completed_by_date.items(), key=lambda x: x[1]['date'], reverse=True)
    
    return render_template('index.html',
                         current_date=current_date,
                         current_date_french=format_french_date(current_date),
                         view='completed',
                         completed_by_date=sorted_completed)


@main_bp.route('/tasks', methods=['POST'])
def create_task_web():
    """
    Create a new task via web form.
    """
    client_ip = request.remote_addr
    current_app.logger.info(f"📝 POST /tasks (web) - Client: {client_ip}")
    
    try:
        # Get form data
        title = request.form.get('title', '').strip()
        due_date_str = request.form.get('due_date', '')
        is_recurring = 'is_recurring' in request.form
        
        current_app.logger.debug(f"📊 Formulaire web - Titre: '{title}', Date: {due_date_str}, Récurrente: {is_recurring}")
        
        # Validate required fields
        if not title:
            flash('Title is required', 'error')
            return redirect(url_for('main.index'))
        
        if not due_date_str:
            flash('Due date is required', 'error')
            return redirect(url_for('main.index'))
        
        # Parse due date
        due_date = parse_due_date(due_date_str)
        if not due_date:
            flash('Invalid date format. Please use YYYY-MM-DD', 'error')
            return redirect(url_for('main.index'))
        
        # Create task with idempotency
        task, status_code = create_task_if_not_exists(
            title=title,
            due_date=due_date,
            is_recurring=is_recurring
        )
        
        if status_code == 201:
            flash(f'Task "{title}" created successfully', 'success')
        elif status_code == 409:
            flash(f'Task "{title}" already exists for {due_date}', 'warning')
        else:
            flash('Error creating task', 'error')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        flash(f'Error creating task: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/tasks/<int:task_id>/toggle', methods=['POST'])
def toggle_task(task_id):
    """
    Toggle task completion status.
    """
    try:
        task = db.session.get(Task, task_id) or abort(404)
        
        is_htmx = request.headers.get('HX-Request') == 'true'

        # Toggle status
        task.is_done = not task.is_done
        
        # Set done_at timestamp
        if task.is_done:
            task.done_at = datetime.now(timezone.utc)
        else:
            task.done_at = None
        
        db.session.commit()
        
        if is_htmx:
            current_app.logger.debug(f"🔁 HTMX toggle pour la tâche {task.id} ({'fait' if task.is_done else 'à faire'})")
            return render_template('task_item.html', task=task)

        status = "completed" if task.is_done else "reopened"
        flash(f'Task "{task.title}" {status}', 'success')
        
        return redirect(url_for('main.index'))
        
    except Exception as e:
        flash(f'Error updating task: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/tasks/<int:task_id>/edit', methods=['POST'])
def edit_task(task_id):
    """
    Edit task title.
    """
    try:
        task = db.session.get(Task, task_id) or abort(404)
        
        # Get new title from form
        new_title = request.form.get('title', '').strip()
        
        if not new_title:
            flash('Title cannot be empty', 'error')
            return redirect(url_for('main.index'))
        
        old_title = task.title
        task.title = new_title
        db.session.commit()
        
        flash(f'Task updated from "{old_title}" to "{new_title}"', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        flash(f'Error updating task: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
def delete_task(task_id):
    """
    Delete a task.
    """
    try:
        task = db.session.get(Task, task_id) or abort(404)
        task_title = task.title
        
        db.session.delete(task)
        db.session.commit()
        
        flash(f'Task "{task_title}" deleted', 'success')
        return redirect(url_for('main.index'))
        
    except Exception as e:
        flash(f'Error deleting task: {str(e)}', 'error')
        return redirect(url_for('main.index'))


@main_bp.route('/healthz', methods=['GET'])
def healthcheck():
    """
    Health check endpoint to verify application status.
    
    Returns:
        - 200: Application is healthy
        - 500: Application has issues
    """
    client_ip = request.remote_addr
    current_app.logger.debug(f"🏥 Healthcheck - Client: {client_ip}")
    
    try:
        # Check database connectivity
        db.session.execute(db.text('SELECT 1'))
        current_app.logger.debug("✅ Base de données connectée")
        
        response_data = {
            'status': 'healthy',
            'version': '1.0.0',
            'database': 'connected'
        }
        
        current_app.logger.debug(f"✅ Healthcheck OK - Client: {client_ip}")
        return jsonify(response_data), 200
    
    except Exception as e:
        current_app.logger.error(f"❌ Healthcheck failed - Client: {client_ip}, Erreur: {str(e)}")
        return jsonify({
            'status': 'unhealthy',
            'version': '1.0.0',
            'database': 'disconnected',
            'error': str(e)
        }), 500
