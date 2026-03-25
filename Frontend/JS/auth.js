// ============================================================================
// AUTENTICACIÓN - Login, Registro, Reset de Contraseña
// ============================================================================

const API_URL = "https://4ylr6wwnpg.execute-api.us-east-2.amazonaws.com";

// ── LOGIN ──────────────────────────────────────────────────────────────────
async function handleLogin(event) {
    event.preventDefault();

    const username = document.getElementById('loginUsername')?.value || '';
    const password = document.getElementById('loginPassword')?.value || '';

    if (!username || !password) {
        alert('Por favor completa usuario y contraseña');
        return;
    }

    try {
        const btn = event.target.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.textContent = 'Iniciando sesión...';

        const response = await fetch(`${API_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'login',
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok && data.access_token) {
            // Guardar en localStorage
            localStorage.setItem('access_token', data.access_token);
            localStorage.setItem('user_email', data.email || username);
            localStorage.setItem('username', data.username || username);
            localStorage.setItem('is_admin', data.is_admin || false);

            console.log('✅ Login exitoso - Admin:', data.is_admin);

            // Redirigir según rol
            if (data.is_admin) {
                window.location.href = '/admin.html';
            } else {
                window.location.href = '/chat.html';
            }
        } else {
            alert(data.error || 'Error en el login');
            btn.disabled = false;
            btn.textContent = 'Iniciar sesión';
        }
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error de conexión');
        event.target.querySelector('button[type="submit"]').disabled = false;
    }
}

// ── REGISTER ───────────────────────────────────────────────────────────────
async function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('registerName')?.value || '';
    const email = document.getElementById('registerEmail')?.value || '';
    const username = document.getElementById('registerUsername')?.value || '';
    const password = document.getElementById('registerPassword')?.value || '';

    if (!name || !email || !username || !password) {
        alert('Por favor completa todos los campos');
        return;
    }

    if (password.length < 8) {
        alert('La contraseña debe tener mínimo 8 caracteres');
        return;
    }

    try {
        const btn = event.target.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.textContent = 'Registrando...';

        const response = await fetch(`${API_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'register',
                name: name,
                email: email,
                username: username,
                password: password
            })
        });

        const data = await response.json();

        if (response.ok) {
            alert('✅ Registro exitoso. Ahora inicia sesión');
            // Limpiar formulario
            event.target.reset();
            // Cambiar a tab de login
            if (document.getElementById('loginTab')) {
                document.getElementById('loginTab').click();
            }
        } else {
            alert(data.error || 'Error en el registro');
        }

        btn.disabled = false;
        btn.textContent = 'Registrarse';
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error de conexión');
        event.target.querySelector('button[type="submit"]').disabled = false;
    }
}

// ── FORGOT PASSWORD: SOLICITAR CÓDIGO ──────────────────────────────────────
async function requestReset() {
    const email = document.getElementById('forgotEmail')?.value.trim() || '';

    if (!email) {
        alert('Por favor ingresa tu email');
        return;
    }

    try {
        const btn = event.target;
        btn.disabled = true;
        btn.textContent = 'Enviando...';

        const response = await fetch(`${API_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'forgot_password',
                username: email
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('forgotSection')?.classList.add('hide');
            document.getElementById('confirmSection')?.classList.remove('hide');
            document.getElementById('successMessage')?.innerHTML = 
                '<div class="message success">✅ Email enviado. Revisa tu correo para el código</div>';
        } else {
            alert(data.error || 'Error al enviar el código');
        }

        btn.disabled = false;
        btn.textContent = 'Enviar código 📧';
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error de conexión');
        event.target.disabled = false;
        event.target.textContent = 'Enviar código 📧';
    }
}

// ── CONFIRMAR RESET: CAMBIAR CONTRASEÑA ────────────────────────────────────
async function confirmReset() {
    const email = document.getElementById('forgotEmail')?.value.trim() || '';
    const code = document.getElementById('resetCode')?.value.trim() || '';
    const pwd1 = document.getElementById('newPassword')?.value || '';
    const pwd2 = document.getElementById('confirmPassword')?.value || '';

    if (!email || !code || !pwd1 || !pwd2) {
        alert('Por favor completa todos los campos');
        return;
    }

    if (pwd1 !== pwd2) {
        alert('Las contraseñas no coinciden');
        return;
    }

    if (pwd1.length < 8) {
        alert('La contraseña debe tener mínimo 8 caracteres');
        return;
    }

    try {
        const btn = event.target;
        btn.disabled = true;
        btn.textContent = 'Procesando...';

        const response = await fetch(`${API_URL}/auth`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                action: 'reset_password',
                username: email,
                code: code,  // El código es en realidad el token
                new_password: pwd1
            })
        });

        const data = await response.json();

        if (response.ok) {
            document.getElementById('confirmSection')?.classList.add('hide');
            document.getElementById('successSection')?.classList.remove('hide');
            
            // Redirigir al index después de 3 segundos
            setTimeout(() => {
                window.location.href = '/';
            }, 3000);
        } else {
            alert(data.error || 'Error al cambiar la contraseña');
        }

        btn.disabled = false;
        btn.textContent = 'Cambiar contraseña ✅';
    } catch (error) {
        console.error('❌ Error:', error);
        alert('Error de conexión');
        event.target.disabled = false;
        event.target.textContent = 'Cambiar contraseña ✅';
    }
}

// ── ALTERNAR SECCIONES ────────────────────────────────────────────────────
function toggleSections() {
    document.getElementById('forgotSection')?.classList.toggle('hide');
    document.getElementById('confirmSection')?.classList.toggle('hide');
    document.getElementById('successMessage')?.innerHTML = '';
}

// ── LOGOUT ─────────────────────────────────────────────────────────────────
function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user_email');
    localStorage.removeItem('username');
    localStorage.removeItem('is_admin');
    window.location.href = '/index.html';
}

// ── VERIFICAR SESIÓN ───────────────────────────────────────────────────────
function checkSession() {
    const token = localStorage.getItem('access_token');
    return !!token;
}

// ── OBTENER TOKEN ──────────────────────────────────────────────────────────
function getAccessToken() {
    return localStorage.getItem('access_token');
}
