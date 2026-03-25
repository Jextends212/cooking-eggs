// ============================================================================
// CHAT - Funciones de mensajería
// ============================================================================

const API_URL = "https://4ylr6wwnpg.execute-api.us-east-2.amazonaws.com";
let accessToken = null;
let currentConversationId = null;
let conversationHistory = [];

// ── INICIALIZACIÓN ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    accessToken = localStorage.getItem('access_token');
    
    if (!accessToken) {
        alert('No autorizado. Por favor inicia sesión.');
        window.location.href = '/index.html';
        return;
    }

    console.log('✅ Usuario autenticado en chat');

    // Event listeners
    document.getElementById('sendButton')?.addEventListener('click', sendMessage);
    document.getElementById('messageInput')?.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    document.getElementById('logoutBtn')?.addEventListener('click', logout);
    document.getElementById('newChatBtn')?.addEventListener('click', newConversation);

    // Cargar historial
    loadHistory();
});

// ── ENVIAR MENSAJE ─────────────────────────────────────────────────────────
async function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const message = messageInput?.value.trim() || '';

    if (!message) return;

    try {
        const messagesContainer = document.getElementById('messagesContainer');
        
        // Agregar mensaje del usuario a la UI
        if (messagesContainer) {
            const userMessageDiv = document.createElement('div');
            userMessageDiv.className = 'message user-message';
            userMessageDiv.innerHTML = `<div class="message-content">${escapeHtml(message)}</div>`;
            messagesContainer.appendChild(userMessageDiv);
        }

        messageInput.value = '';
        messageInput.disabled = true;

        const response = await fetch(`${API_URL}/chat`, {
            method: 'POST',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                access_token: accessToken,
                message: message,
                conversation_id: currentConversationId
            })
        });

        if (!response.ok) {
            throw new Error('Error enviando mensaje');
        }

        const data = await response.json();

        // Guardar conversation_id si es nueva
        if (!currentConversationId && data.conversation_id) {
            currentConversationId = data.conversation_id;
        }

        // Mostrar respuesta del asistente
        if (messagesContainer && data.response) {
            const assistantMessageDiv = document.createElement('div');
            assistantMessageDiv.className = 'message assistant-message';
            assistantMessageDiv.innerHTML = `<div class="message-content">${escapeHtml(data.response)}</div>`;
            messagesContainer.appendChild(assistantMessageDiv);
        }

        // Scroll al final
        if (messagesContainer) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error enviando mensaje: ' + error.message);
    } finally {
        messageInput.disabled = false;
        messageInput.focus();
    }
}

// ── CARGAR HISTORIAL DE CONVERSACIONES ────────────────────────────────────
async function loadHistory() {
    try {
        const response = await fetch(`${API_URL}/history`, {
            method: 'GET',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error cargando historial');
        }

        const data = await response.json();
        conversationHistory = data.conversations || [];

        displayHistory(conversationHistory);

    } catch (error) {
        console.error('❌ Error cargando historial:', error);
    }
}

// ── MOSTRAR HISTORIAL ──────────────────────────────────────────────────────
function displayHistory(conversations) {
    const historyContainer = document.getElementById('historyContainer');
    
    if (!historyContainer) return;

    if (conversations.length === 0) {
        historyContainer.innerHTML = '<p style="color: #999; padding: 20px; text-align: center;">Sin conversaciones</p>';
        return;
    }

    historyContainer.innerHTML = conversations.map(conv => `
        <div class="history-item" onclick="loadConversation(${conv.id})">
            <div class="history-title">${conv.title || 'Conversación'}</div>
            <div class="history-date">${new Date(conv.created_at).toLocaleDateString('es-ES')}</div>
            <button class="btn-delete" onclick="deleteConversation(event, ${conv.id})">🗑️</button>
        </div>
    `).join('');
}

// ── CARGAR CONVERSACIÓN ────────────────────────────────────────────────────
async function loadConversation(conversationId) {
    try {
        currentConversationId = conversationId;

        const response = await fetch(`${API_URL}/history/${conversationId}`, {
            method: 'GET',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error cargando conversación');
        }

        const data = await response.json();
        const messages = data.messages || [];

        // Mostrar mensajes
        displayMessages(messages);

    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error cargando conversación');
    }
}

// ── MOSTRAR MENSAJES ───────────────────────────────────────────────────────
function displayMessages(messages) {
    const messagesContainer = document.getElementById('messagesContainer');
    
    if (!messagesContainer) return;

    messagesContainer.innerHTML = messages.map(msg => `
        <div class="message ${msg.role}-message">
            <div class="message-content">${escapeHtml(msg.content)}</div>
        </div>
    `).join('');

    // Scroll al final
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

// ── NUEVA CONVERSACIÓN ────────────────────────────────────────────────────
function newConversation() {
    currentConversationId = null;
    
    const messagesContainer = document.getElementById('messagesContainer');
    if (messagesContainer) {
        messagesContainer.innerHTML = '<div style="text-align: center; color: #999; padding: 40px;">Inicia un nuevo chat...</div>';
    }

    const messageInput = document.getElementById('messageInput');
    if (messageInput) {
        messageInput.value = '';
        messageInput.focus();
    }
}

// ── ELIMINAR CONVERSACIÓN ──────────────────────────────────────────────────
async function deleteConversation(event, conversationId) {
    event.stopPropagation();
    
    if (!confirm('¿Eliminar esta conversación?')) return;

    try {
        const response = await fetch(`${API_URL}/history/${conversationId}`, {
            method: 'DELETE',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error eliminando conversación');
        }

        console.log('✅ Conversación eliminada');
        loadHistory();

        if (currentConversationId === conversationId) {
            newConversation();
        }

    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error eliminando conversación');
    }
}

// ── LOGOUT ─────────────────────────────────────────────────────────────────
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_email');
    localStorage.removeItem('username');
    window.location.href = '/index.html';
}

// ── ESCAPE HTML ────────────────────────────────────────────────────────────
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
