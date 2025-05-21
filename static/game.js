const socket = io({ autoConnect: false });
let currentUsername = "";

function formatCard(card) {
    if (typeof card === 'object' && card !== null) {
        const val = card.value || card.rank || 'Unknown';
        const suit = card.suit || 'Unknown';
        return `${val} of ${capitalize(suit)}`;
    }
    return card;
}

function capitalize(str) {
    return str.charAt(0).toUpperCase() + str.slice(1);
}

function register() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    fetch('/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
        .then(res => res.json())
        .then(data => {
            document.getElementById("auth-msg").textContent = data.message || data.error;
        });
}

function login() {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value.trim();

    fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
    })
        .then(res => res.json().then(data => ({ status: res.status, data })))
        .then(({ status, data }) => {
            if (status === 200) {
                fetch('/current_user')
                    .then(res => res.json())
                    .then(user => {
                        currentUsername = user.username;
                        document.getElementById("user-display").textContent = currentUsername;
                        document.getElementById("auth").style.display = "none";
                        document.getElementById("auth-header").style.display = "none";
                        document.getElementById("game").style.display = "block";

                        // Optional: Connect socket only after auth confirmed
                        if (typeof io !== 'undefined') {
                            socket.connect(); // move this here from global scope
                            socket.emit('join', { room, username: currentUsername }); // ensure join happens after connect
                        }
                    });
            } else {
                document.getElementById("auth-msg").textContent = data.message || "Login failed";
            }
        })
        .catch(err => {
            console.error('Login error:', err);
            document.getElementById("auth-msg").textContent = "Unexpected error. Try again.";
        });
}

function logout() {
    fetch('/logout', { method: 'GET' })
        .then(res => {
            if (res.status === 200) {
                currentUsername = "";
                document.getElementById("auth").style.display = "block";
                document.getElementById("auth-header").style.display = "block";
                document.getElementById("game").style.display = "none";
                document.getElementById("user-display").textContent = "";
                localStorage.removeItem("joinedRoom");
                socket.disconnect(); // disconnects from the server
            }
        });
}


function joinRoom() {
    const room = document.getElementById("room").value.trim();
    if (!currentUsername || !room) {
        showMessage("Username or room is missing.");
        return;
    }
    localStorage.setItem("joinedRoom", room);
    socket.emit('join', { room, username: currentUsername });
    document.getElementById("leave-room").style.display = "inline-block";
}

function initializeRoom() {
    const savedRoom = localStorage.getItem("joinedRoom");
    if (savedRoom) {
        document.getElementById("room").value = savedRoom;
        document.getElementById("leave-room").style.display = "inline-block";
    } else {
        document.getElementById("leave-room").style.display = "none";
    }
}

window.onload = () => {
    initializeRoom();
    // If user is already logged in, restore UI
    fetch('/current_user')
        .then(res => {
            if (res.status === 200) return res.json();
            throw new Error('Not logged in');
        })
        .then(user => {
            currentUsername = user.username;
            document.getElementById("user-display").textContent = currentUsername;
            document.getElementById("auth").style.display = "none";
            document.getElementById("auth-header").style.display = "none";
            document.getElementById("game").style.display = "block";
        })
        .catch(() => {
            document.getElementById("leave-room").style.display = "none";
        });
};

function startGame() {
    const room = document.getElementById("room").value.trim();
    socket.emit('start_game', { room });
}

function discardCard(card) {
    const room = document.getElementById("room").value.trim();
    socket.emit('discard_card', { room, card });
}

function removeCardButton(card) {
    const buttons = document.querySelectorAll(".card-button");
    buttons.forEach(btn => {
        if (btn.textContent === formatCard(card)) {
            btn.classList.add("fade-out");
            setTimeout(() => btn.remove(), 500); // match animation duration
        }
    });
}


socket.on('your_cards', (cards) => {
    const handDiv = document.getElementById("hand");
    handDiv.innerHTML = '';
    document.getElementById("score").textContent = '0';

    cards.forEach(card => {
        const btn = document.createElement("button");
        btn.textContent = formatCard(card);
        btn.classList.add("card-button");
        btn.onclick = () => {
            btn.disabled = true; // disable on click to prevent double sending
            discardCard(card);
        };
        handDiv.appendChild(btn);
    });
});


socket.on('card_discarded', data => {
    showMessage(`${data.username} discarded ${formatCard(data.card)} — Points: ${data.points}`);
    if (data.username === currentUsername) {
        stopTurnTimer();
        const scoreEl = document.getElementById("score");
        scoreEl.textContent = data.points;
        scoreEl.classList.add("animated");
        setTimeout(() => scoreEl.classList.remove("animated"), 600);

        removeCardButton(data.card);
    }
});


socket.on('your_turn', data => {
    const isMyTurn = data.username === currentUsername;
    document.querySelectorAll(".card-button").forEach(btn => {
        btn.disabled = !isMyTurn;
        btn.style.border = isMyTurn ? "2px solid #28a745" : "1px solid #ccc";
    });

    showMessage(`🔄 It's ${data.username}'s turn.`);

    if (isMyTurn) startTurnTimer();
    else stopTurnTimer();
});


socket.on('player_joined', data => showMessage(`✅ ${data.username} joined the room.`));
socket.on('player_left', data => showMessage(`❌ ${data.username} left the room.`));
socket.on('game_started', () => showMessage("🎮 Game started!"));
socket.on('error', data => showMessage(`⚠️ ${data.msg}`));

function showMessage(msg) {
    const msgBox = document.getElementById("messages");
    const p = document.createElement("p");
    p.textContent = msg;
    msgBox.appendChild(p);
}

socket.on('game_won', data => {
    const msg = `${data.username} wins with ${data.points} points! 🏆`;
    document.getElementById("winner-message").textContent = msg;
    document.getElementById("winner-modal").style.display = "block";
    showMessage(msg);

    // Show restart button only for host
    fetch('/current_user')
        .then(res => res.json())
        .then(user => {
            if (data.username === user.username) {
                document.getElementById("restart-game").style.display = "inline-block";
            }
        });
});



function closeModal() {
    document.getElementById("winner-modal").style.display = "none";
}

socket.on('update_scores', (scores) => {
    const list = document.getElementById('score-list');
    list.innerHTML = '';
    Object.values(scores).forEach(player => {
        const item = document.createElement('li');
        item.textContent = `${player.username}: ${player.points} pts`;
        list.appendChild(item);
    });
});

function leaveRoom() {
    localStorage.removeItem("joinedRoom");
    socket.disconnect(); // disconnects from the server
    location.reload();   // refresh the page
}

socket.on('turn_skipped', data => {
    showMessage(`⏱️ ${data.username}'s turn was skipped due to timeout.`);
});

let countdownInterval;

function startTurnTimer(duration = 30) {
    clearInterval(countdownInterval);
    const bar = document.getElementById('timer-bar');
    const container = document.getElementById('turn-timer');
    container.style.display = 'block';

    let timeLeft = duration;
    bar.style.width = '100%';
    bar.style.backgroundColor = '#28a745';  // Green

    countdownInterval = setInterval(() => {
        timeLeft--;
        const percent = (timeLeft / duration) * 100;
        bar.style.width = percent + '%';

        // Change color based on remaining time
        if (percent <= 33) {
            bar.style.backgroundColor = '#dc3545'; // Red
        } else if (percent <= 66) {
            bar.style.backgroundColor = '#fd7e14'; // Orange
        } else {
            bar.style.backgroundColor = '#28a745'; // Green
        }

        if (timeLeft <= 0) {
            clearInterval(countdownInterval);
            container.style.display = 'none';
        }
    }, 1000);
}


function stopTurnTimer() {
    clearInterval(countdownInterval);
    document.getElementById('turn-timer').style.display = 'none';
}

function toggleInstructions() {
    const instructions = document.getElementById('instructions');
    const button = event.target;

    if (instructions.style.display === 'none') {
        instructions.style.display = 'block';
        button.textContent = 'Hide Instructions';
    } else {
        instructions.style.display = 'none';
        button.textContent = 'Show Instructions';
    }
}
socket.on('room_info', ({ host, is_host }) => {
    document.getElementById('room-host').textContent = `Room Host: ${host}`;
    if (is_host) {
        document.getElementById('start-game').style.display = 'inline-block';
        // Show kick buttons or player management UI here
    }
});

function kickPlayer(username) {
    const room = localStorage.getItem("joinedRoom");
    socket.emit("kick_player", { room, username });
}

socket.on('room_stats', data => {
    showMessage(`👥 Players in room: ${data.players}/${data.max_players}`);
});
