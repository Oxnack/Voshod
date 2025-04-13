from flask import Flask, jsonify
import psycopg2
from datetime import datetime, timedelta
from collections import defaultdict
from contextlib import closing
from statistics import mean
from flask_cors import CORS  # Импортируем CORS

app = Flask(__name__)
CORS(app)  # Разрешаем все CORS-запросы для всех маршрутов

# Database config
DB_CONFIG = {
    "host": "power.oxnack.ru",
    "database": "postgres",
    "user": "root",
    "password": "0000"
}

def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)

def get_similar_users(user_id):
    with closing(get_db_connection()) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT gender_cd, age, lvn_state_nm 
            FROM users_data 
            WHERE party_rk = %s
        """, (user_id,))
        user_data = cur.fetchone()
        
        if not user_data:
            return None
            
        gender, age, region = user_data
        
        cur.execute("""
            SELECT party_rk 
            FROM users_data 
            WHERE gender_cd = %s 
              AND lvn_state_nm = %s 
              AND age BETWEEN %s AND %s
        """, (gender, region, max(0, age-10), age+10))
        return [row[0] for row in cur.fetchall()]

def calculate_category_stats(user_ids):
    if not user_ids:
        return {}
    
    with closing(get_db_connection()) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 
                loyalty_cashback_category_nm,
                AVG(days_between) as avg_days,
                30.0/AVG(days_between) as freq_per_month
            FROM (
                SELECT 
                    party_rk,
                    loyalty_cashback_category_nm,
                    EXTRACT(EPOCH FROM (
                        (real_transaction_dttm::timestamp - LAG(real_transaction_dttm::timestamp) OVER (
                            PARTITION BY party_rk, loyalty_cashback_category_nm 
                            ORDER BY real_transaction_dttm::timestamp
                        ))
                    ))/86400 AS days_between
                FROM all_user_transactions
                WHERE party_rk IN %s
                  AND loyalty_cashback_category_nm IS NOT NULL
                  AND loyalty_cashback_category_nm != '0'
                  AND transaction_type_cd = 'PUC'
            ) subq
            WHERE days_between > 0
            GROUP BY loyalty_cashback_category_nm
        """, (tuple(user_ids),))
        
        return {
            row[0]: {
                'avg_days_between_purchases': round(float(row[1]), 2),
                'purchase_frequency_per_month': round(float(row[2]), 2)
            }
            for row in cur.fetchall()
        }

def get_user_transactions(user_id):
    one_month_ago = datetime.now() - timedelta(days=30)
    with closing(get_db_connection()) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT 
                transaction_type_cd,
                CAST(REPLACE(transaction_amt_rur, ',', '.') AS FLOAT) as transaction_amt,
                real_transaction_dttm::timestamp,
                brand_nm,
                loyalty_cashback_category_nm,
                CAST(REPLACE(loyalty_accrual_rub_amt, ',', '.') AS FLOAT) as cashback_amt,
                utilization_flg
            FROM all_user_transactions
            WHERE party_rk = %s
              AND real_transaction_dttm::timestamp >= %s
            ORDER BY real_transaction_dttm DESC
        """, (user_id, one_month_ago))
        
        columns = ['transaction_type_cd', 'transaction_amt_rur', 'real_transaction_dttm',
                  'brand_nm', 'loyalty_cashback_category_nm', 'loyalty_accrual_rub_amt', 'utilization_flg']
        return [dict(zip(columns, row)) for row in cur.fetchall()]

def calculate_approxymac(transactions):
    category_data = defaultdict(list)
    
    # Группируем транзакции по категориям и дням
    for tx in transactions:
        if not tx['loyalty_cashback_category_nm'] or tx['loyalty_cashback_category_nm'] == '0':
            continue
            
        date = tx['real_transaction_dttm'].date()
        amount = tx['transaction_amt_rur']
        category = tx['loyalty_cashback_category_nm']
        
        category_data[category].append((date, amount))
    
    approxymac = {}
    
    for category, transactions in category_data.items():
        if len(transactions) < 2:
            approxymac[category] = False
            continue
            
        # Сортируем по дате
        transactions.sort()
        
        # Группируем по дням и суммируем траты
        daily_spending = defaultdict(float)
        for date, amount in transactions:
            daily_spending[date] += amount
        
        dates = sorted(daily_spending.keys())
        amounts = [daily_spending[date] for date in dates]
        
        # Последний день и предпоследний
        last_day = amounts[-1]
        prev_day = amounts[-2] if len(amounts) >= 2 else 0
        
        # Если данных достаточно, вычисляем тренд
        if len(amounts) >= 3:
            # Средний прирост за период
            avg_increase = (amounts[-1] - amounts[0]) / len(amounts)
            # Ожидаемое значение для последнего дня
            expected = amounts[-2] + avg_increase
        else:
            expected = amounts[-2] if len(amounts) >= 2 else 0
        
        # Проверяем условие: последний день > 2 * ожидаемого или предыдущего
        approxymac[category] = last_day > 2 * expected or (len(amounts) >= 2 and last_day > 2 * prev_day)
    
    return approxymac

@app.route('/state/<int:user_id>', methods=['GET'])
def get_user_state(user_id):
    similar_users = get_similar_users(user_id)
    
    if not similar_users:
        return jsonify({"error": "User not found or no similar users"}), 404
    
    with closing(get_db_connection()) as conn, conn.cursor() as cur:
        cur.execute("""
            SELECT AVG(monthly_income_amt)
            FROM users_data
            WHERE party_rk IN %s
            AND monthly_income_amt > 0
        """, (tuple(similar_users),))
        avg_income = cur.fetchone()[0]
    
    transactions = get_user_transactions(user_id)
    category_stats = calculate_category_stats(similar_users)
    approxymac_stats = calculate_approxymac(transactions)
    
    response = {
        "transactions": transactions,
        "sr_users_zp": avg_income,
        "sr_stat_category": category_stats,
        "approxymac": approxymac_stats,
        "similar_users_count": len(similar_users),
        "user_id": user_id
    }
    
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8045)