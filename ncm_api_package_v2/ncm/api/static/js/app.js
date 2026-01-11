// NCM Video Service - Main Application JavaScript
// 网易云音乐视频服务主应用脚本

// Global State
let currentResults = [];
let currentMode = 'search';
let currentPage = 1;
let currentKeywords = '';
const pageSize = 10;
let isSearching = false;
let qrCheckInterval = null;
let smsSendCountdown = 0;
let currentPlaylistSongs = [];
let isDragging = false;
let dragOffsetX = 0;
let dragOffsetY = 0;

// ============ Theme Management ============
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    
    if (newTheme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    } else {
        sunIcon.style.display = 'block';
        moonIcon.style.display = 'none';
    }
}

function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const sunIcon = document.querySelector('.sun-icon');
    const moonIcon = document.querySelector('.moon-icon');
    
    if (savedTheme === 'dark') {
        sunIcon.style.display = 'none';
        moonIcon.style.display = 'block';
    }
}

// Mouse glow effect for dark mode
let mouseX = 0, mouseY = 0;

document.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth) * 100;
    mouseY = (e.clientY / window.innerHeight) * 100;
    
    document.documentElement.style.setProperty('--mouse-x', mouseX + '%');
    document.documentElement.style.setProperty('--mouse-y', mouseY + '%');
});

// ============ Mode Switching ============
function switchMode(mode) {
    currentMode = mode;
    const btnSearch = document.getElementById('btnSearch');
    const btnDirect = document.getElementById('btnDirect');
    const btnPlaylist = document.getElementById('btnPlaylist');
    const btnLogin = document.getElementById('btnLogin');
    const searchCard = document.getElementById('searchCard');
    const playlistCard = document.getElementById('playlistCard');
    const loginCard = document.getElementById('loginCard');
    const searchInput = document.getElementById('searchInput');
    const actionButton = document.getElementById('actionButton');
    const resultsDiv = document.getElementById('results');
    const tabs = document.querySelector('.tabs');
    
    btnSearch.classList.remove('active');
    btnDirect.classList.remove('active');
    btnPlaylist.classList.remove('active');
    btnLogin.classList.remove('active');
    
    searchCard.style.display = 'none';
    playlistCard.style.display = 'none';
    loginCard.style.display = 'none';
    resultsDiv.style.display = 'none';
    
    if (mode === 'search') {
        btnSearch.classList.add('active');
        searchCard.style.display = 'block';
        tabs.setAttribute('data-active', 'search');
        searchInput.placeholder = '输入歌曲名或歌手名...';
        actionButton.innerHTML = '查找视频';
        searchInput.type = 'text';
        searchInput.value = '';
        searchInput.focus();
    } else if (mode === 'direct') {
        btnDirect.classList.add('active');
        searchCard.style.display = 'block';
        tabs.setAttribute('data-active', 'direct');
        searchInput.placeholder = '输入歌曲ID或网易云音乐链接 (例如: 483242395 或 https://music.163.com/song?id=483242395)';
        actionButton.innerHTML = '播放歌曲';
        searchInput.type = 'text';
        searchInput.value = '';
        searchInput.focus();
    } else if (mode === 'playlist') {
        btnPlaylist.classList.add('active');
        playlistCard.style.display = 'block';
        tabs.setAttribute('data-active', 'playlist');
        document.getElementById('playlistInput').focus();
    } else if (mode === 'login') {
        btnLogin.classList.add('active');
        loginCard.style.display = 'block';
        tabs.setAttribute('data-active', 'login');
        checkLoginStatus();
    }
}

// ============ Search & Play Functions ============
async function handleAction() {
    if (currentMode === 'search') {
        await searchSongs();
    } else {
        await directPlay();
    }
}

async function directPlay() {
    const input = document.getElementById('searchInput').value.trim();
    if (!input) {
        alert('请输入歌曲ID或网易云音乐链接');
        return;
    }
    
    let songId = input;
    const urlPatterns = [
        /[?&]id=(\d+)/,
        /song\/(\d+)/,
        /^(\d+)$/
    ];
    
    let matched = false;
    for (const pattern of urlPatterns) {
        const match = input.match(pattern);
        if (match) {
            songId = match[1];
            matched = true;
            break;
        }
    }
    
    if (!matched || isNaN(songId)) {
        alert('无法识别的格式。\n\n支持格式：\n- 纯数字ID: 483242395\n- 完整URL: https://music.163.com/song?id=483242395\n- 简化URL: music.163.com/song?id=483242395');
        return;
    }
    
    await playSong(parseInt(songId), 'Song ID: ' + songId, '');
}

async function searchSongs(page = 1) {
    const keywords = document.getElementById('searchInput').value.trim();
    if (!keywords) {
        alert('请输入歌曲名或歌手名');
        return;
    }
    
    const videoElement = document.getElementById('video');
    const floatingVideoDiv = document.getElementById('floatingVideo');
    const floatingVideoElement = document.getElementById('floatingVideoPlayer');
    const floatingVideoTitle = document.getElementById('floatingVideoTitle');
    
    if (videoElement && videoElement.src && !videoElement.paused && !videoElement.ended) {
        floatingVideoElement.src = videoElement.src;
        floatingVideoElement.currentTime = videoElement.currentTime;
        floatingVideoTitle.textContent = videoElement.dataset.currentTitle || '正在播放';
        floatingVideoDiv.style.display = 'block';
        floatingVideoElement.pause();
        
        videoElement.pause();
        videoElement.src = '';
        document.getElementById('videoPlayer').style.display = 'none';
    }
    
    if (isSearching) return;
    isSearching = true;
    currentKeywords = keywords;
    currentPage = page;
    
    const resultsDiv = document.getElementById('results');
    const songListDiv = document.getElementById('songList');
    const paginationDiv = document.getElementById('pagination');
    
    resultsDiv.style.display = 'block';
    songListDiv.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Searching...</p></div>';
    paginationDiv.style.display = 'none';
    
    try {
        const offset = (page - 1) * pageSize;
        let data;
        
        try {
            const response = await fetch(`/search?keywords=${encodeURIComponent(keywords)}&limit=${pageSize}&offset=${offset}`);
            if (!response.ok) throw new Error("API not available");
            data = await response.json();
        } catch (e) {
            console.warn("API fetch failed, utilizing mock data for preview:", e);
            await new Promise(r => setTimeout(r, 800));
            data = {
                code: 200,
                songs: Array.from({length: 5}, (_, i) => ({
                    id: 1000 + i,
                    name: `${keywords} - Demo Song ${i + 1}`,
                    artist: 'Demo Artist',
                    mvId: i % 2 === 0 ? 123 : 0,
                    fee: i % 3 === 0 ? 1 : 0,
                    picUrl: 'https://p2.music.126.net/6y-UleORITEDbvrOLV0Q8A==/5639395138885805.jpg'
                }))
            };
        }
        
        if (data.code === 200 && data.songs && data.songs.length > 0) {
            currentResults = data.songs;
            displayResults(currentResults);
            paginationDiv.style.display = 'flex';
            updatePagination(data.songs.length);
        } else {
            songListDiv.innerHTML = '<div class="loading-state"><p>No results found.</p></div>';
        }
    } catch (error) {
        songListDiv.innerHTML = `<div class="card" style="color: red; padding: 20px; text-align: center;">Error: ${error.message}</div>`;
    } finally {
        isSearching = false;
    }
}

function updatePagination(resultCount) {
    const btnPrev = document.getElementById('btnPrev');
    const btnNext = document.getElementById('btnNext');
    const pageInfo = document.getElementById('pageInfo');
    
    pageInfo.textContent = `${currentPage}`;
    btnPrev.disabled = currentPage === 1;
    btnNext.disabled = resultCount < pageSize;
}

async function prevPage() {
    if (currentPage > 1) {
        await searchSongs(currentPage - 1);
    }
}

async function nextPage() {
    await searchSongs(currentPage + 1);
}

function displayResults(songs) {
    const songListDiv = document.getElementById('songList');
    const resultCountSpan = document.getElementById('resultCount');
    
    resultCountSpan.textContent = `${songs.length} results`;
    
    const html = songs.map(song => {
        const hasMv = song.mvId && song.mvId > 0;
        const fee = song.fee || 0;
        
        return `
            <div class="song-item card" style="margin-bottom: 0;" onclick="selectAndPlay(${song.id}, '${escapeHtml(song.name)}', '${escapeHtml(song.artist)}')">
                <img src="${song.picUrl}?param=60y60" class="song-cover" alt="cover">
                <div class="song-info">
                    <div class="song-name">
                        ${song.name}
                        ${hasMv ? '<span class="badge badge-mv">MV</span>' : ''}
                        ${fee === 1 ? '<span class="badge badge-vip">VIP</span>' : ''}
                    </div>
                    <div class="song-meta">${song.artist}</div>
                </div>
                <div class="play-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg"><path d="M8 5V19L19 12L8 5Z"/></svg>
                </div>
            </div>
        `;
    }).join('');
    
    songListDiv.innerHTML = html;
}

function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/'/g, "\\'").replace(/"/g, '&quot;');
}

async function selectAndPlay(id, name, artist) {
    await playSong(id, name, artist);
}

async function playSong(id, name, artist) {
    const videoPlayerDiv = document.getElementById('videoPlayer');
    const videoElement = document.getElementById('video');
    
    const useMv = document.getElementById('optionMv').checked;
    const useGpu = document.getElementById('optionGpu').checked;
    const level = document.getElementById('optionLevel').value;
    
    const params = new URLSearchParams({
        id: id,
        mv: useMv ? '1' : '0',
        use_gpu: useGpu ? '1' : '0',
        level: level
    });
    
    const accessHash = localStorage.getItem('access_hash') || getCookie('access_password');
    if (accessHash) {
        params.append('access_hash', accessHash);
    }
    
    const videoUrl = `/video?${params.toString()}`;
    const fullApiUrl = window.location.origin + videoUrl;
    
    document.getElementById('apiUrl').value = fullApiUrl;
    
    videoPlayerDiv.style.display = 'block';
    
    // 先暂停并清空当前播放，防止重复播放
    videoElement.pause();
    videoElement.removeAttribute('src');
    videoElement.load();
    
    // 设置新的源
    videoElement.src = videoUrl;
    videoElement.dataset.currentTitle = `${name} - ${artist}`;
    
    videoElement.onerror = () => {
        console.log("Video load failed (expected in preview mode).");
    };
    
    videoElement.load();
    videoPlayerDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function copyApiUrl() {
    const apiUrlInput = document.getElementById('apiUrl');
    apiUrlInput.select();
    document.execCommand('copy');
    
    const btn = event.currentTarget || event.target;
    const originalText = btn.textContent;
    btn.textContent = 'Copied!';
    btn.style.background = '#000';
    btn.style.color = '#fff';
    
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
        btn.style.color = '';
    }, 2000);
}

// ============ Floating Video Functions ============
function toggleFloatingVideo() {
    const floatingVideo = document.getElementById('floatingVideo');
    floatingVideo.classList.toggle('minimized');
}

function closeFloatingVideo() {
    const floatingVideo = document.getElementById('floatingVideo');
    const floatingVideoElement = document.getElementById('floatingVideoPlayer');
    
    floatingVideoElement.pause();
    floatingVideoElement.src = '';
    floatingVideo.style.display = 'none';
}

// Floating video drag functionality
function initFloatingVideoDrag() {
    const floatingVideo = document.getElementById('floatingVideo');
    const floatingHeader = floatingVideo.querySelector('.floating-video-header');

    floatingHeader.addEventListener('mousedown', function(e) {
        if (e.target.classList.contains('floating-control-btn')) return;
        
        isDragging = true;
        const rect = floatingVideo.getBoundingClientRect();
        dragOffsetX = e.clientX - rect.left;
        dragOffsetY = e.clientY - rect.top;
        
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isDragging) return;
        
        const newX = e.clientX - dragOffsetX;
        const newY = e.clientY - dragOffsetY;
        
        const maxX = window.innerWidth - floatingVideo.offsetWidth;
        const maxY = window.innerHeight - floatingVideo.offsetHeight;
        
        floatingVideo.style.left = Math.max(0, Math.min(newX, maxX)) + 'px';
        floatingVideo.style.bottom = 'auto';
        floatingVideo.style.top = Math.max(0, Math.min(newY, maxY)) + 'px';
    });

    document.addEventListener('mouseup', function() {
        if (isDragging) {
            isDragging = false;
            document.body.style.userSelect = '';
        }
    });
}

// ============ Login Functions ============
async function checkLoginStatus() {
    const statusDiv = document.getElementById('loginStatus');
    const statusText = document.getElementById('loginStatusText');
    const logoutSection = document.getElementById('logoutSection');
    
    try {
        const response = await fetch('/user/info');
        const data = await response.json();
        
        if (data.code === 200 && data.profile) {
            statusDiv.className = 'login-status success';
            statusText.textContent = `✅ 已登录：${data.profile.nickname} (UID: ${data.account.id})`;
            logoutSection.style.display = 'block';
            console.log('登录状态已更新：', data.profile.nickname);
            return true;
        } else {
            statusDiv.className = 'login-status';
            statusText.textContent = '未登录，请选择登录方式';
            logoutSection.style.display = 'none';
            return false;
        }
    } catch (error) {
        console.error('检查登录状态失败：', error);
        statusDiv.className = 'login-status';
        statusText.textContent = '未登录，请选择登录方式';
        logoutSection.style.display = 'none';
        return false;
    }
}

function selectLoginMethod(method, event) {
    document.getElementById('qrLoginSection').style.display = 'none';
    document.getElementById('smsLoginSection').style.display = 'none';
    document.getElementById('passwordLoginSection').style.display = 'none';
    document.getElementById('cookieLoginSection').style.display = 'none';
    
    document.querySelectorAll('.login-method-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    
    if (event && event.target) {
        event.target.classList.add('active');
    }
    
    if (method === 'qr') {
        document.getElementById('qrLoginSection').style.display = 'block';
        startQRLogin();
    } else if (method === 'sms') {
        document.getElementById('smsLoginSection').style.display = 'block';
    } else if (method === 'password') {
        document.getElementById('passwordLoginSection').style.display = 'block';
    } else if (method === 'cookie') {
        document.getElementById('cookieLoginSection').style.display = 'block';
    }
}

async function startQRLogin() {
    const qrImage = document.getElementById('qrCodeImage');
    const qrTip = document.getElementById('qrTip');
    
    try {
        qrTip.textContent = '正在生成二维码...';
        
        if (qrCheckInterval) {
            clearInterval(qrCheckInterval);
        }
        
        const keyResponse = await fetch('/login/qr/key');
        const keyData = await keyResponse.json();
        
        if (keyData.code !== 200) {
            throw new Error('获取二维码Key失败');
        }
        
        const qrKey = keyData.unikey;
        
        const qrResponse = await fetch(`/login/qr/create?key=${qrKey}`);
        const qrData = await qrResponse.json();
        
        if (qrData.code !== 200) {
            throw new Error('生成二维码失败');
        }
        
        qrImage.src = qrData.qrimg;
        qrTip.textContent = '请使用网易云音乐APP扫码登录';
        
        let checkCount = 0;
        const maxChecks = 60;
        
        qrCheckInterval = setInterval(async () => {
            checkCount++;
            
            if (checkCount > maxChecks) {
                clearInterval(qrCheckInterval);
                qrTip.textContent = '⏱️ 登录超时，请刷新二维码重试';
                qrTip.style.color = '#ef4444';
                return;
            }
            
            try {
                const checkResponse = await fetch(`/login/qr/check?key=${qrKey}`);
                const checkData = await checkResponse.json();
                
                if (checkData.code === 800) {
                    clearInterval(qrCheckInterval);
                    qrTip.textContent = '❌ 二维码已过期，请刷新';
                    qrTip.style.color = '#ef4444';
                } else if (checkData.code === 801) {
                    const remaining = maxChecks - checkCount;
                    qrTip.textContent = `⌛ 等待扫码中... (${remaining * 2}秒后超时)`;
                    qrTip.style.color = 'var(--text-secondary)';
                } else if (checkData.code === 802) {
                    qrTip.textContent = '📱 已扫码，请在手机上确认...';
                    qrTip.style.color = '#0070f3';
                } else if (checkData.code === 803) {
                    clearInterval(qrCheckInterval);
                    qrTip.textContent = '✅ 登录成功！正在更新状态...';
                    qrTip.style.color = '#10b981';
                    await checkLoginStatus();
                    qrTip.textContent = '✅ 登录成功！';
                }
            } catch (error) {
                console.error('检查二维码状态失败:', error);
            }
        }, 2000);
        
    } catch (error) {
        qrTip.textContent = '❌ ' + error.message;
        qrTip.style.color = '#ef4444';
    }
}

async function sendSMSCode() {
    const phone = document.getElementById('smsPhone').value.trim();
    const sendBtn = document.getElementById('smsSendBtn');
    
    if (!phone || phone.length !== 11) {
        alert('请输入有效的11位手机号');
        return;
    }
    
    if (smsSendCountdown > 0) {
        return;
    }
    
    try {
        sendBtn.disabled = true;
        const response = await fetch(`/login/sms/send?phone=${phone}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.code === 200) {
            alert('验证码已发送，请查收短信');
            smsSendCountdown = 60;
            
            const interval = setInterval(() => {
                smsSendCountdown--;
                sendBtn.textContent = `${smsSendCountdown}秒后重试`;
                
                if (smsSendCountdown <= 0) {
                    clearInterval(interval);
                    sendBtn.textContent = '发送验证码';
                    sendBtn.disabled = false;
                }
            }, 1000);
        } else {
            alert('发送失败：' + (data.message || '未知错误'));
            sendBtn.disabled = false;
        }
    } catch (error) {
        alert('发送失败：' + error.message);
        sendBtn.disabled = false;
    }
}

async function verifySMSLogin() {
    const phone = document.getElementById('smsPhone').value.trim();
    const captcha = document.getElementById('smsCaptcha').value.trim();
    
    if (!phone || !captcha) {
        alert('请输入手机号和验证码');
        return;
    }
    
    try {
        const response = await fetch(`/login/sms/verify?phone=${phone}&captcha=${captcha}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.code === 200) {
            const success = await checkLoginStatus();
            if (success) {
                alert('✅ 登录成功！Cookie 已同步到所有线程');
            } else {
                alert('登录成功，但状态更新失败，请刷新页面');
            }
        } else {
            alert('登录失败：' + (data.message || '验证码错误'));
        }
    } catch (error) {
        alert('登录失败：' + error.message);
    }
}

async function passwordLogin() {
    const phone = document.getElementById('pwdPhone').value.trim();
    const password = document.getElementById('pwdPassword').value.trim();
    
    if (!phone || !password) {
        alert('请输入手机号和密码');
        return;
    }
    
    try {
        const response = await fetch(`/login/password?phone=${phone}&password=${password}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.code === 200) {
            const success = await checkLoginStatus();
            if (success) {
                alert('✅ 登录成功！Cookie 已同步到所有线程');
            } else {
                alert('登录成功，但状态更新失败，请刷新页面');
            }
        } else {
            alert('登录失败：' + (data.message || '账号或密码错误'));
        }
    } catch (error) {
        alert('登录失败：' + error.message);
    }
}

async function importCookie() {
    const cookie = document.getElementById('cookieInput').value.trim();
    
    if (!cookie || cookie.length < 10) {
        alert('请输入有效的Cookie');
        return;
    }
    
    try {
        const response = await fetch(`/cookie/import?cookie=${encodeURIComponent(cookie)}`, { method: 'POST' });
        const data = await response.json();
        
        if (data.code === 200) {
            const success = await checkLoginStatus();
            if (success) {
                alert('✅ Cookie 导入成功！已同步到所有线程');
            } else {
                alert('Cookie 已导入，但状态更新失败，请刷新页面');
            }
        } else {
            alert('导入失败：' + (data.message || '未知错误'));
        }
    } catch (error) {
        alert('导入失败：' + error.message);
    }
}

async function logout() {
    if (!confirm('确定要退出登录吗？')) {
        return;
    }
    
    try {
        const response = await fetch('/logout');
        const data = await response.json();
        
        if (data.code === 200 || data.code === -1) {
            alert('已退出登录');
            checkLoginStatus();
        } else {
            alert('退出失败：' + (data.message || '未知错误'));
        }
    } catch (error) {
        alert('退出失败：' + error.message);
    }
}

// ============ Access Password Management ============
async function changeAccessPassword() {
    const currentPassword = document.getElementById('currentPasswordForChange').value.trim();
    const newPassword = document.getElementById('newPasswordInput').value.trim();
    const confirmPassword = document.getElementById('confirmPasswordInput').value.trim();
    const resultDiv = document.getElementById('passwordChangeResult');
    const messageP = document.getElementById('passwordChangeMessage');
    const newHashDisplay = document.getElementById('newHashDisplay');
    const newHashValue = document.getElementById('newHashValue');
    
    if (!currentPassword) {
        alert('请输入当前访问密码');
        return;
    }
    
    if (!newPassword) {
        alert('请输入新密码');
        return;
    }
    
    if (newPassword.length < 6) {
        alert('新密码长度至少6位');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        alert('两次输入的新密码不一致');
        return;
    }
    
    if (currentPassword === newPassword) {
        alert('新密码不能与当前密码相同');
        return;
    }
    
    if (!confirm('⚠️ 确定要修改访问密码吗？\n\n修改后，所有用户（包括您）都需要使用新密码重新登录系统。')) {
        return;
    }
    
    try {
        const formData = new FormData();
        formData.append('current_password', currentPassword);
        formData.append('new_password', newPassword);
        
        const response = await fetch('/auth/change-password', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        
        if (data.code === 200) {
            messageP.textContent = '✅ 访问密码修改成功！';
            messageP.style.color = '#059669';
            resultDiv.style.background = '#d1fae5';
            resultDiv.style.border = '2px solid #059669';
            resultDiv.style.display = 'block';
            
            if (data.hash) {
                newHashValue.value = data.hash;
                newHashDisplay.style.display = 'block';
                localStorage.setItem('access_hash', data.hash);
            }
            
            document.getElementById('currentPasswordForChange').value = '';
            document.getElementById('newPasswordInput').value = '';
            document.getElementById('confirmPasswordInput').value = '';
            
            alert('✅ 访问密码修改成功！\n\n新密码已生效。\n5秒后将自动跳转到登录页面。');
            
            setTimeout(() => {
                document.cookie = 'access_password=; path=/; max-age=0';
                window.location.href = '/';
            }, 5000);
        } else {
            messageP.textContent = '❌ ' + (data.message || '修改失败');
            messageP.style.color = '#dc2626';
            resultDiv.style.background = '#fee2e2';
            resultDiv.style.border = '2px solid #dc2626';
            resultDiv.style.display = 'block';
            newHashDisplay.style.display = 'none';
        }
    } catch (error) {
        messageP.textContent = '❌ 修改失败：' + error.message;
        messageP.style.color = '#dc2626';
        resultDiv.style.background = '#fee2e2';
        resultDiv.style.border = '2px solid #dc2626';
        resultDiv.style.display = 'block';
        newHashDisplay.style.display = 'none';
    }
}

async function loadApiHash() {
    try {
        const password = getCookie('access_password');
        if (!password) {
            return;
        }
        
        const response = await fetch('/auth/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `password=${encodeURIComponent(password)}`
        });
        
        const data = await response.json();
        if (data.code === 200 && data.hash) {
            document.getElementById('apiHashValue').value = data.hash;
            document.getElementById('apiHashDisplay').style.display = 'block';
            localStorage.setItem('access_hash', data.hash);
        }
    } catch (error) {
        console.error('加载API Hash失败:', error);
    }
}

function copyApiHash() {
    const hashInput = document.getElementById('apiHashValue');
    hashInput.select();
    document.execCommand('copy');
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '✓ 已复制';
    btn.style.background = '#10b981';
    setTimeout(() => {
        btn.textContent = originalText;
        btn.style.background = '';
    }, 2000);
}

function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return null;
}

// ============ Playlist Functions ============
async function loadPlaylist() {
    const input = document.getElementById('playlistInput').value.trim();
    if (!input) {
        alert('请输入歌单链接或ID');
        return;
    }

    const loadingDiv = document.getElementById('playlistLoading');
    const infoDiv = document.getElementById('playlistInfo');
    const songsDiv = document.getElementById('playlistSongs');

    loadingDiv.style.display = 'block';
    infoDiv.style.display = 'none';
    songsDiv.style.display = 'none';

    try {
        const response = await fetch(`/playlist/tracks?id=${encodeURIComponent(input)}`);
        const data = await response.json();

        if (data.code === 200) {
            currentPlaylistSongs = data.songs || [];
            displayPlaylistInfo(data.playlist_info);
            displayPlaylistSongs(currentPlaylistSongs);
            
            infoDiv.style.display = 'block';
            songsDiv.style.display = 'block';
        } else {
            alert('获取歌单失败: ' + (data.message || '未知错误'));
        }
    } catch (error) {
        console.error('Error loading playlist:', error);
        alert('加载歌单时出错: ' + error.message);
    } finally {
        loadingDiv.style.display = 'none';
    }
}

function displayPlaylistInfo(info) {
    document.getElementById('playlistCover').src = info.coverImgUrl || '';
    document.getElementById('playlistName').textContent = info.name || '未知歌单';
    document.getElementById('playlistCreator').textContent = info.creator || '未知';
    document.getElementById('playlistCount').textContent = info.trackCount || 0;
    document.getElementById('playlistPlayCount').textContent = (info.playCount || 0).toLocaleString();
}

function displayPlaylistSongs(songs) {
    const listDiv = document.getElementById('playlistSongList');
    listDiv.innerHTML = '';

    songs.forEach((song, index) => {
        const artists = song.ar?.map(ar => ar.name).join(', ') || '未知';
        const duration = song.dt ? Math.floor(song.dt / 1000) : 0;
        const minutes = Math.floor(duration / 60);
        const seconds = duration % 60;
        const durationStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

        const songItem = document.createElement('div');
        songItem.className = 'song-item';
        songItem.innerHTML = `
            <div class="song-number">${index + 1}</div>
            <div class="song-info">
                <div class="song-title">${song.name || '未知歌曲'}</div>
                <div class="song-artist">${artists} • ${song.al?.name || '未知专辑'}</div>
            </div>
            <div class="song-duration">${durationStr}</div>
            <div class="song-actions">
                <button class="btn-action" onclick="playPlaylistSong(${song.id})" title="播放">▶</button>
                <button class="btn-action" onclick="viewSongInfo(${song.id})" title="详情">ℹ</button>
            </div>
        `;
        listDiv.appendChild(songItem);
    });
}

async function playPlaylistSong(songId) {
    try {
        const level = document.getElementById('optionLevel')?.value || 'standard';

        const params = new URLSearchParams({
            id: songId,
            level: level
        });

        // 使用 /play/direct 获取 URL（JSON格式）
        const response = await fetch(`/play/direct?${params.toString()}`);
        const data = await response.json();

        if (data.success && data.url) {
            const videoPlayer = document.getElementById('video');
            
            // 先暂停并清空当前播放，防止重复播放
            videoPlayer.pause();
            videoPlayer.removeAttribute('src');
            videoPlayer.load();
            
            // 设置新的源并播放
            videoPlayer.src = data.url;
            videoPlayer.load();
            videoPlayer.play();

            const apiUrl = `${window.location.origin}/stream?id=${songId}&level=${level}`;
            document.getElementById('apiUrl').value = apiUrl;

            document.getElementById('videoPlayer').style.display = 'block';
            document.getElementById('videoPlayer').scrollIntoView({ behavior: 'smooth' });
        } else {
            alert('无法播放: ' + (data.message || '未知错误'));
        }
    } catch (error) {
        console.error('Error playing song:', error);
        alert('播放失败: ' + error.message);
    }
}

function playAllPlaylistSongs() {
    if (currentPlaylistSongs.length === 0) {
        alert('歌单为空');
        return;
    }
    playPlaylistSong(currentPlaylistSongs[0].id);
    alert(`将播放 ${currentPlaylistSongs.length} 首歌曲（当前播放第一首，其他歌曲需要手动点击播放）`);
}

function viewSongInfo(songId) {
    const song = currentPlaylistSongs.find(s => s.id === songId);
    if (!song) return;

    const artists = song.ar?.map(ar => ar.name).join(', ') || '未知';
    const album = song.al?.name || '未知专辑';
    const duration = song.dt ? Math.floor(song.dt / 1000) : 0;
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;

    alert(`歌曲信息:\n\n名称: ${song.name}\n歌手: ${artists}\n专辑: ${album}\n时长: ${minutes}:${seconds.toString().padStart(2, '0')}\nID: ${songId}`);
}

// ============ Initialization ============
window.onload = function() {
    initTheme();
    switchMode('search');
    loadApiHash();
    initFloatingVideoDrag();
};
