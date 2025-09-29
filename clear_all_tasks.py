#!/usr/bin/env python3
"""
Script de suppression de toutes les tâches - Todo Hôtel
⚠️  ATTENTION: Ce script supprime TOUTES les tâches de la base de données

Usage:
    python clear_all_tasks.py [--confirm]

Options:
    --confirm    Confirme la suppression (requis pour éviter les suppressions accidentelles)
    --dry-run    Simule la suppression sans l'effectuer (pour compter les tâches)
"""

import sys
import argparse
from app import create_app
from app.models import Task
from app import db


def clear_all_tasks(dry_run=False):
    """
    Supprime toutes les tâches de la base de données.
    
    Args:
        dry_run (bool): Si True, simule sans supprimer
        
    Returns:
        int: Nombre de tâches supprimées
    """
    app = create_app()
    
    with app.app_context():
        # Compter les tâches existantes
        total_tasks = Task.query.count()
        
        if total_tasks == 0:
            print("📭 Aucune tâche trouvée dans la base de données")
            return 0
        
        if dry_run:
            print(f"🔍 MODE SIMULATION: {total_tasks} tâches seraient supprimées")
            
            # Afficher quelques exemples
            sample_tasks = Task.query.limit(5).all()
            print("\n📋 Exemples de tâches qui seraient supprimées:")
            for task in sample_tasks:
                status = "✅" if task.is_done else "⏳"
                print(f"  {status} {task.title} (due: {task.due_date})")
            
            if total_tasks > 5:
                print(f"  ... et {total_tasks - 5} autres tâches")
            
            return total_tasks
        
        # Suppression réelle
        print(f"🗑️  Suppression de {total_tasks} tâches...")
        
        try:
            # Supprimer toutes les tâches
            deleted_count = Task.query.delete()
            db.session.commit()
            
            print(f"✅ {deleted_count} tâches supprimées avec succès")
            return deleted_count
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erreur lors de la suppression: {str(e)}")
            raise e


def main():
    """Point d'entrée principal."""
    parser = argparse.ArgumentParser(
        description="Supprime toutes les tâches de la base de données Todo Hôtel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="⚠️  ATTENTION: Cette opération est irréversible!\n"
               "Assurez-vous d'avoir une sauvegarde de votre base de données."
    )
    parser.add_argument(
        "--confirm", 
        action="store_true",
        help="Confirme la suppression (REQUIS pour éviter les suppressions accidentelles)"
    )
    parser.add_argument(
        "--dry-run", 
        action="store_true",
        help="Simule la suppression sans l'effectuer (pour compter les tâches)"
    )
    
    args = parser.parse_args()
    
    print("🗑️  Script de suppression de toutes les tâches - Todo Hôtel")
    print("=" * 60)
    
    if args.dry_run:
        print("🔍 Mode simulation activé")
        try:
            count = clear_all_tasks(dry_run=True)
            if count > 0:
                print(f"\n💡 Pour supprimer réellement ces {count} tâches, utilisez:")
                print("   python clear_all_tasks.py --confirm")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            sys.exit(1)
            
    elif args.confirm:
        print("⚠️  SUPPRESSION CONFIRMÉE - Toutes les tâches vont être supprimées")
        response = input("Êtes-vous ABSOLUMENT sûr ? Tapez 'SUPPRIMER' pour continuer: ")
        
        if response != 'SUPPRIMER':
            print("❌ Suppression annulée")
            sys.exit(0)
        
        try:
            count = clear_all_tasks(dry_run=False)
            print(f"🎉 Opération terminée: {count} tâches supprimées")
        except Exception as e:
            print(f"❌ Erreur: {e}")
            sys.exit(1)
            
    else:
        print("❌ Erreur: Vous devez utiliser --confirm ou --dry-run")
        print("\n💡 Utilisez d'abord --dry-run pour voir ce qui serait supprimé:")
        print("   python clear_all_tasks.py --dry-run")
        print("\n⚠️  Puis --confirm pour supprimer réellement:")
        print("   python clear_all_tasks.py --confirm")
        sys.exit(1)



if __name__ == "__main__":
    main()