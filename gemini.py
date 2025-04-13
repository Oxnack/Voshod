from flask import Flask, request, jsonify
import requests
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Разрешаем CORS для всех доменов

@app.route('/check/<id>', methods=['POST'])
def check_user(id):
    # Получаем сообщение из тела запроса
    data = request.get_json()
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    message = data['message']
    
    try:
        # Получаем аналитические данные от power.oxnack.ru
        analytics_url = f"http://power.oxnack.ru:8045/state/{id}"
        analytics_response = requests.get(analytics_url)
        analytics_response.raise_for_status()  # Проверяем на ошибки HTTP
        
        analytics_data = analytics_response.json()
        
        # Уменьшаем данные аналитики
        simplified_data = {
            "transactions": analytics_data.get("transactions", []),
            "sr_users_zp": analytics_data.get("avg_income"),
            "sr_stat_category": analytics_data.get("category_stats"),
            "similar_users_count": analytics_data.get("similar_users_count", 0),
            "user_id": id
        }
        
        # Формируем промпт для нейросети
        prompt = f"""
        Проанализируйте аналитические данные пользователя и ответьте на его сообщение.
        
        Аналитические данные:
        {simplified_data}
        
        Сообщение пользователя: {message}
        
        Пожалуйста, дайте развернутый ответ, учитывая финансовые привычки пользователя.
        """
        
        # Отправляем запрос к нейросети
        neural_url = "http://oxnack.ru:5000/get_response"
        neural_response = requests.post(neural_url, json={"prompt": prompt})
        neural_response.raise_for_status()
        
        neural_data = neural_response.json()
        
        # Возвращаем ответ от нейросети
        return jsonify(neural_data)
        
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"External service error: {str(e)}"}), 502
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)