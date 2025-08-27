// Global variables for queue system
let currentPlaylist = [];
let currentSongIndex = -1;
let isPlaying = false;
let audio = new Audio();
let isShuffle = false;
let isRepeat = false;

// Initialize queue from page songs
function initializeQueue() {
    const songElements = document.querySelectorAll('.play-btn');
    currentPlaylist = Array.from(songElements).map((btn, index) => ({
        id: btn.dataset.songId,
        audioUrl: btn.dataset.audioUrl,
        title: btn.dataset.title,
        artist: btn.dataset.artist,
        coverUrl: btn.dataset.coverUrl,
        index: index
    }));
    
    console.log('Queue initialized with', currentPlaylist.length, 'songs');
}

// Play song from queue
async function playSongFromQueue(songId) {
    const songIndex = currentPlaylist.findIndex(song => song.id === songId);
    if (songIndex === -1) {
        console.error('Song not found in queue');
        return;
    }
    
    currentSongIndex = songIndex;
    await playCurrentSong();
}

// Play current song in queue
async function playCurrentSong() {
    if (currentSongIndex === -1 || currentPlaylist.length === 0) return;
    
    const song = currentPlaylist[currentSongIndex];
    
    try {
        // Update audio source
        audio.src = song.audioUrl;
        audio.currentTime = 0;
        
        // Track stream
        await fetch(`/stream/${song.id}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        // Update player UI
        updatePlayerInfo(song);
        updatePlayButtons();
        
        // Play audio
        await audio.play();
        isPlaying = true;
        showPlayer();
        
    } catch (error) {
        console.error('Error playing song:', error);
    }
}

// Play next song in queue
async function playNextSong() {
    if (currentPlaylist.length === 0) return;
    
    if (isRepeat) {
        // Repeat current song
        await playCurrentSong();
        return;
    }
    
    if (isShuffle) {
        // Play random song
        const randomIndex = Math.floor(Math.random() * currentPlaylist.length);
        currentSongIndex = randomIndex;
    } else {
        // Play next song in order
        currentSongIndex = (currentSongIndex + 1) % currentPlaylist.length;
    }
    
    await playCurrentSong();
}

// Play previous song in queue
async function playPreviousSong() {
    if (currentPlaylist.length === 0) return;
    
    if (audio.currentTime > 3) {
        // If more than 3 seconds played, restart current song
        audio.currentTime = 0;
        return;
    }
    
    if (isShuffle) {
        // Play random song
        const randomIndex = Math.floor(Math.random() * currentPlaylist.length);
        currentSongIndex = randomIndex;
    } else {
        // Play previous song in order
        currentSongIndex = (currentSongIndex - 1 + currentPlaylist.length) % currentPlaylist.length;
    }
    
    await playCurrentSong();
}

// Toggle play/pause
function togglePlayPause() {
    if (currentSongIndex === -1) {
        // If no song is selected, play first song
        if (currentPlaylist.length > 0) {
            currentSongIndex = 0;
            playCurrentSong();
        }
        return;
    }
    
    if (isPlaying) {
        audio.pause();
    } else {
        audio.play().catch(console.error);
    }
    isPlaying = !isPlaying;
    updatePlayButtons();
}

// Update player info
function updatePlayerInfo(song) {
    const cover = document.getElementById('player-cover');
    const title = document.getElementById('player-title');
    const artist = document.getElementById('player-artist');
    
    if (cover) cover.src = song.coverUrl || 'https://via.placeholder.com/40x40';
    if (title) title.textContent = song.title || 'Unknown Title';
    if (artist) artist.textContent = song.artist || 'Unknown Artist';
    
    // Update like button if needed
    updateLikeButton(song.id);
}

// Update play buttons
function updatePlayButtons() {
    const playBtn = document.getElementById('player-play');
    if (!playBtn) return;
    
    const icon = playBtn.querySelector('i');
    if (isPlaying) {
        icon.classList.replace('fa-play', 'fa-pause');
    } else {
        icon.classList.replace('fa-pause', 'fa-play');
    }
}

// Show player
function showPlayer() {
    const player = document.getElementById('music-player');
    if (player) {
        player.style.display = 'flex';
    }
}

// Update like button
function updateLikeButton(songId) {
    const likeBtn = document.querySelector('.player-like-btn');
    if (likeBtn) {
        // Check if song is liked (you'll need to implement this)
        const isLiked = false; // Replace with actual check
        likeBtn.classList.toggle('liked', isLiked);
        likeBtn.innerHTML = isLiked ? 
            '<i class="fas fa-heart"></i>' : 
            '<i class="far fa-heart"></i>';
    }
}

// Event listeners for audio
audio.addEventListener('ended', () => {
    isPlaying = false;
    playNextSong();
});

audio.addEventListener('timeupdate', () => {
    updateProgressBar();
});

audio.addEventListener('loadedmetadata', () => {
    updateDurationDisplay();
});

// Update progress bar
function updateProgressBar() {
    const progressBar = document.querySelector('.progress-fill');
    const currentTime = document.getElementById('player-current-time');
    
    if (progressBar && audio.duration) {
        const progress = (audio.currentTime / audio.duration) * 100;
        progressBar.style.width = `${progress}%`;
    }
    
    if (currentTime) {
        currentTime.textContent = formatTime(audio.currentTime);
    }
}

// Update duration display
function updateDurationDisplay() {
    const totalTime = document.getElementById('player-total-time');
    if (totalTime && audio.duration) {
        totalTime.textContent = formatTime(audio.duration);
    }
}

// Format time (MM:SS)
function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    initializeQueue();
    setupEventListeners();
});

// Setup event listeners
function setupEventListeners() {
    // Play buttons on song cards
    document.querySelectorAll('.play-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const songId = e.currentTarget.dataset.songId;
            playSongFromQueue(songId);
        });
    });
    
    // Player controls
    const playBtn = document.getElementById('player-play');
    const prevBtn = document.getElementById('player-prev');
    const nextBtn = document.getElementById('player-next');
    
    if (playBtn) playBtn.addEventListener('click', togglePlayPause);
    if (prevBtn) prevBtn.addEventListener('click', playPreviousSong);
    if (nextBtn) nextBtn.addEventListener('click', playNextSong);
    
    // Progress bar seeking
    const progressBar = document.querySelector('.progress-bar');
    if (progressBar) {
        progressBar.addEventListener('click', (e) => {
            if (audio.duration) {
                const rect = progressBar.getBoundingClientRect();
                const clickPosition = (e.clientX - rect.left) / rect.width;
                audio.currentTime = clickPosition * audio.duration;
            }
        });
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
        
        switch(e.code) {
            case 'Space':
                e.preventDefault();
                togglePlayPause();
                break;
            case 'ArrowRight':
                e.preventDefault();
                playNextSong();
                break;
            case 'ArrowLeft':
                e.preventDefault();
                playPreviousSong();
                break;
        }
    });
}

// Shuffle functionality
function toggleShuffle() {
    isShuffle = !isShuffle;
    const shuffleBtn = document.querySelector('.control-btn.shuffle');
    if (shuffleBtn) {
        shuffleBtn.classList.toggle('active', isShuffle);
    }
}

// Repeat functionality
function toggleRepeat() {
    isRepeat = !isRepeat;
    const repeatBtn = document.querySelector('.control-btn.repeat');
    if (repeatBtn) {
        repeatBtn.classList.toggle('active', isRepeat);
    }
}

// Add to queue function (for future use)
function addToQueue(song, playNext = false) {
    if (playNext) {
        // Add after current song
        currentPlaylist.splice(currentSongIndex + 1, 0, song);
    } else {
        // Add to end of queue
        currentPlaylist.push(song);
    }
}

// Remove from queue function
function removeFromQueue(songId) {
    const index = currentPlaylist.findIndex(song => song.id === songId);
    if (index !== -1) {
        currentPlaylist.splice(index, 1);
        if (currentSongIndex >= index) {
            currentSongIndex--;
        }
    }
}

// Clear queue function
function clearQueue() {
    currentPlaylist = [];
    currentSongIndex = -1;
    audio.pause();
    isPlaying = false;
    updatePlayButtons();
}