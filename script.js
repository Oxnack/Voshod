document.getElementById('messageInput').focus();
let chat_history = "";
const xValues = [1];
const yValues = [0];
const transact = [0];
let userid = -1;
let balance = 0;
generate_Chart();
generate_Chart2();
function generate_Chart()
{
    new Chart("myChart", {
    type: "line",
    data: {
        labels: xValues,
        datasets: [{
        fill: false,
        lineTension: 0,
        backgroundColor: "rgba(0,0,255,1.0)",
        borderColor: "rgba(0,0,255,0.1)",
        data: yValues
        }]
    },
    options: {
        legend: {display: false},
        /*scales: {
        yAxes: [{ticks: {min: 0, max:100}}],
        }*/
    }
    });
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function generate_Chart2()
{
    new Chart("transactions", {
    type: "line",
    data: {
        labels: xValues,
        datasets: [{
        fill: false,
        lineTension: 0,
        backgroundColor: "rgba(255,0,,1.0)",
        borderColor: "rgba(255,0,,0.1)",
        data: transact
        }]
    },
    options: {
        legend: {display: false},
        /*scales: {
        yAxes: [{ticks: {min: 0, max:100}}],
        }*/
    }
    });
}

function handleKeyPress(event) {
    if (event.key === 'Enter') {
        sendMessage();
    }
}

function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    if (message === "") return;

    const chatBox = document.getElementById('chatBox');
    //const model = document.getElementById('modelSelector').value;
    const model = "ФинПомощник";

    // Добавление сообщения пользователя в чат
    const userMessage = document.createElement('div');
    userMessage.className = 'message you';
    userMessage.textContent = `Вы: ${message}`;
    chatBox.appendChild(userMessage);

    // Очистка поля ввода
    input.value = '';

    // Показываем "печатает..."
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'message other';
    typingIndicator.textContent = `${model}: печатает...`;
    chatBox.appendChild(typingIndicator);

    const preprompt = `Ты - финансовый ассистент команды веном. Твоя задача - не дать пользователю делать спонтанные покупки. Для этого вы должны переубедить его делать покупку, если она авляется спотанной или сильно повлияет на его финансовое положение. Вот значения баланса пользователя с каждой транзакцией: ${yValues.join(", ")}. Вот история твоей переписки с пользователем: `;
    chat_history += "Пользователь: " + message + ". ";
    // Отправка сообщения на сервер
    if (userid === -1)
    {
        fetch('http://oxnack.ru:5000/get_response', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: preprompt+chat_history
            })
        })
        .then(response => response.json())
        .then(data => {
            // Убираем "печатает..."
            chatBox.removeChild(typingIndicator);

            // Добавляем ответ от сервера
            const botMessage = document.createElement('div');
            botMessage.className = 'message other';
            botMessage.textContent = `${model}: ${data.response}`;
            chatBox.appendChild(botMessage);
            chat_history += "Ассистент: " + botMessage + ". ";
        })
        .catch(error => {
            // Убираем "печатает..." и показываем ошибку
            chatBox.removeChild(typingIndicator);

            const errorMessage = document.createElement('div');
            errorMessage.className = 'message error';
            errorMessage.textContent = `Ошибка: ${error.message}`;
            chatBox.appendChild(errorMessage);
        });
    } else {
        fetch('http://power.oxnack.ru:8074/check/' + userid, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                message: " история чата:" + chat_history
            })
        })
        .then(response => response.json())
        .then(data => {
            // Убираем "печатает..."
            chatBox.removeChild(typingIndicator);

            // Добавляем ответ от сервера
            const botMessage = document.createElement('div');
            botMessage.className = 'message other';
            botMessage.textContent = `${model}: ${data.response}`;
            chatBox.appendChild(botMessage);
            chat_history += "Ассистент: " + botMessage + ". ";
        })
        .catch(error => {
            // Убираем "печатает..." и показываем ошибку
            chatBox.removeChild(typingIndicator);

            const errorMessage = document.createElement('div');
            errorMessage.className = 'message error';
            errorMessage.textContent = `Ошибка: ${error.message}`;
            chatBox.appendChild(errorMessage);
        });
    }

}

function AddPoint()
{
    const y_pos = document.getElementById('amount').value;
    xValues.push(xValues[xValues.length - 1]+1);
    balance += parseInt(document.getElementById('payment_selector').value) * y_pos;
    yValues.push(balance);
    transact.push(y_pos * document.getElementById('payment_selector').value);
    generate_Chart();
    generate_Chart2();
}

function SetID()
{
    userid = document.getElementById('userID').value;
}
