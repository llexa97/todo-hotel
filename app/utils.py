"""
Utility functions for the Todo Hotel application
"""

import os
import re
import ast
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional, Tuple, List
from sqlalchemy.exc import IntegrityError
from flask import current_app
from . import db
from .models import Task


def check_duplicate_task(title: str, due_date: date) -> bool:
    """
    Check if an open task with the same title and due_date already exists.
    
    Args:
        title (str): Task title
        due_date (date): Task due date
        
    Returns:
        bool: True if duplicate exists, False otherwise
    """
    try:
        current_app.logger.debug(f"🔍 Vérification doublon - Titre: '{title}', Date: {due_date.strftime('%Y-%m-%d')}")
        
        existing_task = Task.query.filter_by(
            title=title,
            due_date=due_date,
            is_done=False
        ).first()
        
        if existing_task:
            current_app.logger.debug(f"⚠️ Doublon trouvé - ID: {existing_task.id}, Titre: '{title}'")
            return True
        else:
            current_app.logger.debug(f"✅ Pas de doublon - Titre: '{title}', Date: {due_date.strftime('%Y-%m-%d')}")
            return False
    except Exception as e:
        current_app.logger.error(f"❌ Erreur vérification doublon - Titre: '{title}', Erreur: {str(e)}")
        return False


def create_task_if_not_exists(title: str, due_date: date, is_recurring: bool = False, display_order: int = 0) -> Tuple[Task, int]:
    """
    Create a task if no open task with the same title and due_date exists.
    
    Args:
        title (str): Task title
        due_date (date): Task due date
        is_recurring (bool): Whether the task is recurring
        display_order (int): Display order for sorting
        
    Returns:
        Tuple[Task, int]: (task_object, status_code)
            - (task, 201) if task was created
            - (existing_task, 409) if duplicate exists
    """
    current_app.logger.info(f"🔨 Création tâche demandée - Titre: '{title}', Date: {due_date.strftime('%Y-%m-%d')}, Récurrente: {is_recurring}, Ordre: {display_order}")
    
    # Check for duplicates
    if check_duplicate_task(title, due_date):
        existing_task = Task.query.filter_by(
            title=title,
            due_date=due_date,
            is_done=False
        ).first()
        current_app.logger.info(f"ℹ️ Tâche déjà existante retournée - ID: {existing_task.id}, Titre: '{title}'")
        return existing_task, 409
    
    # Create new task
    try:
        current_app.logger.debug(f"💾 Insertion en base - Titre: '{title}', Date: {due_date.strftime('%Y-%m-%d')}")

        new_task = Task(
            title=title,
            due_date=due_date,
            is_recurring=is_recurring,
            display_order=display_order
        )
        db.session.add(new_task)
        db.session.commit()

        current_app.logger.info(f"✅ Tâche créée avec succès - ID: {new_task.id}, Titre: '{title}'")

        # Synchronize recurring task to script
        if is_recurring:
            current_app.logger.debug(f"🔄 Synchronisation tâche récurrente vers script - Titre: '{title}'")
            sync_success = sync_recurring_task_to_script(title, due_date)
            if sync_success:
                current_app.logger.info(f"✅ Synchronisation script réussie - Titre: '{title}'")
            else:
                current_app.logger.warning(f"⚠️ Synchronisation script échouée (tâche créée en DB) - Titre: '{title}'")

        return new_task, 201
    
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.warning(f"⚠️ IntegrityError (race condition) - Titre: '{title}', Erreur: {str(e)}")
        
        # Race condition: task was created between check and insert
        existing_task = Task.query.filter_by(
            title=title,
            due_date=due_date,
            is_done=False
        ).first()
        return existing_task, 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"💥 Erreur création tâche - Titre: '{title}', Erreur: {str(e)}", exc_info=True)
        raise e


def validate_task_data(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate task data for API requests.
    
    Args:
        data (dict): Task data to validate
        
    Returns:
        Tuple[bool, Optional[str]]: (is_valid, error_message)
            - (True, None) if data is valid
            - (False, error_message) if validation fails
    """
    # Check required fields
    if not data.get('title'):
        return False, "Title is required and cannot be empty"
    
    if not data.get('due_date'):
        return False, "due_date is required"
    
    # Validate title length
    title = data['title'].strip()
    if len(title) < 1:
        return False, "Title cannot be empty"
    
    if len(title) > 500:
        return False, "Title cannot exceed 500 characters"
    
    # Validate due_date format
    due_date_result = parse_due_date(data['due_date'])
    if due_date_result is None:
        return False, "due_date must be in YYYY-MM-DD format"
    
    # Validate is_recurring (optional field)
    if 'is_recurring' in data:
        if not isinstance(data['is_recurring'], bool):
            return False, "is_recurring must be a boolean"
    
    return True, None


def parse_due_date(date_string: str) -> Optional[date]:
    """
    Parse a date string in ISO format (YYYY-MM-DD).
    
    Args:
        date_string (str): Date string to parse
        
    Returns:
        Optional[date]: Parsed date object or None if invalid
    """
    if not isinstance(date_string, str):
        return None
    
    try:
        # Parse ISO format YYYY-MM-DD
        parsed_date = datetime.strptime(date_string.strip(), '%Y-%m-%d').date()
        return parsed_date
    
    except (ValueError, TypeError):
        return None


def get_target_weekend(reference_date=None):
    """
    Calculate the target weekend dates based on business rules.
    
    Rules:
    - If current date is Friday, Saturday, or Sunday → current weekend
    - Otherwise (Monday-Thursday) → next weekend
    
    Args:
        reference_date (date, optional): Reference date for calculation. 
                                       If None, uses today's date.
    
    Returns:
        tuple: (friday, saturday, sunday) dates for the target weekend
    """
    if reference_date is None:
        reference_date = date.today()
    
    current_app.logger.debug(f"📅 Calcul week-end cible - Date référence: {reference_date.strftime('%Y-%m-%d')} ({reference_date.strftime('%A')})")
    
    # Get weekday (0=Monday, 1=Tuesday, ..., 6=Sunday)
    weekday = reference_date.weekday()
    
    if weekday in [4, 5, 6]:  # Friday, Saturday, Sunday
        # Current weekend
        days_to_friday = weekday - 4  # 0 for Friday, 1 for Saturday, 2 for Sunday
        friday = reference_date - timedelta(days=days_to_friday)
        current_app.logger.debug("🎯 Week-end actuel sélectionné (Vendredi-Dimanche)")
    else:  # Monday-Thursday
        # Next weekend
        days_to_friday = 4 - weekday  # Days until Friday
        friday = reference_date + timedelta(days=days_to_friday)
        current_app.logger.debug("🎯 Week-end suivant sélectionné (Lundi-Jeudi)")
    
    # Calculate Saturday and Sunday
    saturday = friday + timedelta(days=1)
    sunday = friday + timedelta(days=2)
    
    current_app.logger.debug(f"✅ Week-end calculé - Vendredi: {friday.strftime('%Y-%m-%d')}, Samedi: {saturday.strftime('%Y-%m-%d')}, Dimanche: {sunday.strftime('%Y-%m-%d')}")

    return friday, saturday, sunday


def sync_recurring_task_to_script(title: str, due_date: date) -> bool:
    """
    Synchronize a recurring task to the generate_weekly_tasks.py script.

    Args:
        title (str): Task title
        due_date (date): Task due date (must be Friday, Saturday, or Sunday)

    Returns:
        bool: True if sync succeeded, False otherwise
    """
    try:
        # Determine day_offset based on weekday
        weekday = due_date.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

        if weekday == 4:  # Friday
            day_offset = 0
        elif weekday == 5:  # Saturday
            day_offset = 1
        elif weekday == 6:  # Sunday
            day_offset = 2
        else:
            current_app.logger.warning(f"⚠️ Sync ignorée - Date non weekend: {due_date.strftime('%Y-%m-%d')} ({due_date.strftime('%A')})")
            return False

        # Get path to generate_weekly_tasks.py
        script_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'generate_weekly_tasks.py')

        if not os.path.exists(script_path):
            current_app.logger.error(f"❌ Script introuvable: {script_path}")
            return False

        # Read the file
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse existing tasks to find max order for this day
        existing_tasks = _parse_weekly_tasks(content)
        max_order = max([t['order'] for t in existing_tasks if t['day_offset'] == day_offset], default=0)
        new_order = max_order + 1

        # Check if task already exists
        if any(t['title'] == title and t['day_offset'] == day_offset for t in existing_tasks):
            current_app.logger.info(f"ℹ️ Tâche déjà dans le script: '{title}' (day_offset={day_offset})")
            return True

        # Create new task entry
        day_name = ["Vendredi", "Samedi", "Dimanche"][day_offset]
        new_task_line = f'    {{"title": "{title}", "day_offset": {day_offset}, "order": {new_order}}},'

        # Find insertion point (before the closing bracket of WEEKLY_TASKS)
        # Find the section for the appropriate day
        pattern = rf'# {day_name}.*?\n((?:    \{{"title":.*?\}},\n)*)'
        match = re.search(pattern, content, re.DOTALL)

        if match:
            # Insert at the end of this day's section
            insert_pos = match.end(1)
            new_content = content[:insert_pos] + new_task_line + '\n' + content[insert_pos:]
        else:
            # Fallback: insert before closing bracket
            pattern = r'(\n]\s*\n)'
            match = re.search(pattern, content)
            if match:
                insert_pos = match.start()
                new_content = content[:insert_pos] + '\n    ' + new_task_line + content[insert_pos:]
            else:
                current_app.logger.error(f"❌ Impossible de trouver le point d'insertion dans {script_path}")
                return False

        # Write updated content
        with open(script_path, 'w', encoding='utf-8') as f:
            f.write(new_content)

        current_app.logger.info(f"✅ Tâche synchronisée dans script: '{title}' (day_offset={day_offset}, order={new_order})")
        return True

    except Exception as e:
        current_app.logger.error(f"💥 Erreur sync script - Titre: '{title}', Erreur: {str(e)}", exc_info=True)
        return False


def _parse_weekly_tasks(content: str) -> List[Dict[str, Any]]:
    """
    Parse WEEKLY_TASKS from the script content.

    Args:
        content (str): Script file content

    Returns:
        List[Dict]: List of parsed tasks
    """
    tasks = []

    # Find all task dictionaries
    pattern = r'\{"title":\s*"([^"]+)",\s*"day_offset":\s*(\d+),\s*"order":\s*(\d+)\}'

    for match in re.finditer(pattern, content):
        tasks.append({
            'title': match.group(1),
            'day_offset': int(match.group(2)),
            'order': int(match.group(3))
        })

    return tasks