from sqlalchemy import text


def check_db_connection():
    from app.database import engine

    with engine.connect() as connection:
        result = connection.execute(text("SELECT version()"))
        return result.scalar()


if __name__ == "__main__":
    print(check_db_connection())