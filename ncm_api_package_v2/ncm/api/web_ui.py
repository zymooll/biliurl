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
    <title>NCM Video Service - 网易云音乐视频服务</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 40px;
            animation: fadeInDown 0.8s ease;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.2);
        }
        
        .header p {
            font-size: 1.1em;
            opacity: 0.9;
        }
        
        .search-box {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            margin-bottom: 30px;
            animation: fadeInUp 0.8s ease;
        }
        
        .search-input-wrapper {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .search-input {
            flex: 1;
            padding: 15px 20px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 16px;
            transition: all 0.3s;
        }
        
        .search-input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        
        .btn {
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
            text-align: center;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-secondary {
            background: #f0f0f0;
            color: #333;
        }
        
        .btn-secondary:hover {
            background: #e0e0e0;
        }
        
        .options {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: center;
        }
        
        .option {
            display: flex;
            align-items: center;
            gap: 8px;
        }
        
        .option label {
            font-size: 14px;
            color: #666;
            cursor: pointer;
        }
        
        .option input[type="checkbox"] {
            width: 18px;
            height: 18px;
            cursor: pointer;
        }
        
        .option select {
            padding: 8px 12px;
            border: 2px solid #e0e0e0;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
        }
        
        .results {
            background: white;
            border-radius: 12px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            animation: fadeInUp 0.8s ease 0.2s backwards;
        }
        
        .results-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f0f0f0;
        }
        
        .results-header h2 {
            color: #333;
            font-size: 1.5em;
        }
        
        .result-count {
            color: #666;
            font-size: 14px;
        }
        
        .song-list {
            list-style: none;
        }
        
        .song-item {
            padding: 20px;
            border-bottom: 1px solid #f0f0f0;
            transition: all 0.3s;
            cursor: pointer;
        }
        
        .song-item:hover {
            background: #f8f9fa;
            transform: translateX(5px);
        }
        
        .song-item:last-child {
            border-bottom: none;
        }
        
        .song-info {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .song-cover {
            width: 60px;
            height: 60px;
            border-radius: 8px;
            object-fit: cover;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        
        .song-details {
            flex: 1;
        }
        
        .song-name {
            font-size: 18px;
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        
        .song-artist {
            font-size: 14px;
            color: #666;
        }
        
        .song-actions {
            display: flex;
            gap: 10px;
        }
        
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        
        .spinner {
            display: inline-block;
            width: 40px;
            height: 40px;
            border: 4px solid #f3f3f3;
            border-top: 4px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        
        .empty {
            text-align: center;
            padding: 60px 20px;
            color: #999;
        }
        
        .empty-icon {
            font-size: 60px;
            margin-bottom: 20px;
        }
        
        .error {
            background: #fee;
            color: #c33;
            padding: 15px 20px;
            border-radius: 8px;
            margin-top: 20px;
            border-left: 4px solid #c33;
        }
        
        .video-player {
            margin-top: 30px;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }
        
        .video-player video {
            width: 100%;
            display: block;
        }
        
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
            margin-left: 8px;
        }
        
        .badge-mv {
            background: #ff6b6b;
            color: white;
        }
        
        .badge-vip {
            background: #ffd93d;
            color: #333;
        }
        
        @keyframes fadeInDown {
            from {
                opacity: 0;
                transform: translateY(-20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        @media (max-width: 768px) {
            .header h1 {
                font-size: 2em;
            }
            
            .search-input-wrapper {
                flex-direction: column;
            }
            
            .song-info {
                flex-direction: column;
                align-items: flex-start;
            }
            
            .song-actions {
                width: 100%;
                flex-direction: column;
            }
            
            .btn {
                width: 100%;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎵 NCM Video Service</h1>
            <p>网易云音乐视频服务 - 搜索、播放、下载</p>
        </div>
        
        <div class="search-box">
            <div class="search-input-wrapper">
                <input 
                    type="text" 
                    id="searchInput" 
                    class="search-input" 
                    placeholder="输入歌曲名、歌手名..."
                    onkeypress="if(event.key==='Enter') searchSongs()"
                >
                <button class="btn btn-primary" onclick="searchSongs()">
                    🔍 搜索
                </button>
            </div>
            
            <div class="options">
                <div class="option">
                    <input type="checkbox" id="optionMv" checked>
                    <label for="optionMv">优先 MV</label>
                </div>
                <div class="option">
                    <input type="checkbox" id="optionGpu" checked>
                    <label for="optionGpu">硬件加速</label>
                </div>
                <div class="option">
                    <label for="optionLevel">音质:</label>
                    <select id="optionLevel">
                        <option value="standard">标准</option>
                        <option value="higher">较高</option>
                        <option value="exhigh">极高</option>
                        <option value="lossless">无损</option>
                    </select>
                </div>
            </div>
        </div>
        
        <div id="results" class="results" style="display: none;">
            <div class="results-header">
                <h2>搜索结果</h2>
                <span class="result-count" id="resultCount"></span>
            </div>
            <div id="songList"></div>
        </div>
        
        <div id="videoPlayer" class="video-player" style="display: none;">
            <video id="video" controls autoplay></video>
        </div>
    </div>
    
    <script>
        let currentResults = [];
        
        async function searchSongs() {
            const keywords = document.getElementById('searchInput').value.trim();
            if (!keywords) {
                alert('请输入搜索关键词');
                return;
            }
            
            const resultsDiv = document.getElementById('results');
            const songListDiv = document.getElementById('songList');
            
            resultsDiv.style.display = 'block';
            songListDiv.innerHTML = '<div class="loading"><div class="spinner"></div><p>搜索中...</p></div>';
            
            try {
                const response = await fetch(`/search?keywords=${encodeURIComponent(keywords)}`);
                const data = await response.json();
                
                if (data.code === 200 && data.result && data.result.songs) {
                    currentResults = data.result.songs;
                    displayResults(currentResults);
                } else {
                    songListDiv.innerHTML = '<div class="empty"><div class="empty-icon">😢</div><p>未找到相关歌曲</p></div>';
                }
            } catch (error) {
                songListDiv.innerHTML = `<div class="error">搜索失败: ${error.message}</div>`;
            }
        }
        
        function displayResults(songs) {
            const songListDiv = document.getElementById('songList');
            const resultCountSpan = document.getElementById('resultCount');
            
            resultCountSpan.textContent = `共 ${songs.length} 首`;
            
            const html = '<ul class="song-list">' + songs.map(song => {
                const artists = song.ar ? song.ar.map(a => a.name).join(' / ') : '未知';
                const cover = song.al && song.al.picUrl ? song.al.picUrl : '';
                const hasMv = song.mv && song.mv > 0;
                const fee = song.fee || 0;
                
                return `
                    <li class="song-item" onclick="playSong(${song.id}, '${escapeHtml(song.name)}', '${escapeHtml(artists)}')">
                        <div class="song-info">
                            <img src="${cover}?param=60y60" class="song-cover" alt="封面" onerror="this.src='data:image/svg+xml,%3Csvg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 60 60%22%3E%3Crect fill=%22%23ddd%22 width=%2260%22 height=%2260%22/%3E%3Ctext x=%2230%22 y=%2235%22 text-anchor=%22middle%22 fill=%22%23999%22 font-size=%2220%22%3E♪%3C/text%3E%3C/svg%3E'">
                            <div class="song-details">
                                <div class="song-name">
                                    ${song.name}
                                    ${hasMv ? '<span class="badge badge-mv">MV</span>' : ''}
                                    ${fee === 1 ? '<span class="badge badge-vip">VIP</span>' : ''}
                                </div>
                                <div class="song-artist">${artists}</div>
                            </div>
                        </div>
                    </li>
                `;
            }).join('') + '</ul>';
            
            songListDiv.innerHTML = html;
        }
        
        function escapeHtml(text) {
            return text.replace(/'/g, "\\'").replace(/"/g, '&quot;');
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
            
            console.log('Playing:', name, '-', artist);
            console.log('Video URL:', videoUrl);
            
            videoPlayerDiv.style.display = 'block';
            videoElement.src = videoUrl;
            videoElement.load();
            
            // 滚动到播放器
            videoPlayerDiv.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
        
        // 页面加载时聚焦搜索框
        window.onload = function() {
            document.getElementById('searchInput').focus();
        };
    </script>
</body>
</html>
"""

def get_web_ui_html():
    """返回Web UI的HTML内容"""
    return HTML_TEMPLATE
