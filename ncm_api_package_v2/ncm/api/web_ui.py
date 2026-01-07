"""
Web UI - 可视化界面
提供搜索和播放功能的网页界面
"""

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NCM Video Service</title>
    <style>
        :root {
            --bg-color: #fff;
            --text-primary: #171717;
            --text-secondary: #666;
            --border-color: #eaeaea;
            --accent-color: #000;
            --accent-hover: #333;
            --blue: #0070f3;
            --radius: 6px;
            --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            --shadow-sm: 0 2px 4px rgba(0,0,0,0.02);
            --shadow-md: 0 5px 10px rgba(0,0,0,0.12);
            --transition: all 0.2s ease;
        }

        [data-theme="dark"] {
            --bg-color: #000;
            --text-primary: #fafafa;
            --text-secondary: #888;
            --border-color: #333;
            --accent-color: #fff;
            --accent-hover: #ccc;
            --shadow-sm: 0 2px 4px rgba(255,255,255,0.02);
            --shadow-md: 0 5px 10px rgba(255,255,255,0.05);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            -webkit-font-smoothing: antialiased;
        }

        /* Mouse glow effect for dark mode */
        [data-theme="dark"] body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            background: radial-gradient(100px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04) 40%, transparent 70%);
            pointer-events: none;
            z-index: -1;
            transition: opacity 0.3s ease;
        }

        body {
            font-family: var(--font-sans);
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            align-items: center;
            padding: 40px 20px;
            transition: background-color 0.3s ease, color 0.3s ease;
            position: relative;
        }

        .container {
            width: 100%;
            max-width: 900px;
            margin: 0 auto;
            padding-bottom: 80px; /* Prevent content from being hidden by floating tabs */
        }

        /* Theme Toggle Button */
        .theme-toggle {
            position: fixed;
            top: 30px;
            right: 30px;
            width: 48px;
            height: 48px;
            border: 1px solid var(--border-color);
            border-radius: 50%;
            background: var(--bg-color);
            color: var(--text-primary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: var(--transition);
            box-shadow: var(--shadow-md);
            z-index: 1001;
        }

        .theme-toggle:hover {
            transform: translateY(-2px);
            box-shadow: var(--shadow-md), 0 8px 25px rgba(0,0,0,0.15);
        }

        .theme-toggle svg {
            width: 20px;
            height: 20px;
            transition: transform 0.3s ease;
        }

        .theme-toggle:hover svg {
            transform: rotate(180deg);
        }

        /* Header */
        .header {
            text-align: center;
            margin-bottom: 40px;
        }

        .header h1 {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.05rem;
            margin-bottom: 10px;
            background: linear-gradient(180deg, #555 0%, #000 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        [data-theme="dark"] .header h1 {
            background: linear-gradient(180deg, #fff 0%, #ccc 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .header p {
            color: var(--text-secondary);
            font-size: 1rem;
        }

        /* Tabs (Floating Bottom) */
        .tabs {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(255, 255, 255, 0.85); /* Slightly transparent */
            backdrop-filter: blur(12px); /* Glassmorphism effect */
            border: 1px solid rgba(0,0,0,0.1);
            border-radius: 9999px; /* Capsule shape */
            padding: 4px; /* Tighter padding */
            display: inline-flex;
            box-shadow: 0 8px 30px rgba(0,0,0,0.12); /* Pop out shadow */
            z-index: 1000;
            gap: 2px;
            transition: all 0.3s ease;
        }

        [data-theme="dark"] .tabs {
            background: rgba(0, 0, 0, 0.85);
            border: 1px solid rgba(255,255,255,0.1);
            box-shadow: 0 8px 30px rgba(0,0,0,0.5);
        }

        .tabs:hover {
            transform: translate(-50%, -4px); /* Slight upward float */
            box-shadow: 0 12px 40px rgba(0,0,0,0.2), 0 0 20px rgba(102, 126, 234, 0.3); /* Enhanced shadow + glow */
            background: rgba(255, 255, 255, 0.95); /* Slightly more opaque on hover */
        }

        [data-theme="dark"] .tabs:hover {
            background: rgba(0, 0, 0, 0.95);
            box-shadow: 0 12px 40px rgba(0,0,0,0.6), 0 0 20px rgba(102, 126, 234, 0.4);
        }

        /* Sliding indicator */
        .tabs::before {
            content: '';
            position: absolute;
            top: 4px;
            left: 4px;
            width: calc(50% - 1px); /* Half width minus gap */
            height: calc(100% - 8px);
            background: var(--accent-color);
            border-radius: 9999px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: -1;
        }

        .tabs[data-active="direct"]::before {
            transform: translateX(calc(100% + 2px));
        }

        .tab-btn {
            background: transparent;
            border: none;
            padding: 10px 24px;
            border-radius: 9999px; /* Capsule buttons */
            font-size: 0.9rem;
            color: var(--text-secondary);
            cursor: pointer;
            transition: var(--transition);
            font-weight: 500;
            white-space: nowrap;
            position: relative;
            z-index: 1;
        }

        .tab-btn:hover {
            color: var(--text-primary);
        }

        .tab-btn.active {
            color: #fff;
        }

        [data-theme="dark"] .tab-btn.active {
            color: #000;
        }

        /* Main Content Card */
        .card {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 30px;
            box-shadow: var(--shadow-md);
            margin-bottom: 24px;
            transition: var(--transition);
        }

        .card:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }

        /* Search Section */
        .input-group {
            display: flex;
            gap: 12px;
            margin-bottom: 24px;
            align-items: stretch; /* Ensure equal height */
        }

        .input-wrapper {
            flex: 1;
            position: relative;
        }

        .input {
            width: 100%;
            height: 48px; /* Match button height */
            padding: 0 16px;
            padding-left: 40px; /* Space for icon */
            font-size: 1rem;
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            outline: none;
            transition: var(--transition);
            background: var(--bg-color);
            color: var(--text-primary);
            box-sizing: border-box; /* Ensure consistent sizing */
        }

        .input::placeholder {
            color: var(--text-secondary);
        }

        .input:focus {
            border-color: var(--text-primary);
            box-shadow: 0 0 0 2px rgba(0,0,0,0.1);
        }
        
        .search-icon-placeholder {
            position: absolute;
            left: 14px;
            top: 50%;
            transform: translateY(-50%);
            color: #999;
            width: 16px;
            height: 16px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .search-icon-placeholder svg {
            width: 16px;
            height: 16px;
            vertical-align: middle;
        }

        .btn {
            padding: 0 24px;
            height: 48px;
            border-radius: var(--radius);
            border: 1px solid transparent;
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .btn-primary {
            background: var(--text-primary);
            color: var(--bg-color);
        }

        .btn-primary:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        /* Options */
        .options-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 16px;
            align-items: center;
            padding-top: 20px;
            border-top: 1px solid var(--border-color);
        }

        .checkbox-label {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9rem;
            color: var(--text-secondary);
            cursor: pointer;
            user-select: none;
        }

        .checkbox-label input[type="checkbox"] {
            appearance: none;
            width: 18px;
            height: 18px;
            border: 1px solid var(--border-color);
            border-radius: 4px;
            position: relative;
            cursor: pointer;
            transition: var(--transition);
        }

        .checkbox-label input[type="checkbox"]:checked {
            background: var(--accent-color);
            border-color: var(--accent-color);
        }

        .checkbox-label input[type="checkbox"]:checked::after {
            content: "✓";
            color: var(--bg-color);
            position: absolute;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%);
            font-size: 12px;
        }

        .select-wrapper {
            position: relative;
        }

        .select-wrapper select {
            width: 100%;
            padding: 8px 12px;
            padding-right: 32px; /* Space for arrow */
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            font-size: 0.9rem;
            color: var(--text-primary);
            outline: none;
            background: var(--bg-color);
            cursor: pointer;
            transition: var(--transition);
            box-shadow: var(--shadow-sm);
            appearance: none; /* Remove default styling */
            -webkit-appearance: none;
            -moz-appearance: none;
        }

        .select-wrapper::after {
            content: '';
            position: absolute;
            right: 12px;
            top: 50%;
            transform: translateY(-50%);
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid var(--text-secondary);
            pointer-events: none;
            transition: var(--transition);
        }

        .select-wrapper:hover::after {
            border-top-color: var(--text-primary);
        }

        .select-wrapper select:hover {
            border-color: var(--text-primary);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            transform: translateY(-1px);
        }

        .select-wrapper select:focus {
            border-color: var(--text-primary);
            box-shadow: 0 0 0 2px rgba(0,0,0,0.1), 0 4px 12px rgba(0,0,0,0.15);
        }

        .select-wrapper select option {
            padding: 8px 12px;
            color: var(--text-primary);
            background: var(--bg-color);
        }

        .select-wrapper select option:hover,
        .select-wrapper select option:checked {
            background: var(--border-color);
        }

        /* Results */
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
        }

        .results-header h2 {
            font-size: 1.25rem;
            font-weight: 600;
        }

        .results-count {
            font-size: 0.85rem;
            color: var(--text-secondary);
            background: #f0f0f0;
            padding: 4px 8px;
            border-radius: 99px;
        }

        .song-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .song-item {
            display: flex;
            align-items: center;
            padding: 12px;
            border: 1px solid transparent;
            border-radius: var(--radius);
            cursor: pointer;
            transition: var(--transition);
        }

        .song-item:hover {
            background: var(--border-color);
            border-color: var(--text-secondary);
        }

        .song-cover {
            width: 48px;
            height: 48px;
            border-radius: 4px;
            object-fit: cover;
            background: #eee;
            margin-right: 16px;
        }

        .song-info {
            flex: 1;
        }

        .song-name {
            font-size: 1rem;
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .song-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
        }

        .badge {
            font-size: 0.65rem;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .badge-mv {
            background: #ffe3e3;
            color: #d63333;
        }

        .badge-vip {
            background: #fff3cd;
            color: #856404;
        }
        
        .play-icon {
            opacity: 0;
            transform: translateX(-10px);
            transition: var(--transition);
            color: var(--text-primary);
        }
        
        .song-item:hover .play-icon {
            opacity: 1;
            transform: translateX(0);
        }

        /* Video Player */
        .video-container {
            border-radius: 12px;
            overflow: hidden;
            background: #000;
            box-shadow: 0 20px 40px -10px rgba(0,0,0,0.3);
            margin: 20px 0;
            display: none; /* Initially hidden */
        }

        .video-container video {
            width: 100%;
            display: block;
        }

        .api-tools {
            background: #f7f7f7;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
        }

        .api-url-group {
            display: flex;
            gap: 10px;
            margin-top: 8px;
        }

        .api-input {
            flex: 1;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', 'Droid Sans Mono', 'Source Code Pro', monospace;
            font-size: 0.85rem;
            padding: 8px 12px;
            border-radius: 4px;
        }

        .btn-copy {
            padding: 8px 16px;
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            border-radius: 4px;
            font-size: 0.85rem;
            cursor: pointer;
            transition: var(--transition);
        }

        .btn-copy:hover {
            border-color: var(--text-primary);
        }

        /* Pagination */
        .pagination {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 16px;
            padding-top: 24px;
        }

        .btn-page {
            background: var(--bg-color);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: var(--radius);
            font-size: 0.9rem;
            cursor: pointer;
        }
        
        .btn-page:hover:not(:disabled) {
            border-color: var(--text-primary);
        }

        .btn-page:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Loading */
        .loading-state {
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }
        
        .spinner {
            width: 20px;
            height: 20px;
            border: 2px solid #eaeaea;
            border-top-color: #000;
            border-radius: 50%;
            margin: 0 auto 10px;
            animation: spin 0.8s linear infinite;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        /* Responsive */
        @media (max-width: 600px) {
            .header h1 { font-size: 1.5rem; }
            .input-group { flex-direction: column; }
            .btn { width: 100%; }
            .card { padding: 20px; }
        }
    </style>
</head>
<body>

    <div class="header">
        <h1>NCM Video Service</h1>
        <p>网易云音乐视频预载服务</p>
    </div>

    <!-- Theme Toggle Button -->
    <button class="theme-toggle" onclick="toggleTheme()" id="themeToggle">
        <svg class="sun-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"/>
            <line x1="12" y1="1" x2="12" y2="3"/>
            <line x1="12" y1="21" x2="12" y2="23"/>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
            <line x1="1" y1="12" x2="3" y2="12"/>
            <line x1="21" y1="12" x2="23" y2="12"/>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
        <svg class="moon-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display: none;">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>
    </button>

    <!-- Floating Tabs moved outside Header for logical separation -->
    <div class="tabs" data-active="search">
        <button id="btnSearch" class="tab-btn active" onclick="switchMode('search')">关键词搜索</button>
        <button id="btnDirect" class="tab-btn" onclick="switchMode('direct')">歌曲ID播放</button>
    </div>

    <div class="container">
        <!-- Search Card -->
        <div class="card">
            <div class="input-group">
                <div class="input-wrapper">
                    <span class="search-icon-placeholder">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
                    </span>
                    <input 
                        type="text" 
                        id="searchInput" 
                        class="input" 
                        placeholder="输入歌曲名或歌手名..."
                        onkeypress="if(event.key==='Enter') handleAction()"
                    >
                </div>
                <button class="btn btn-primary" onclick="handleAction()" id="actionButton">
                    查找视频
                </button>
            </div>
            
            <div class="options-grid">
                <label class="checkbox-label">
                    <input type="checkbox" id="optionMv" checked>
                    <span>优先使用 MV</span>
                </label>
                <label class="checkbox-label">
                    <input type="checkbox" id="optionGpu" checked>
                    <span>启用硬件加速</span>
                </label>
                <div class="select-wrapper">
                    <select id="optionLevel">
                        <option value="standard">标准音质</option>
                        <option value="higher">较高音质</option>
                        <option value="exhigh">极高音质</option>
                        <option value="lossless">无损音质</option>
                    </select>
                </div>
            </div>
        </div>

        <!-- Player Card -->
        <div id="videoPlayer" class="video-container">
            <video id="video" controls autoplay></video>
            <div style="background: white; padding: 20px;">
                <h3 style="font-size: 1rem; margin-bottom: 10px;">API Integration</h3>
                <div class="api-tools">
                    <label style="font-size: 0.8rem; font-weight: 600;">Request URL</label>
                    <div class="api-url-group">
                        <input type="text" id="apiUrl" readonly class="api-input" value="Waiting for playback...">
                        <button onclick="copyApiUrl()" class="btn-copy">Copy</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Results Section -->
        <div id="results" class="card" style="display: none; border: none; box-shadow: none; background: transparent; padding: 0;">
            <div class="results-header">
                <h2 id="resultsTitle">搜索结果</h2>
                <span class="results-count" id="resultCount">0</span>
            </div>
            
            <div id="songList" class="song-list">
                <!-- Items will be injected here -->
            </div>

            <div class="pagination" id="pagination" style="display: none;">
                <button onclick="prevPage()" id="btnPrev" class="btn-page">Previous</button>
                <span id="pageInfo" style="font-size: 0.9rem; color: var(--text-secondary);">1 / 1</span>
                <button onclick="nextPage()" id="btnNext" class="btn-page">Next</button>
            </div>
        </div>
    </div>

    <script>
        let currentResults = [];
        let currentMode = 'search'; // 'search' or 'direct'
        let currentPage = 1;
        let currentKeywords = '';
        const pageSize = 10;
        let isSearching = false;
        
        // Theme management
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
        
        // Initialize theme
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
        
        function switchMode(mode) {
            currentMode = mode;
            const btnSearch = document.getElementById('btnSearch');
            const btnDirect = document.getElementById('btnDirect');
            const searchInput = document.getElementById('searchInput');
            const actionButton = document.getElementById('actionButton');
            const resultsDiv = document.getElementById('results');
            const tabs = document.querySelector('.tabs');
            
            if (mode === 'search') {
                btnSearch.classList.add('active');
                btnDirect.classList.remove('active');
                tabs.setAttribute('data-active', 'search');
                searchInput.placeholder = '输入歌曲名或歌手名...';
                actionButton.innerHTML = '查找视频';
                searchInput.type = 'text';
            } else {
                btnSearch.classList.remove('active');
                btnDirect.classList.add('active');
                tabs.setAttribute('data-active', 'direct');
                searchInput.placeholder = '输入歌曲 ID (例如: 1330944279)';
                actionButton.innerHTML = '播放歌曲';
                searchInput.type = 'number';
                resultsDiv.style.display = 'none';
            }
            
            searchInput.value = '';
            searchInput.focus();
        }
        
        async function handleAction() {
            if (currentMode === 'search') {
                await searchSongs();
            } else {
                await directPlay();
            }
        }
        
        async function directPlay() {
            const songId = document.getElementById('searchInput').value.trim();
            if (!songId || isNaN(songId)) {
                alert('请输入有效的歌曲ID（纯数字）');
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
            
            if (isSearching) return;
            isSearching = true;
            currentKeywords = keywords;
            currentPage = page;
            
            const resultsDiv = document.getElementById('results');
            const songListDiv = document.getElementById('songList');
            const resultsTitle = document.getElementById('resultsTitle');
            const paginationDiv = document.getElementById('pagination');
            
            resultsDiv.style.display = 'block';
            songListDiv.innerHTML = '<div class="loading-state"><div class="spinner"></div><p>Searching...</p></div>';
            paginationDiv.style.display = 'none';
            
            try {
                // Try to fetch from real API
                const offset = (page - 1) * pageSize;
                let data;
                
                try {
                    const response = await fetch(`/search?keywords=${encodeURIComponent(keywords)}&limit=${pageSize}&offset=${offset}`);
                    if (!response.ok) throw new Error("API not available");
                    data = await response.json();
                } catch (e) {
                    console.warn("API fetch failed, utilizing mock data for preview:", e);
                    // Mock data for preview purposes
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
            
            const videoUrl = `/video?${params.toString()}`;
            const fullApiUrl = window.location.origin + videoUrl;
            
            document.getElementById('apiUrl').value = fullApiUrl;
            
            videoPlayerDiv.style.display = 'block';
            videoElement.src = videoUrl; // Assuming logic or adding mock fallback below
            
            // Mock behavior for preview if not on server
            videoElement.onerror = () => {
                console.log("Video load failed (expected in preview mode).");
                // Optional: set a placeholder video if desired
            };
            
            videoElement.load();
            videoPlayerDiv.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
        
        function copyApiUrl() {
            const apiUrlInput = document.getElementById('apiUrl');
            apiUrlInput.select();
            document.execCommand('copy');
            
            const btn = event.currentTarget || event.target; // event.target needs currentTarget for button click
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

        // Theme management
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
        
        // Initialize theme
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

        window.onload = function() {
            initTheme();
            switchMode('search');
        };
    </script>
</body>
</html>
"""

def get_web_ui_html():
    """返回Web UI的HTML内容"""
    return HTML_TEMPLATE
