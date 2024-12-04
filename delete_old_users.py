import psycopg2
from datetime import timedelta, date
from hanex import DATABASE_URL  # Импортируйте URL для подключения к базе данных


def delete_old_users():
    today = date.today()
    days_since_friday = today.weekday() - 4  # 4 — это пятница
    last_friday = today - timedelta(days=days_since_friday)

    conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    cursor = conn.cursor()
    cursor.execute(
        """
        DELETE FROM user_stats
        WHERE join_date < %s
        """,
        (last_friday,),
    )
    conn.commit()
    cursor.close()
    conn.close()


if __name__ == "__main__":
    delete_old_users()
