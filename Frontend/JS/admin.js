// ============================================================================
// ADMIN PANEL - Gestión de usuarios y conversaciones
// ============================================================================

const API_URL = "https://4ylr6wwnpg.execute-api.us-east-2.amazonaws.com";
let accessToken = null;
let currentUserEmail = null;
let users = [];
let selectedUserId = null;

// ── INICIALIZACIÓN ────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', function() {
    // Recuperar token del localStorage
    accessToken = localStorage.getItem('access_token');
    currentUserEmail = localStorage.getItem('user_email');
    
    if (!accessToken || !currentUserEmail) {
        alert('No autorizado. Por favor inicia sesión.');
        window.location.href = '/index.html';
        return;
    }

    // Actualizar email en la topbar
    const emailElement = document.getElementById('admin-email');
    if (emailElement) {
        emailElement.textContent = currentUserEmail;
    }

    console.log('✅ Usuario autenticado:', currentUserEmail);

    // Cargar usuarios
    loadUsers();

    // Event listeners
    document.getElementById('logoutBtn')?.addEventListener('click', logout);
    document.getElementById('userSearchInput')?.addEventListener('input', filterUsers);
});

// ── OBTENER USUARIOS ──────────────────────────────────────────────────────
async function loadUsers() {
    try {
        console.log('📥 Cargando usuarios...');
        
        const response = await fetch(`${API_URL}/admin/users`, {
            method: 'GET',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        console.log('📊 Status:', response.status);

        if (response.status === 403) {
            alert('❌ No tienes permisos de administrador');
            window.location.href = '/chat.html';
            return;
        }

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Error cargando usuarios');
        }

        const data = await response.json();
        users = data.users || [];

        console.log('🎯 Usuarios cargados:', users.length);

        displayUsers(users);

    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error cargando usuarios: ' + error.message);
    }
}

// ── MOSTRAR USUARIOS EN LISTA ──────────────────────────────────────────────
function displayUsers(usersList) {
    const usersContainer = document.getElementById('usersContainer');
    
    if (!usersContainer) {
        console.warn('⚠️ Contenedor #usersContainer no encontrado');
        return;
    }

    if (usersList.length === 0) {
        usersContainer.innerHTML = '<div style="padding: 20px; text-align: center; color: #999;">No hay usuarios</div>';
        return;
    }

    usersContainer.innerHTML = usersList.map(user => `
        <div class="user-item" onclick="selectUser('${user.id}', '${user.email}')">
            <div class="user-avatar">👤</div>
            <div class="user-info">
                <div class="user-name">${user.username || user.email}</div>
                <div class="user-email">${user.email}</div>
            </div>
            <div class="user-status">
                <span class="badge ${user.role === 'admin' ? 'admin' : 'user'}">
                    ${user.role === 'admin' ? '⭐ Admin' : 'Usuario'}
                </span>
            </div>
        </div>
    `).join('');
}

// ── SELECCIONAR USUARIO ───────────────────────────────────────────────────
async function selectUser(userId, userEmail) {
    selectedUserId = userId;
    
    try {
        console.log('👤 Seleccionando usuario:', userEmail);

        const response = await fetch(`${API_URL}/admin/conversations/user/${userId}`, {
            method: 'GET',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Error cargando conversaciones');
        }

        const data = await response.json();
        const conversations = data.conversations || [];

        // Mostrar detalles del usuario
        displayUserDetails(userId, userEmail, conversations);

    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error cargando detalles: ' + error.message);
    }
}

// ── MOSTRAR DETALLES DEL USUARIO ──────────────────────────────────────────
function displayUserDetails(userId, userEmail, conversations) {
    const detailsContainer = document.getElementById('userDetailsContainer');
    
    if (!detailsContainer) {
        console.warn('⚠️ Contenedor #userDetailsContainer no encontrado');
        return;
    }

    const user = users.find(u => u.id === userId);
    const convCount = conversations.length;

    detailsContainer.innerHTML = `
        <div class="user-details-card">
            <div class="details-header">
                <div class="details-avatar">👤</div>
                <div class="details-info">
                    <h2>${user?.username || 'Usuario'}</h2>
                    <p class="details-email">📧 ${userEmail}</p>
                    <p class="details-role">👑 Rol: <strong>${user?.role === 'admin' ? 'Administrador' : 'Usuario Regular'}</strong></p>
                </div>
            </div>

            <div class="details-section">
                <h3>📊 Estadísticas</h3>
                <div class="stats-grid">
                    <div class="stat-card">
                        <div class="stat-number">${convCount}</div>
                        <div class="stat-label">Conversaciones</div>
                    </div>
                </div>
            </div>

            <div class="details-section">
                <h3>💬 Conversaciones</h3>
                <div class="conversations-list">
                    ${conversations.length > 0 ? conversations.map(conv => `
                        <div class="conversation-item">
                            <div class="conv-title">${conv.title || 'Sin título'}</div>
                            <div class="conv-date">${new Date(conv.created_at).toLocaleDateString('es-ES')}</div>
                            <button class="btn-small btn-delete" onclick="deleteConversation(${conv.id})">🗑️ Eliminar</button>
                        </div>
                    `).join('') : '<p class="empty-message">Sin conversaciones registradas</p>'}
                </div>
            </div>

            <div class="details-footer">
                <button class="btn btn-delete" onclick="deleteUser('${userId}', '${userEmail}')">
                    🗑️ Eliminar usuario
                </button>
            </div>
        </div>
    `;

    // Agregar estilos si no existen
    addDetailsStyles();
}

// ── AGREGAR ESTILOS PARA DETALLES ──────────────────────────────────────────
function addDetailsStyles() {
    if (document.getElementById('adminDetailsStyles')) return;

    const style = document.createElement('style');
    style.id = 'adminDetailsStyles';
    style.innerHTML = `
        .user-details-card {
            background: white;
            border-radius: 12px;
            padding: 24px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .details-header {
            display: flex;
            gap: 16px;
            margin-bottom: 24px;
            padding-bottom: 20px;
            border-bottom: 1px solid #eee;
        }

        .details-avatar {
            font-size: 48px;
            line-height: 1;
        }

        .details-info h2 {
            margin: 0 0 8px 0;
            color: #1A1208;
            font-size: 22px;
        }

        .details-email,
        .details-role {
            margin: 4px 0;
            color: #666;
            font-size: 14px;
        }

        .details-section {
            margin-bottom: 24px;
        }

        .details-section h3 {
            font-size: 16px;
            color: #1A1208;
            margin-bottom: 12px;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
            gap: 12px;
        }

        .stat-card {
            background: #f5f5f5;
            padding: 16px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #F5A623;
        }

        .stat-number {
            font-size: 28px;
            font-weight: bold;
            color: #F5A623;
        }

        .stat-label {
            font-size: 12px;
            color: #666;
            margin-top: 4px;
        }

        .conversations-list {
            background: #f9f9f9;
            border-radius: 8px;
            padding: 12px;
            max-height: 400px;
            overflow-y: auto;
        }

        .conversation-item {
            background: white;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 8px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-left: 3px solid #F5A623;
        }

        .conv-title {
            font-weight: 600;
            color: #1A1208;
            flex: 1;
        }

        .conv-date {
            font-size: 12px;
            color: #999;
            margin: 0 12px;
        }

        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            background: #f0f0f0;
            color: #666;
            transition: all 0.2s;
        }

        .btn-small:hover {
            background: #E8442A;
            color: white;
        }

        .empty-message {
            text-align: center;
            color: #999;
            padding: 20px;
            font-style: italic;
        }

        .details-footer {
            margin-top: 24px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            display: flex;
            justify-content: flex-end;
        }

        .btn-delete {
            background: #E8442A;
        }

        .btn-delete:hover {
            background: #c93a23;
        }
    `;

    document.head.appendChild(style);
}

// ── FILTRAR USUARIOS ──────────────────────────────────────────────────────
function filterUsers(event) {
    const query = event.target.value.toLowerCase();
    const filtered = users.filter(u => 
        (u.username || '').toLowerCase().includes(query) ||
        (u.email || '').toLowerCase().includes(query)
    );
    displayUsers(filtered);
}

// ── ELIMINAR CONVERSACIÓN ──────────────────────────────────────────────────
async function deleteConversation(convId) {
    if (!confirm('¿Estás seguro de que quieres eliminar esta conversación?')) return;

    try {
        const response = await fetch(`${API_URL}/admin/conversations/${convId}`, {
            method: 'DELETE',
            headers: {
                'access-token': accessToken,
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) throw new Error('Error eliminando conversación');

        alert('✅ Conversación eliminada');
        
        // Recargar detalles del usuario
        if (selectedUserId) {
            const user = users.find(u => u.id === selectedUserId);
            selectUser(selectedUserId, user.email);
        }
    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

// ── ELIMINAR USUARIO ──────────────────────────────────────────────────────
async function deleteUser(userId, userEmail) {
    if (!confirm(`¿Estás seguro de que quieres eliminar a ${userEmail}?`)) return;

    try {
        // No hay endpoint de DELETE para usuarios, solo mostrar mensaje
        alert('❌ La eliminación de usuarios aún no está implementada');
        // TODO: Implementar en backend cuando sea necesario

    } catch (error) {
        alert('❌ Error: ' + error.message);
    }
}

// ── LOGOUT ─────────────────────────────────────────────────────────────────
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_email');
    window.location.href = '/index.html';
}
