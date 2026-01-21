// NCM Video Service - Login Page JavaScript
// 访问密码登录页面脚本

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
}

function toggleTheme() {
    const html = document.documentElement;
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
}

function updateThemeIcon(theme) {
    const sunIcon = document.getElementById('sunIcon');
    const moonIcon = document.getElementById('moonIcon');
    if (theme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }
}

// Mouse glow effect for dark mode
if (window.matchMedia('(pointer: fine)').matches) {
    document.addEventListener('mousemove', (e) => {
        const x = (e.clientX / window.innerWidth) * 100;
        const y = (e.clientY / window.innerHeight) * 100;
        document.body.style.setProperty('--mouse-x', x + '%');
        document.body.style.setProperty('--mouse-y', y + '%');
    });
}

// Form handling
document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('loginForm');
    const passwordInput = document.getElementById('password');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = document.getElementById('btnText');
    const errorMessage = document.getElementById('errorMessage');

    initTheme();
    passwordInput.focus();

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const password = passwordInput.value.trim();
        if (!password) {
            showError('请输入密码');
            return;
        }

        submitBtn.disabled = true;
        btnText.innerHTML = '<span class="loading"></span>验证中...';
        hideError();

        try {
            const response = await fetch('/auth/verify', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `password=${encodeURIComponent(password)}`
            });

            const data = await response.json();

            if (data.code === 200) {
                if (data.hash) {
                    localStorage.setItem('access_hash', data.hash);
                }
                
                btnText.innerHTML = '<span class="success-icon">✓</span>验证成功';
                setTimeout(() => {
                    window.location.href = '/';
                }, 600);
            } else {
                showError(data.message || '密码错误，请重试');
                submitBtn.disabled = false;
                btnText.textContent = '进入系统';
                passwordInput.value = '';
                passwordInput.focus();
            }
        } catch (error) {
            showError('网络错误，请稍后重试');
            submitBtn.disabled = false;
            btnText.textContent = '进入系统';
        }
    });

    function showError(message) {
        errorMessage.textContent = '✕ ' + message;
        errorMessage.style.display = 'block';
    }

    function hideError() {
        errorMessage.style.display = 'none';
    }

    passwordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            form.dispatchEvent(new Event('submit'));
        }
    });
});
