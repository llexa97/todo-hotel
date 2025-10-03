#!/usr/bin/env python3
"""
Script de génération automatique des tâches récurrentes - Todo Hôtel
Génère les tâches hebdomadaires pour le week-end cible.

Usage:
    python generate_weekly_tasks.py [--dry-run] [--api-url URL]

Conçu pour fonctionner via cron tous les vendredis à 06:00 Europe/Paris
"""

import os
import sys
import argparse
import json
import requests
from datetime import datetime, timedelta
from typing import List, Dict
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

# Configuration par défaut
DEFAULT_API_BASE_URL = "http://localhost:8081/api"
DEFAULT_TIMEOUT = 10

# Tâches hebdomadaires prédéfinies
# day_offset: 0 = vendredi, 1 = samedi, 2 = dimanche
# order: ordre d'affichage (1 = premier, plus élevé = plus tard)
WEEKLY_TASKS = [
    # Vendredi
    {"title": "Prendre les info auprès de jérémie", "day_offset": 0, "order": 1},
    {"title": "Lancer les machines", "day_offset": 0, "order": 2},
    {"title": "Défaire l'estrade", "day_offset": 0, "order": 3},
    {"title": "Sortir les affaires du pti dej", "day_offset": 0, "order": 4},
    {"title": "Vérifier les cakes", "day_offset": 0, "order": 5},
    {"title": "Faire les inox", "day_offset": 0, "order": 6},
    {"title": "nettoyer le bar et le rail", "day_offset": 0, "order": 7},
    {"title": "Nettoyer le présentoire a bouteille", "day_offset": 0, "order": 8},
    {"title": "Aspirer les banquettes et chaises", "day_offset": 0, "order": 9},
    {"title": "Faire les couverts au vinaigre et mettre dans les serviettes", "day_offset": 0, "order": 10},
    {"title": "Nettoyer les toilettes", "day_offset": 0, "order": 11},
    {"title": "Nettoyer le sol", "day_offset": 0, "order": 12},
    {"title": "Plier les serviettes de la cuisine", "day_offset": 0, "order": 13},
    
    # Samedi  
    {"title": "Lancer les machine", "day_offset": 1, "order": 1},
    {"title": "Souffler l'exterieur", "day_offset": 1, "order": 2},
    {"title": "Nettoyer la rigole", "day_offset": 1, "order": 3},
    {"title": "Nettoyer et mettre en place la salle de séminaire", "day_offset": 1, "order": 4},
    {"title": "Nettoyer et Désinfecter la réception", "day_offset": 1, "order": 5},
    {"title": "Vérifier les cakes", "day_offset": 1, "order": 6},
    
    # Dimanche
    {"title": "Lancer les machine", "day_offset": 2, "order": 1},
    {"title": "Finir de souffler l'exterieur", "day_offset": 2, "order": 2},
    {"title": "Vérifier les cakes", "day_offset": 2, "order": 3},
    {"title": "Remonter l'estrade", "day_offset": 2, "order": 4},
    {"title": "Faire les poussieres dans tous l'hotel", "day_offset": 2, "order": 5},
    {"title": "Plié les serviettes de l'hotel", "day_offset": 2, "order": 6},
    {"title": "Nettoyage du sol de la cuisine", "day_offset": 2, "order": 7},
    {"title": "jeter les poubelles", "day_offset": 2, "order": 8},
]


def calculate_target_weekend() -> datetime:
    """
    Calcule le week-end cible selon la logique métier.
    
    Returns:
        datetime: Date du vendredi du week-end cible
    """
    today = datetime.now()
    current_weekday = today.weekday()  # 0=lundi, 4=vendredi, 6=dimanche
    
    if current_weekday >= 4:  # Si vendredi, samedi ou dimanche
        # Week-end actuel
        days_to_friday = 4 - current_weekday
        if days_to_friday <= 0:
            days_to_friday += 7
        friday = today + timedelta(days=days_to_friday - 7)
    else:
        # Week-end suivant
        days_to_friday = 4 - current_weekday
        friday = today + timedelta(days=days_to_friday)
    
    return friday.replace(hour=0, minute=0, second=0, microsecond=0)


def create_task(api_url: str, title: str, due_date: datetime, display_order: int = 0, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """
    Crée une tâche via l'API.
    
    Args:
        api_url: URL de base de l'API
        title: Titre de la tâche
        due_date: Date d'échéance
        display_order: Ordre d'affichage
        timeout: Timeout pour la requête HTTP
        
    Returns:
        bool: True si succès (201 ou 409), False sinon
    """
    endpoint = f"{api_url}/tasks"
    payload = {
        "title": title,
        "due_date": due_date.strftime("%Y-%m-%d"),
        "is_recurring": True,
        "display_order": display_order
    }
    
    try:
        response = requests.post(endpoint, json=payload, timeout=timeout)
        
        if response.status_code == 201:
            print(f"✓ CRÉÉE: {title} - {due_date.strftime('%Y-%m-%d')}")
            return True
        elif response.status_code == 409:
            print(f"✓ EXISTE: {title} - {due_date.strftime('%Y-%m-%d')}")
            return True
        else:
            print(f"✗ ERREUR {response.status_code}: {title} - {response.text[:100]}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"✗ TIMEOUT: {title} - Délai d'attente dépassé")
        return False
    except requests.exceptions.ConnectionError:
        print(f"✗ CONNEXION: {title} - Impossible de se connecter à l'API")
        return False
    except Exception as e:
        print(f"✗ EXCEPTION: {title} - {str(e)}")
        return False


def test_api_connection(api_url: str, timeout: int = DEFAULT_TIMEOUT) -> bool:
    """
    Teste la connexion à l'API.
    
    Args:
        api_url: URL de base de l'API
        timeout: Timeout pour la requête
        
    Returns:
        bool: True si l'API répond, False sinon
    """
    try:
        healthcheck_url = api_url.replace('/api', '/healthz')
        response = requests.get(healthcheck_url, timeout=timeout)
        
        if response.status_code == 200:
            health_data = response.json()
            print(f"✓ API accessible - Status: {health_data.get('status', 'unknown')}")
            return True
        else:
            print(f"✗ API erreur {response.status_code}")
            return False
            
    except Exception as e:
        print(f"✗ Test API échoué: {e}")
        return False


def generate_tasks(api_url: str, dry_run: bool = False) -> Dict:
    """
    Génère toutes les tâches hebdomadaires.
    
    Args:
        api_url: URL de base de l'API
        dry_run: Si True, simule sans créer les tâches
        
    Returns:
        dict: Statistiques de génération
    """
    print(f"🕐 Génération des tâches récurrentes - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 Mode: {'SIMULATION' if dry_run else 'PRODUCTION'}")
    
    if not dry_run and not test_api_connection(api_url):
        return {"success": False, "error": "API inaccessible"}
    
    friday = calculate_target_weekend()
    print(f"📅 Week-end cible: {friday.strftime('%Y-%m-%d')} (Vendredi)")
    
    stats = {"total": len(WEEKLY_TASKS), "success": 0, "errors": 0, "tasks": []}
    
    for task_def in WEEKLY_TASKS:
        due_date = friday + timedelta(days=task_def["day_offset"])
        day_name = ["Vendredi", "Samedi", "Dimanche"][task_def["day_offset"]]
        
        task_info = {
            "title": task_def["title"],
            "due_date": due_date.strftime("%Y-%m-%d"),
            "day": day_name
        }
        
        if dry_run:
            print(f"🔍 SIMUL: {task_def['title']} - {due_date.strftime('%Y-%m-%d')} ({day_name})")
            task_info["status"] = "simulated"
            stats["success"] += 1
        else:
            success = create_task(api_url, task_def["title"], due_date, task_def.get("order", 0))
            task_info["status"] = "success" if success else "error"
            
            if success:
                stats["success"] += 1
            else:
                stats["errors"] += 1
        
        stats["tasks"].append(task_info)
    
    print(f"📊 Résultat: {stats['success']}/{stats['total']} tâches traitées")
    if stats["errors"] > 0:
        print(f"⚠️  {stats['errors']} erreurs détectées")
    
    stats["success_rate"] = stats["success"] / stats["total"] if stats["total"] > 0 else 0
    return stats


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Génère les tâches récurrentes hebdomadaires pour Todo Hôtel"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simule la génération sans créer les tâches"
    )
    parser.add_argument(
        "--api-url",
        default=os.environ.get("API_BASE_URL", DEFAULT_API_BASE_URL),
        help=f"URL de base de l'API (défaut: {DEFAULT_API_BASE_URL})"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Timeout HTTP en secondes (défaut: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--json",
        action="store_true", 
        help="Sortie au format JSON"
    )
    
    args = parser.parse_args()
    
    try:
        stats = generate_tasks(args.api_url, args.dry_run)
        
        if args.json:
            print(json.dumps(stats, indent=2, ensure_ascii=False))
        else:
            print("🎉 Génération terminée!")
        
        # Code de sortie selon le succès
        if stats.get("success", 0) == stats.get("total", 0):
            sys.exit(0)  # Succès complet
        elif stats.get("success", 0) > 0:
            sys.exit(1)  # Succès partiel
        else:
            sys.exit(2)  # Échec total
            
    except KeyboardInterrupt:
        print("\n⚠️  Interruption utilisateur")
        sys.exit(130)
    except Exception as e:
        print(f"❌ Erreur inattendue: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()