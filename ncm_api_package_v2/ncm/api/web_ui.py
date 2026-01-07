"""
Web UI - 可视化界面
提供搜索和播放功能的网页界面
"""

HTML_TEMPLATE = r"""
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

        html {
            background-color: var(--bg-color);
            transition: background-color 0.3s ease;
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
            max-width: 1200px;
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
            width: calc(33.333% - 2px); /* One third width for 3 tabs */
            height: calc(100% - 8px);
            background: var(--accent-color);
            border-radius: 9999px;
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            z-index: -1;
        }

        .tabs[data-active="direct"]::before {
            transform: translateX(calc(100% + 4px));
        }

        .tabs[data-active="login"]::before {
            transform: translateX(calc(200% + 8px));
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
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 30px;
            box-shadow: var(--shadow-md);
            margin-bottom: 24px;
            transition: var(--transition);
            backdrop-filter: blur(8px);
        }

        .card:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }

        [data-theme="dark"] .card {
            background: rgba(17, 17, 17, 0.9);
            box-shadow: 0 4px 20px rgba(0,0,0,0.8);
        }

        [data-theme="light"] .card {
            background: rgba(255, 255, 255, 0.9);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        [data-theme="dark"] .card:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.8);
        }

        [data-theme="light"] .card:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.3);
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
            background: var(--card-bg);
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

        /* Login Styles */
        .login-status {
            padding: 15px;
            border-radius: 8px;
            background: rgba(0, 112, 243, 0.1);
            border: 1px solid rgba(0, 112, 243, 0.3);
            margin-bottom: 20px;
            text-align: center;
        }

        .login-status.success {
            background: rgba(16, 185, 129, 0.1);
            border-color: rgba(16, 185, 129, 0.3);
        }

        .login-status.error {
            background: rgba(239, 68, 68, 0.1);
            border-color: rgba(239, 68, 68, 0.3);
        }

        .login-methods {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }

        .login-method-btn {
            flex: 1;
            min-width: 100px;
            padding: 10px 16px;
            border: 1px solid var(--border-color);
            background: var(--bg-color);
            color: var(--text-primary);
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            transition: var(--transition);
        }

        .login-method-btn:hover {
            background: var(--accent-color);
            color: #fff;
            border-color: var(--accent-color);
        }

        .login-method-btn.active {
            background: var(--accent-color);
            color: #fff;
            border-color: var(--accent-color);
        }

        [data-theme="dark"] .login-method-btn.active {
            background: var(--accent-color);
            color: #000;
        }

        .login-section {
            animation: fadeIn 0.3s ease;
        }

        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        #qrCodeContainer {
            border: 2px solid var(--border-color);
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

        .video-info-panel {
            background: var(--card-bg);
            padding: 20px;
            border-top: 1px solid var(--border-color);
        }

        [data-theme="dark"] .video-info-panel {
            background: rgba(17, 17, 17, 0.9);
        }

        [data-theme="light"] .video-info-panel {
            background: rgba(255, 255, 255, 0.9);
        }

        .video-info-panel h3 {
            color: var(--text-primary);
        }

        /* Floating Video Window */
        .floating-video {
            position: fixed;
            bottom: 20px;
            left: 20px;
            width: 300px;
            height: auto;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            z-index: 1000;
            display: none;
            overflow: hidden;
            cursor: move;
            user-select: none;
        }

        [data-theme="dark"] .floating-video {
            box-shadow: 0 10px 30px rgba(0,0,0,0.8);
        }

        .floating-video-header {
            background: var(--card-bg);
            color: var(--text-primary);
            padding: 8px 12px;
            font-size: 0.8rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            cursor: move;
            border-bottom: 1px solid var(--border-color);
            backdrop-filter: blur(8px);
        }

        [data-theme="dark"] .floating-video-header {
            background: rgba(17, 17, 17, 0.9);
        }

        [data-theme="light"] .floating-video-header {
            background: rgba(255, 255, 255, 0.9);
        }

        .floating-video-title {
            flex: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .floating-video-controls {
            display: flex;
            gap: 8px;
        }

        .floating-control-btn {
            background: none;
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            padding: 2px 4px;
            font-size: 12px;
            border-radius: 2px;
            transition: background 0.2s;
        }

        .floating-control-btn:hover {
            background: var(--hover-bg);
        }

        [data-theme="dark"] .floating-control-btn:hover {
            background: rgba(255,255,255,0.1);
        }

        [data-theme="light"] .floating-control-btn:hover {
            background: rgba(0,0,0,0.1);
        }

        .floating-video video {
            width: 100%;
            height: auto;
            display: block;
            background: #000;
        }

        /* Minimize floating video */
        .floating-video.minimized {
            height: 40px;
        }

        .floating-video.minimized video {
            display: none;
        }

        .api-tools {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 16px;
            margin-top: 16px;
            backdrop-filter: blur(8px);
        }

        [data-theme="dark"] .api-tools {
            background: rgba(17, 17, 17, 0.9);
        }

        [data-theme="light"] .api-tools {
            background: rgba(255, 255, 255, 0.9);
        }

        .api-url-group {
            display: flex;
            gap: 10px;
            margin-top: 8px;
        }

        .api-input {
            flex: 1;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-secondary);
            font-family: 'SF Mono', 'Monaco', 'Inconsolata', 'Fira Mono', 'Droid Sans Mono', 'Source Code Pro', monospace;
            font-size: 0.85rem;
            padding: 8px 12px;
            border-radius: 4px;
        }

        .btn-copy {
            padding: 8px 16px;
            background: var(--card-bg);
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

        [data-theme="dark"] .btn-copy:hover {
            background: rgba(255,255,255,0.1);
        }

        [data-theme="light"] .btn-copy:hover {
            background: rgba(0,0,0,0.1);
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
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-primary);
            padding: 8px 16px;
            border-radius: var(--radius);
            cursor: pointer;
            font-size: 0.9rem;
            transition: var(--transition);
        }

        .btn-page:hover:not(:disabled) {
            border-color: var(--text-primary);
        }

        [data-theme="dark"] .btn-page:hover:not(:disabled) {
            background: rgba(255,255,255,0.1);
        }

        [data-theme="light"] .btn-page:hover:not(:disabled) {
            background: rgba(0,0,0,0.1);
        }

        .btn-page:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
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
        <button id="btnLogin" class="tab-btn" onclick="switchMode('login')">登录管理</button>
    </div>

    <div class="container">
        <!-- Login Card -->
        <div id="loginCard" class="card" style="display: none;">
            <h2 style="margin-bottom: 20px; font-size: 1.5rem;">网易云音乐登录</h2>
            
            <!-- Login Status -->
            <div id="loginStatus" class="login-status">
                <p id="loginStatusText">检查登录状态中...</p>
            </div>

            <!-- Login Method Selector -->
            <div class="login-methods">
                <button class="login-method-btn active" onclick="selectLoginMethod('qr', event)">扫码登录</button>
                <button class="login-method-btn" onclick="selectLoginMethod('sms', event)">短信登录</button>
                <button class="login-method-btn" onclick="selectLoginMethod('password', event)">密码登录</button>
                <button class="login-method-btn" onclick="selectLoginMethod('cookie', event)">导入Cookie</button>
            </div>

            <!-- QR Code Login -->
            <div id="qrLoginSection" class="login-section">
                <div style="text-align: center;">
                    <div id="qrCodeContainer" style="display: inline-block; padding: 20px; background: white; border-radius: 8px; margin: 20px 0;">
                        <img id="qrCodeImage" src="" alt="二维码加载中..." style="width: 200px; height: 200px;">
                    </div>
                    <p id="qrTip" style="color: var(--text-secondary); margin-top: 10px;">请使用网易云音乐APP扫码登录</p>
                    <button class="btn btn-primary" onclick="startQRLogin()" style="margin-top: 10px;">刷新二维码</button>
                </div>
            </div>

            <!-- SMS Login -->
            <div id="smsLoginSection" class="login-section" style="display: none;">
                <div class="input-group" style="flex-direction: column; gap: 15px;">
                    <input type="tel" id="smsPhone" class="input" placeholder="请输入手机号" maxlength="11">
                    <div style="display: flex; gap: 10px;">
                        <button class="btn btn-secondary" onclick="sendSMSCode()" id="smsSendBtn">发送验证码</button>
                    </div>
                    <input type="text" id="smsCaptcha" class="input" placeholder="请输入验证码" maxlength="6">
                    <button class="btn btn-primary" onclick="verifySMSLogin()">登录</button>
                </div>
            </div>

            <!-- Password Login -->
            <div id="passwordLoginSection" class="login-section" style="display: none;">
                <div class="input-group" style="flex-direction: column; gap: 15px;">
                    <input type="tel" id="pwdPhone" class="input" placeholder="请输入手机号" maxlength="11">
                    <input type="password" id="pwdPassword" class="input" placeholder="请输入密码">
                    <button class="btn btn-primary" onclick="passwordLogin()">登录</button>
                </div>
            </div>

            <!-- Cookie Import -->
            <div id="cookieLoginSection" class="login-section" style="display: none;">
                <div class="input-group" style="flex-direction: column; gap: 15px;">
                    <textarea id="cookieInput" class="input" placeholder="请粘贴完整的Cookie字符串" style="min-height: 100px; resize: vertical; font-family: monospace; font-size: 12px;"></textarea>
                    <button class="btn btn-primary" onclick="importCookie()">导入Cookie</button>
                    <p style="color: var(--text-secondary); font-size: 0.85rem; margin-top: 10px;">
                        💡 提示：从浏览器开发者工具中复制Cookie，格式如：MUSIC_U=...; __csrf=...
                    </p>
                </div>
            </div>

            <!-- Logout Button -->
            <div id="logoutSection" style="display: none; margin-top: 20px;">
                <button class="btn btn-secondary" onclick="logout()" style="width: 100%;">退出登录</button>
            </div>
            
            <!-- Access Password Management -->
            <div style="margin-top: 30px; padding-top: 30px; border-top: 1px solid var(--border-color);">
                <h3 style="margin-bottom: 15px; font-size: 1.2rem; color: var(--text-primary);">访问密码管理</h3>
                
                <!-- API Hash Display -->
                <div id="apiHashDisplay" style="display: none; margin-bottom: 20px; padding: 15px; background: rgba(0, 112, 243, 0.05); border: 2px solid rgba(0, 112, 243, 0.3); border-radius: 8px;">
                    <p style="font-weight: 600; margin-bottom: 8px; color: var(--text-primary);">🔑 API访问Hash（用于API调用）：</p>
                    <div style="display: flex; gap: 10px; align-items: center;">
                        <input type="text" id="apiHashValue" readonly class="input" style="flex: 1; font-family: monospace; font-size: 0.85rem;" value="">
                        <button onclick="copyApiHash()" class="btn btn-primary" style="min-width: 80px;">📋 复制</button>
                    </div>
                    <p style="margin-top: 10px; font-size: 0.85rem; color: var(--text-secondary);">
                        💡 在API请求中添加参数 <code style="background: rgba(0,0,0,0.1); padding: 2px 6px; border-radius: 3px;">access_hash={your_hash}</code> 即可直接访问
                    </p>
                </div>
                
                <p style="color: var(--text-secondary); font-size: 0.9rem; margin-bottom: 15px;">
                    修改访问密码后，所有用户需要使用新密码才能访问系统
                </p>
                <div class="input-group" style="flex-direction: column; gap: 15px;">
                    <input type="password" id="currentPasswordForChange" class="input" placeholder="输入当前访问密码">
                    <input type="password" id="newPasswordInput" class="input" placeholder="输入新密码（至少6位）" minlength="6">
                    <input type="password" id="confirmPasswordInput" class="input" placeholder="确认新密码">
                    <button class="btn btn-primary" onclick="changeAccessPassword()" style="background: #f59e0b;">
                        🔒 修改访问密码
                    </button>
                </div>
                <div id="passwordChangeResult" style="display: none; margin-top: 15px; padding: 15px; border-radius: 8px;">
                    <p id="passwordChangeMessage" style="font-weight: 600;"></p>
                    <div id="newHashDisplay" style="display: none; margin-top: 10px;">
                        <p style="font-size: 0.9rem; color: var(--text-secondary); margin-bottom: 5px;">新密码的Hash值：</p>
                        <input type="text" id="newHashValue" readonly class="input" style="font-family: monospace; font-size: 0.85rem; margin-top: 5px;" value="">
                    </div>
                </div>
                </div>
            </div>
        </div>

        <!-- Search Card -->
        <div class="card" id="searchCard">
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
            <div class="video-info-panel">
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
            const btnLogin = document.getElementById('btnLogin');
            const searchCard = document.getElementById('searchCard');
            const loginCard = document.getElementById('loginCard');
            const searchInput = document.getElementById('searchInput');
            const actionButton = document.getElementById('actionButton');
            const resultsDiv = document.getElementById('results');
            const tabs = document.querySelector('.tabs');
            
            // Remove active from all buttons
            btnSearch.classList.remove('active');
            btnDirect.classList.remove('active');
            btnLogin.classList.remove('active');
            
            // Hide all cards
            searchCard.style.display = 'none';
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
                searchInput.placeholder = '输入歌曲 ID (例如: 1330944279)';
                actionButton.innerHTML = '播放歌曲';
                searchInput.type = 'number';
                searchInput.value = '';
                searchInput.focus();
            } else if (mode === 'login') {
                btnLogin.classList.add('active');
                loginCard.style.display = 'block';
                tabs.setAttribute('data-active', 'login');
                checkLoginStatus();
            }
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
            
            // 搜索时检查是否有视频在播放，如果有则转移到悬浮窗口
            const videoElement = document.getElementById('video');
            const floatingVideoDiv = document.getElementById('floatingVideo');
            const floatingVideoElement = document.getElementById('floatingVideoPlayer');
            const floatingVideoTitle = document.getElementById('floatingVideoTitle');
            
            if (videoElement && videoElement.src && !videoElement.paused && !videoElement.ended) {
                floatingVideoElement.src = videoElement.src;
                floatingVideoElement.currentTime = videoElement.currentTime;
                floatingVideoTitle.textContent = videoElement.dataset.currentTitle || '正在播放';
                floatingVideoDiv.style.display = 'block';
                // 悬浮窗口视频默认暂停
                floatingVideoElement.pause();
                
                // 清空主视频播放器
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
            
            // 添加access_hash参数
            const accessHash = localStorage.getItem('access_hash') || getCookie('access_password');
            if (accessHash) {
                params.append('access_hash', accessHash);
            }
            
            const videoUrl = `/video?${params.toString()}`;
            const fullApiUrl = window.location.origin + videoUrl;
            
            document.getElementById('apiUrl').value = fullApiUrl;
            
            videoPlayerDiv.style.display = 'block';
            videoElement.src = videoUrl;
            videoElement.dataset.currentTitle = `${name} - ${artist}`;
            
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

        // 悬浮视频窗口控制函数
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

        // 悬浮窗口拖拽功能
        let isDragging = false;
        let dragOffsetX = 0;
        let dragOffsetY = 0;

        document.addEventListener('DOMContentLoaded', function() {
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
                
                // 限制在视窗内
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
        });

        // ============ Login Functions ============
        let qrCheckInterval = null;
        let smsSendCountdown = 0;

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
                    return true; // 返回登录成功状态
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
            // Hide all sections
            document.getElementById('qrLoginSection').style.display = 'none';
            document.getElementById('smsLoginSection').style.display = 'none';
            document.getElementById('passwordLoginSection').style.display = 'none';
            document.getElementById('cookieLoginSection').style.display = 'none';
            
            // Remove active from all buttons
            document.querySelectorAll('.login-method-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            // Show selected section and mark button as active
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
                
                // Stop existing check interval
                if (qrCheckInterval) {
                    clearInterval(qrCheckInterval);
                }
                
                // Get QR key
                const keyResponse = await fetch('/login/qr/key');
                const keyData = await keyResponse.json();
                
                if (keyData.code !== 200) {
                    throw new Error('获取二维码Key失败');
                }
                
                const qrKey = keyData.unikey;
                
                // Get QR code image
                const qrResponse = await fetch(`/login/qr/create?key=${qrKey}`);
                const qrData = await qrResponse.json();
                
                if (qrData.code !== 200) {
                    throw new Error('生成二维码失败');
                }
                
                qrImage.src = qrData.qrimg;
                qrTip.textContent = '请使用网易云音乐APP扫码登录';
                
                // Start checking QR status with timeout (60 times, 2s interval = 120s)
                let checkCount = 0;
                const maxChecks = 60;
                
                qrCheckInterval = setInterval(async () => {
                    checkCount++;
                    
                    // Check timeout
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
                            // 立即检查登录状态
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

        async function changeAccessPassword() {
            const currentPassword = document.getElementById('currentPasswordForChange').value.trim();
            const newPassword = document.getElementById('newPasswordInput').value.trim();
            const confirmPassword = document.getElementById('confirmPasswordInput').value.trim();
            const resultDiv = document.getElementById('passwordChangeResult');
            const messageP = document.getElementById('passwordChangeMessage');
            const newHashDisplay = document.getElementById('newHashDisplay');
            const newHashValue = document.getElementById('newHashValue');
            
            // 验证输入
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
                    // 显示成功消息
                    messageP.textContent = '✅ 访问密码修改成功！';
                    messageP.style.color = '#059669';
                    resultDiv.style.background = '#d1fae5';
                    resultDiv.style.border = '2px solid #059669';
                    resultDiv.style.display = 'block';
                    
                    // 显示新的hash值
                    if (data.hash) {
                        newHashValue.value = data.hash;
                        newHashDisplay.style.display = 'block';
                        // 更新localStorage
                        localStorage.setItem('access_hash', data.hash);
                    }
                    
                    // 清空输入框
                    document.getElementById('currentPasswordForChange').value = '';
                    document.getElementById('newPasswordInput').value = '';
                    document.getElementById('confirmPasswordInput').value = '';
                    
                    alert('✅ 访问密码修改成功！\n\n新密码已生效。\n5秒后将自动跳转到登录页面。');
                    
                    // 5秒后跳转到登录页面
                    setTimeout(() => {
                        // 清除当前的访问密码 cookie
                        document.cookie = 'access_password=; path=/; max-age=0';
                        window.location.href = '/';
                    }, 5000);
                } else {
                    // 显示错误消息
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

        // 加载API Hash值
        async function loadApiHash() {
            try {
                // 从cookie中获取当前密码
                const password = getCookie('access_password');
                if (!password) {
                    return;
                }
                
                // 重新验证以获取hash（因为首次登录在登录页面，这里需要在主页面也能显示）
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
                    // 存储hash到localStorage，用于API URL生成
                    localStorage.setItem('access_hash', data.hash);
                }
            } catch (error) {
                console.error('加载API Hash失败:', error);
            }
        }

        // 复制API Hash
        function copyApiHash() {
            const hashInput = document.getElementById('apiHashValue');
            hashInput.select();
            document.execCommand('copy');
            
            // 显示复制成功提示
            const btn = event.target;
            const originalText = btn.textContent;
            btn.textContent = '✓ 已复制';
            btn.style.background = '#10b981';
            setTimeout(() => {
                btn.textContent = originalText;
                btn.style.background = '';
            }, 2000);
        }

        // 获取Cookie值的辅助函数
        function getCookie(name) {
            const value = `; ${document.cookie}`;
            const parts = value.split(`; ${name}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        }

        window.onload = function() {
            initTheme();
            switchMode('search');
            loadApiHash(); // 加载API Hash
        };
    </script>

    <!-- Floating Video Window -->
    <div id="floatingVideo" class="floating-video">
        <div class="floating-video-header">
            <div class="floating-video-title" id="floatingVideoTitle">正在播放</div>
            <div class="floating-video-controls">
                <button class="floating-control-btn" onclick="toggleFloatingVideo()">−</button>
                <button class="floating-control-btn" onclick="closeFloatingVideo()">×</button>
            </div>
        </div>
        <video id="floatingVideoPlayer" controls></video>
    </div>
</body>
</html>
"""

def get_web_ui_html():
    """返回Web UI的HTML内容"""
    return HTML_TEMPLATE

def get_login_page_html():
    """返回访问密码登录页面（匹配主UI风格）"""
    return r"""
<!DOCTYPE html>
<html lang="zh-CN" data-theme="light">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>访问验证 - NCM Video Service</title>
    <style>
        :root {
            --bg-color: #fff;
            --text-primary: #171717;
            --text-secondary: #666;
            --border-color: #eaeaea;
            --accent-color: #000;
            --accent-hover: #333;
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

        html {
            background-color: var(--bg-color);
            transition: background-color 0.3s ease;
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
            align-items: center;
            justify-content: center;
            padding: 20px;
            transition: background-color 0.3s ease, color 0.3s ease;
            position: relative;
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

        .login-container {
            background: rgba(255, 255, 255, 0.9);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            box-shadow: var(--shadow-md);
            padding: 40px;
            width: 100%;
            max-width: 420px;
            animation: slideIn 0.5s ease;
            backdrop-filter: blur(8px);
            transition: var(--transition);
        }

        [data-theme="dark"] .login-container {
            background: rgba(17, 17, 17, 0.9);
            box-shadow: 0 4px 20px rgba(0,0,0,0.8);
        }

        .login-container:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }

        [data-theme="dark"] .login-container:hover {
            box-shadow: 0 8px 30px rgba(0,0,0,0.8);
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }

        .logo {
            text-align: center;
            margin-bottom: 30px;
        }

        .logo h1 {
            font-size: 2rem;
            font-weight: 800;
            letter-spacing: -0.05rem;
            margin-bottom: 8px;
            background: linear-gradient(180deg, #555 0%, #000 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        [data-theme="dark"] .logo h1 {
            background: linear-gradient(180deg, #fff 0%, #ccc 100%);
            background-clip: text;
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }

        .logo p {
            color: var(--text-secondary);
            font-size: 0.95rem;
        }

        .form-group {
            margin-bottom: 20px;
        }

        .form-group label {
            display: block;
            margin-bottom: 8px;
            color: var(--text-primary);
            font-weight: 500;
            font-size: 0.9rem;
        }

        .form-group input {
            width: 100%;
            height: 48px;
            padding: 0 16px;
            border: 1px solid var(--border-color);
            border-radius: var(--radius);
            font-size: 1rem;
            transition: var(--transition);
            outline: none;
            background: var(--bg-color);
            color: var(--text-primary);
        }

        .form-group input::placeholder {
            color: var(--text-secondary);
        }

        .form-group input:focus {
            border-color: var(--text-primary);
            box-shadow: 0 0 0 2px rgba(0,0,0,0.1);
        }

        [data-theme="dark"] .form-group input:focus {
            box-shadow: 0 0 0 2px rgba(255,255,255,0.1);
        }

        .btn {
            width: 100%;
            height: 48px;
            padding: 0 24px;
            background: var(--text-primary);
            color: var(--bg-color);
            border: 1px solid transparent;
            border-radius: var(--radius);
            font-size: 0.95rem;
            font-weight: 600;
            cursor: pointer;
            transition: var(--transition);
            margin-top: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .btn:hover {
            background: var(--accent-hover);
            transform: translateY(-1px);
        }

        .btn:active {
            transform: translateY(0);
        }

        .btn:disabled {
            background: var(--text-secondary);
            cursor: not-allowed;
            transform: none;
            opacity: 0.6;
        }

        .error-message {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            color: #dc2626;
            padding: 12px;
            border-radius: var(--radius);
            margin-bottom: 20px;
            font-size: 0.9rem;
            display: none;
            animation: shake 0.4s ease;
        }

        [data-theme="dark"] .error-message {
            background: rgba(239, 68, 68, 0.15);
            color: #f87171;
        }

        @keyframes shake {
            0%, 100% { transform: translateX(0); }
            25% { transform: translateX(-8px); }
            75% { transform: translateX(8px); }
        }

        .info-message {
            background: rgba(0, 112, 243, 0.05);
            border: 1px solid rgba(0, 112, 243, 0.2);
            color: var(--text-secondary);
            padding: 12px;
            border-radius: var(--radius);
            margin-top: 20px;
            font-size: 0.85rem;
            text-align: center;
            line-height: 1.6;
        }

        [data-theme="dark"] .info-message {
            background: rgba(0, 112, 243, 0.1);
        }

        .info-message strong {
            color: var(--text-primary);
            font-family: 'Courier New', monospace;
            background: rgba(0,0,0,0.05);
            padding: 2px 6px;
            border-radius: 3px;
        }

        [data-theme="dark"] .info-message strong {
            background: rgba(255,255,255,0.1);
        }

        .loading {
            display: inline-block;
            width: 14px;
            height: 14px;
            border: 2px solid var(--bg-color);
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.6s linear infinite;
            margin-right: 8px;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .success-icon {
            display: inline-block;
            margin-right: 6px;
        }
    </style>
</head>
<body>
    <!-- Theme Toggle -->
    <button class="theme-toggle" onclick="toggleTheme()" aria-label="Toggle theme">
        <svg id="sunIcon" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        </svg>
        <svg id="moonIcon" style="display: none;" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        </svg>
    </button>

    <div class="login-container">
        <div class="logo">
            <h1>🎵 NCM Video Service</h1>
            <p>请输入访问密码继续</p>
        </div>

        <div id="errorMessage" class="error-message"></div>

        <form id="loginForm">
            <div class="form-group">
                <label for="password">访问密码</label>
                <input 
                    type="password" 
                    id="password" 
                    name="password" 
                    placeholder="请输入访问密码"
                    required
                    autocomplete="off"
                >
            </div>

            <button type="submit" class="btn" id="submitBtn">
                <span id="btnText">进入系统</span>
            </button>
        </form>

        <div class="info-message">
            💡 请联系管理员获取访问密码<br>
            首次部署后，管理员可在服务器日志中查看初始密码
        </div>
    </div>

    <script>
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
        const form = document.getElementById('loginForm');
        const passwordInput = document.getElementById('password');
        const submitBtn = document.getElementById('submitBtn');
        const btnText = document.getElementById('btnText');
        const errorMessage = document.getElementById('errorMessage');

        // Initialize theme and focus
        initTheme();
        passwordInput.focus();

        form.addEventListener('submit', async (e) => {
            e.preventDefault();

            const password = passwordInput.value.trim();
            if (!password) {
                showError('请输入密码');
                return;
            }

            // Show loading state
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
                    // 存储hash到localStorage
                    if (data.hash) {
                        localStorage.setItem('access_hash', data.hash);
                    }
                    
                    // 验证成功，直接跳转
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

        // Enter key submit
        passwordInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                form.dispatchEvent(new Event('submit'));
            }
        });
    </script>
</body>
</html>
"""
