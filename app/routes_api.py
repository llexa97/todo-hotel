from flask import Blueprint, request, jsonify, current_app
from datetime import datetime
from . import db
from .models import Task
from .utils import validate_task_data, parse_due_date, create_task_if_not_exists

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/tasks', methods=['POST'])
def create_task():
    """
    Create a new task.
    
    Expected JSON payload:
    {
        "title": "Task title",
        "due_date": "YYYY-MM-DD",
        "is_recurring": false (optional)
    }
    
    Returns:
        - 201: Task created successfully
        - 409: Task already exists (same title + due_date)
        - 400: Validation error
        - 500: Server error
    """
    client_ip = request.remote_addr
    current_app.logger.info(f"📝 API POST /tasks - Client: {client_ip}")
    
    try:
        # Get JSON data with proper error handling
        if not request.is_json:
            current_app.logger.warning(f"❌ Requête sans JSON - Client: {client_ip}")
            return jsonify({
                'error': 'JSON payload is required',
                'message': 'Request must contain valid JSON data'
            }), 400
            
        try:
            data = request.get_json()
        except Exception as e:
            current_app.logger.warning(f"❌ JSON invalide - Client: {client_ip}, Erreur: {str(e)}")
            return jsonify({
                'error': 'Invalid JSON',
                'message': 'Request contains invalid JSON data'
            }), 400
        
        if not data:
            current_app.logger.warning(f"❌ Payload JSON vide - Client: {client_ip}")
            return jsonify({
                'error': 'JSON payload is required',
                'message': 'Request must contain valid JSON data'
            }), 400
            
        current_app.logger.debug(f"📊 Données reçues - Client: {client_ip}, Data: {data}")
        
        # Validate input data
        is_valid, error_message = validate_task_data(data)
        if not is_valid:
            current_app.logger.warning(f"❌ Validation échouée - Client: {client_ip}, Erreur: {error_message}")
            return jsonify({
                'error': 'Validation error',
                'message': error_message
            }), 400
        
        # Parse due_date
        due_date = parse_due_date(data['due_date'])
        if not due_date:
            current_app.logger.warning(f"❌ Format de date invalide - Client: {client_ip}, Date: {data.get('due_date')}")
            return jsonify({
                'error': 'Invalid date format',
                'message': 'due_date must be in YYYY-MM-DD format'
            }), 400
        
        # Log tentative de création
        task_title = data['title'].strip()
        is_recurring = data.get('is_recurring', False)
        display_order = data.get('display_order', 0)
        current_app.logger.info(f"🔨 Création tâche - Client: {client_ip}, Titre: '{task_title}', Date: {due_date.strftime('%Y-%m-%d')}, Récurrente: {is_recurring}, Ordre: {display_order}")
        
        # Create task with idempotency check
        task, status_code = create_task_if_not_exists(
            title=task_title,
            due_date=due_date,
            is_recurring=is_recurring,
            display_order=display_order
        )
        
        if status_code == 201:
            current_app.logger.info(f"✅ Tâche créée - Client: {client_ip}, ID: {task.id}, Titre: '{task.title}'")
            return jsonify({
                'message': 'Task created successfully',
                'task': task.to_dict()
            }), 201
        
        elif status_code == 409:
            current_app.logger.info(f"ℹ️ Tâche existe déjà - Client: {client_ip}, ID: {task.id}, Titre: '{task.title}'")
            return jsonify({
                'message': 'Task already exists',
                'task': task.to_dict()
            }), 409
        
        else:
            current_app.logger.error(f"❌ Erreur inattendue - Client: {client_ip}, Status: {status_code}")
            return jsonify({
                'error': 'Unexpected error',
                'message': 'An unexpected error occurred'
            }), 500
    
    except Exception as e:
        current_app.logger.error(f"💥 Erreur serveur POST /tasks - Client: {client_ip}, Erreur: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Server error',
            'message': 'An internal server error occurred'
        }), 500


@api_bp.route('/tasks', methods=['GET'])
def get_tasks():
    """
    Get tasks with optional filtering.
    
    Query parameters:
    - from: Start date (YYYY-MM-DD) - filter by due_date >= from
    - to: End date (YYYY-MM-DD) - filter by due_date <= to
    - is_done: Filter by completion status (true/false)
    - limit: Maximum number of results (default: 100)
    - offset: Number of results to skip (default: 0)
    
    Returns:
        - 200: List of tasks
        - 400: Invalid parameters
    """
    client_ip = request.remote_addr
    params = dict(request.args)
    current_app.logger.info(f"📋 API GET /tasks - Client: {client_ip}, Params: {params}")
    
    try:
        # Build query
        query = Task.query
        
        # Filter by date range
        from_date = request.args.get('from')
        if from_date:
            parsed_from = parse_due_date(from_date)
            if not parsed_from:
                current_app.logger.warning(f"❌ Date 'from' invalide - Client: {client_ip}, Date: {from_date}")
                return jsonify({
                    'error': 'Invalid from date',
                    'message': 'from parameter must be in YYYY-MM-DD format'
                }), 400
            query = query.filter(Task.due_date >= parsed_from)
            current_app.logger.debug(f"🔍 Filtre date début: {parsed_from.strftime('%Y-%m-%d')}")
        
        to_date = request.args.get('to')
        if to_date:
            parsed_to = parse_due_date(to_date)
            if not parsed_to:
                current_app.logger.warning(f"❌ Date 'to' invalide - Client: {client_ip}, Date: {to_date}")
                return jsonify({
                    'error': 'Invalid to date',
                    'message': 'to parameter must be in YYYY-MM-DD format'
                }), 400
            query = query.filter(Task.due_date <= parsed_to)
            current_app.logger.debug(f"🔍 Filtre date fin: {parsed_to.strftime('%Y-%m-%d')}")
        
        # Filter by completion status
        is_done = request.args.get('is_done')
        if is_done is not None:
            if is_done.lower() == 'true':
                query = query.filter(Task.is_done == True)
                current_app.logger.debug("🔍 Filtre: tâches terminées uniquement")
            elif is_done.lower() == 'false':
                query = query.filter(Task.is_done == False)
                current_app.logger.debug("🔍 Filtre: tâches ouvertes uniquement")
            else:
                current_app.logger.warning(f"❌ Paramètre 'is_done' invalide - Client: {client_ip}, Valeur: {is_done}")
                return jsonify({
                    'error': 'Invalid is_done parameter',
                    'message': 'is_done must be true or false'
                }), 400
        
        # Pagination
        limit = request.args.get('limit', 100, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        if limit < 1 or limit > 1000:
            current_app.logger.warning(f"❌ Limite invalide - Client: {client_ip}, Limite: {limit}")
            return jsonify({
                'error': 'Invalid limit',
                'message': 'limit must be between 1 and 1000'
            }), 400
        
        if offset < 0:
            current_app.logger.warning(f"❌ Offset invalide - Client: {client_ip}, Offset: {offset}")
            return jsonify({
                'error': 'Invalid offset',
                'message': 'offset must be 0 or greater'
            }), 400
        
        current_app.logger.debug(f"📊 Pagination - Limite: {limit}, Offset: {offset}")
        
        # Order by: open tasks first, then by display_order, due_date, and creation date
        query = query.order_by(Task.is_done.asc(), Task.display_order.asc(), Task.due_date.asc(), Task.created_at.desc())
        
        # Apply pagination
        total_count = query.count()
        tasks = query.offset(offset).limit(limit).all()
        
        current_app.logger.info(f"✅ Requête GET /tasks réussie - Client: {client_ip}, Total: {total_count}, Retournées: {len(tasks)}")
        
        return jsonify({
            'tasks': [task.to_dict() for task in tasks],
            'pagination': {
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            }
        }), 200
    
    except Exception as e:
        current_app.logger.error(f"💥 Erreur serveur GET /tasks - Client: {client_ip}, Erreur: {str(e)}", exc_info=True)
        return jsonify({
            'error': 'Server error',
            'message': 'An internal server error occurred'
        }), 500