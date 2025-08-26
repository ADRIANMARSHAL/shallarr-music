// Theme toggle
const themeToggle = document.getElementById('theme-toggle');
const html = document.documentElement;

// Check for saved theme preference or respect OS preference
if (localStorage.theme === 'dark' || (!('theme' in localStorage) && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
    html.classList.add('dark');
} else {
    html.classList.remove('dark');
}

themeToggle.addEventListener('click', () => {
    html.classList.toggle('dark');
    localStorage.theme = html.classList.contains('dark') ? 'dark' : 'light';
});

// Music player functionality
let currentSong = null;
let isPlaying = false;
const audio = document.getElementById('audio-element');
const player = document.getElementById('music-player');
const playerTitle = document.getElementById('player-title');
const playerArtist = document.getElementById('player-artist');
const playerCover = document.getElementById('player-cover');
const playerPlayBtn = document.getElementById('player-play');
const playerPrevBtn = document.getElementById('player-prev');
const playerNextBtn = document.getElementById('player-next');
const playerProgress = document.getElementById('player-progress');
const playerCurrentTime = document.getElementById('player-current-time');
const playerTotalTime = document.getElementById('player-total-time');
const playerVolume = document.getElementById('player-volume');
const playerVolumeBtn = document.getElementById('player-volume-btn');

// Fullscreen player elements
const fullscreenPlayer = document.getElementById('fullscreen-player');
const fullscreenPlayerBtn = document.getElementById('fullscreen-player-btn');
const closeFullscreen = document.getElementById('close-fullscreen');
const fullscreenCover = document.getElementById('fullscreen-cover');
const fullscreenTitle = document.getElementById('fullscreen-title');
const fullscreenArtist = document.getElementById('fullscreen-artist');
const fullscreenPlayBtn = document.getElementById('fullscreen-play');
const fullscreenPrevBtn = document.getElementById('fullscreen-prev');
const fullscreenNextBtn = document.getElementById('fullscreen-next');
const fullscreenProgress = document.getElementById('fullscreen-progress');
const fullscreenCurrentTime = document.getElementById('fullscreen-current-time');
const fullscreenTotalTime = document.getElementById('fullscreen-total-time');

// Play song function
function playSong(songId, audioUrl, title, artist, coverUrl) {
    if (currentSong !== songId) {
        audio.src = audioUrl;
        currentSong = songId;
        
        // Track stream
        fetch(`/stream/${songId}`, { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (!data.success) {
                    console.error('Error tracking stream:', data.error);
                }
            });
    }
    
    // Update player UI
    playerTitle.textContent = title;
    playerArtist.textContent = artist;
    playerCover.src = coverUrl;
    fullscreenTitle.textContent = title;
    fullscreenArtist.textContent = artist;
    fullscreenCover.src = coverUrl;
    
    // Show player if hidden
    player.classList.remove('hidden');
    
    // Play audio
    audio.play();
    isPlaying = true;
    updatePlayButtons();
}

// Update play/pause buttons
function updatePlayButtons() {
    if (isPlaying) {
        playerPlayBtn.innerHTML = '<i class="fas fa-pause"></i>';
        fullscreenPlayBtn.innerHTML = '<i class="fas fa-pause"></i>';
    } else {
        playerPlayBtn.innerHTML = '<i class="fas fa-play"></i>';
        fullscreenPlayBtn.innerHTML = '<i class="fas fa-play"></i>';
    }
}

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// Event listeners for audio element
audio.addEventListener('loadedmetadata', () => {
    playerTotalTime.textContent = formatTime(audio.duration);
    fullscreenTotalTime.textContent = formatTime(audio.duration);
});

audio.addEventListener('timeupdate', () => {
    const progress = (audio.currentTime / audio.duration) * 100;
    playerProgress.style.width = `${progress}%`;
    fullscreenProgress.style.width = `${progress}%`;
    playerCurrentTime.textContent = formatTime(audio.currentTime);
    fullscreenCurrentTime.textContent = formatTime(audio.currentTime);
});

audio.addEventListener('ended', () => {
    isPlaying = false;
    updatePlayButtons();
    // Auto-play next song if available
    // This would need implementation based on your song list
});

// Play button click
playerPlayBtn.addEventListener('click', () => {
    if (isPlaying) {
        audio.pause();
    } else {
        audio.play();
    }
    isPlaying = !isPlaying;
    updatePlayButtons();
});

fullscreenPlayBtn.addEventListener('click', () => {
    if (isPlaying) {
        audio.pause();
    } else {
        audio.play();
    }
    isPlaying = !isPlaying;
    updatePlayButtons();
});

// Volume control
playerVolume.addEventListener('input', () => {
    audio.volume = playerVolume.value / 100;
});

playerVolumeBtn.addEventListener('click', () => {
    if (audio.volume > 0) {
        audio.volume = 0;
        playerVolume.value = 0;
        playerVolumeBtn.innerHTML = '<i class="fas fa-volume-mute"></i>';
    } else {
        audio.volume = 0.8;
        playerVolume.value = 80;
        playerVolumeBtn.innerHTML = '<i class="fas fa-volume-up"></i>';
    }
});

// Fullscreen player
fullscreenPlayerBtn.addEventListener('click', () => {
    if (currentSong) {
        fullscreenPlayer.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }
});

closeFullscreen.addEventListener('click', () => {
    fullscreenPlayer.classList.add('hidden');
    document.body.style.overflow = 'auto';
});

// Play buttons on song cards
document.querySelectorAll('.play-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const songId = e.currentTarget.dataset.songId;
        const audioUrl = e.currentTarget.dataset.audioUrl;
        const title = e.currentTarget.dataset.title;
        const artist = e.currentTarget.dataset.artist;
        const coverUrl = e.currentTarget.dataset.coverUrl;
        
        playSong(songId, audioUrl, title, artist, coverUrl);
    });
});

// Like buttons
document.querySelectorAll('.like-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
        e.preventDefault();
        const songId = e.currentTarget.dataset.songId;
        const heartIcon = e.currentTarget.querySelector('i');
        const likeCount = e.currentTarget.querySelector('.like-count');
        
        try {
            const response = await fetch(`/like/${songId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                likeCount.textContent = data.likes;
                
                if (data.liked) {
                    heartIcon.classList.remove('far');
                    heartIcon.classList.add('fas', 'text-purple-600');
                } else {
                    heartIcon.classList.remove('fas', 'text-purple-600');
                    heartIcon.classList.add('far');
                }
            } else {
                console.error('Error liking song:', data.error);
            }
        } catch (error) {
            console.error('Error:', error);
        }
    });
});

// Close flash messages
document.querySelectorAll('.close-flash').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.currentTarget.parentElement.style.display = 'none';
    });
});