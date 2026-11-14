from nicegui import ui

from database.handler import Database
from src.ui.routes import register_routes


def create_db() -> Database:
    db = Database(
        db_path='database/reviews.db',
        schema_path='database/schema.sql',
    )
    return db


def main():
    db = create_db()
    register_routes(db)
    ui.run(reload=False, title='SmartReview', port=8080)


if __name__ == '__main__':
    main()
