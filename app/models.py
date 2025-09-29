from datetime import datetime, timezone
from sqlalchemy import UniqueConstraint, Index
from . import db

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.Text, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    is_done = db.Column(db.Boolean, default=False, nullable=False)
    done_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    display_order = db.Column(db.Integer, nullable=True, default=0)
    
    # Index pour les requêtes
    __table_args__ = (
        Index('ix_task_is_done_created_at', 'is_done', 'created_at'),
        Index('ix_task_due_date', 'due_date'),
        # Note: La contrainte d'unicité conditionnelle sera gérée au niveau applicatif
        # car SQLite ne supporte pas les contraintes WHERE dans les UniqueConstraint
    )
    
    def __repr__(self):
        return f'<Task {self.id}: "{self.title}" due {self.due_date}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'is_done': self.is_done,
            'done_at': self.done_at.isoformat() if self.done_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_recurring': self.is_recurring,
            'display_order': self.display_order
        }