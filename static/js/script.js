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
let currentPlaylist = [];
let currentSongIndex = -1;
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

// Mobile menu functionality
const mobileMenuButton = document.querySelector('.mobile-menu-button');
const mobileMenu = document.querySelector('.mobile-menu');

if (mobileMenuButton && mobileMenu) {
    mobileMenuButton.addEventListener('click', (e) => {
        e.stopPropagation();
        mobileMenu.classList.toggle('active');
        document.body.style.overflow = mobileMenu.classList.contains('active') ? 'hidden' : '';
    });

    // Close mobile menu when clicking outside
    document.addEventListener('click', (e) => {
        if (mobileMenu.classList.contains('active') && 
            !e.target.closest('.mobile-menu') && 
            !e.target.closest('.mobile-menu-button')) {
            mobileMenu.classList.remove('active');
            document.body.style.overflow = '';
        }
    });
}

// Format time (seconds to MM:SS)
function formatTime(seconds) {
    if (isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
}

// Play song function
async function playSong(songId, audioUrl, title, artist, coverUrl) {
    try {
        if (currentSong !== songId) {
            audio.src = audioUrl;
            currentSong = songId;
            
            // Track stream
            const streamResponse = await fetch(`/stream/${songId}`, { 
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            const streamData = await streamResponse.json();
            if (!streamData.success) {
                console.error('Error tracking stream:', streamData.error);
            }
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
        await audio.play();
        isPlaying = true;
        updatePlayButtons();
        
    } catch (error) {
        console.error('Error playing song:', error);
    }
}

// Update play/pause buttons
function updatePlayButtons() {
    const playIcon = isPlaying ? '<i class="fas fa-pause"></i>' : '<i class="fas fa-play"></i>';
    if (playerPlayBtn) playerPlayBtn.innerHTML = playIcon;
    if (fullscreenPlayBtn) fullscreenPlayBtn.innerHTML = playIcon;
}

// Event listeners for audio element
audio.addEventListener('loadedmetadata', () => {
    if (playerTotalTime) playerTotalTime.textContent = formatTime(audio.duration);
    if (fullscreenTotalTime) fullscreenTotalTime.textContent = formatTime(audio.duration);
});

audio.addEventListener('timeupdate', () => {
    const progress = (audio.currentTime / audio.duration) * 100;
    if (playerProgress) playerProgress.style.width = `${progress}%`;
    if (fullscreenProgress) fullscreenProgress.style.width = `${progress}%`;
    if (playerCurrentTime) playerCurrentTime.textContent = formatTime(audio.currentTime);
    if (fullscreenCurrentTime) fullscreenCurrentTime.textContent = formatTime(audio.currentTime);
});

audio.addEventListener('ended', () => {
    isPlaying = false;
    updatePlayButtons();
    playNextSong();
});

audio.addEventListener('error', (e) => {
    console.error('Audio error:', e);
    isPlaying = false;
    updatePlayButtons();
});

// Play button click
if (playerPlayBtn) {
    playerPlayBtn.addEventListener('click', () => {
        togglePlayPause();
    });
}

if (fullscreenPlayBtn) {
    fullscreenPlayBtn.addEventListener('click', () => {
        togglePlayPause();
    });
}

function togglePlayPause() {
    if (isPlaying) {
        audio.pause();
    } else {
        audio.play().catch(error => {
            console.error('Play failed:', error);
        });
    }
    isPlaying = !isPlaying;
    updatePlayButtons();
}

// Volume control
if (playerVolume) {
    playerVolume.addEventListener('input', () => {
        audio.volume = playerVolume.value / 100;
    });
}

if (playerVolumeBtn) {
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
}

// Fullscreen player
if (fullscreenPlayerBtn) {
    fullscreenPlayerBtn.addEventListener('click', () => {
        if (currentSong) {
            fullscreenPlayer.classList.remove('hidden');
            document.body.style.overflow = 'hidden';
        }
    });
}

if (closeFullscreen) {
    closeFullscreen.addEventListener('click', () => {
        fullscreenPlayer.classList.add('hidden');
        document.body.style.overflow = '';
    });
}

// Navigation controls
if (playerNextBtn) {
    playerNextBtn.addEventListener('click', playNextSong);
}

if (fullscreenNextBtn) {
    fullscreenNextBtn.addEventListener('click', playNextSong);
}

if (playerPrevBtn) {
    playerPrevBtn.addEventListener('click', playPreviousSong);
}

if (fullscreenPrevBtn) {
    fullscreenPrevBtn.addEventListener('click', playPreviousSong);
}

function playNextSong() {
    // This would need implementation based on your playlist structure
    console.log('Next song functionality would go here');
}

function playPreviousSong() {
    // This would need implementation based on your playlist structure
    console.log('Previous song functionality would go here');
}

// Play buttons on song cards
document.addEventListener('click', (e) => {
    const playBtn = e.target.closest('.play-btn');
    if (playBtn) {
        const songId = playBtn.dataset.songId;
        const audioUrl = playBtn.dataset.audioUrl;
        const title = playBtn.dataset.title;
        const artist = playBtn.dataset.artist;
        const coverUrl = playBtn.dataset.coverUrl;
        
        playSong(songId, audioUrl, title, artist, coverUrl);
    }
});

// Like buttons
document.addEventListener('click', async (e) => {
    const likeBtn = e.target.closest('.like-btn');
    if (likeBtn) {
        e.preventDefault();
        const songId = likeBtn.dataset.songId;
        const heartIcon = likeBtn.querySelector('i');
        const likeCount = likeBtn.querySelector('.like-count');
        
        // Show loading state
        const originalHtml = likeBtn.innerHTML;
        likeBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        likeBtn.disabled = true;
        
        try {
            const response = await fetch(`/like/${songId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            });
            
            const data = await response.json();
            
            if (data.success) {
                likeCount.textContent = data.likes;
                
                if (data.liked) {
                    heartIcon.classList.remove('far');
                    heartIcon.classList.add('fas', 'text-purple-600');
                    likeBtn.classList.add('text-purple-600');
                } else {
                    heartIcon.classList.remove('fas', 'text-purple-600');
                    heartIcon.classList.add('far');
                    likeBtn.classList.remove('text-purple-600');
                }
            } else {
                console.error('Error liking song:', data.error);
                // Show error message to user
                showNotification('Error liking song. Please try again.', 'error');
            }
        } catch (error) {
            console.error('Error:', error);
            showNotification('Network error. Please try again.', 'error');
        } finally {
            // Restore original button state
            likeBtn.innerHTML = originalHtml;
            likeBtn.disabled = false;
        }
    }
});

// Helper function to show notifications
function showNotification(message, type = 'info') {
    // Remove existing notifications
    const existingNotifications = document.querySelectorAll('.custom-notification');
    existingNotifications.forEach(notif => notif.remove());
    
    // Create new notification
    const notification = document.createElement('div');
    notification.className = `custom-notification fixed top-4 right-4 z-50 px-4 py-3 rounded-md shadow-lg ${
        type === 'error' ? 'bg-red-100 border border-red-400 text-red-700' : 
        type === 'success' ? 'bg-green-100 border border-green-400 text-green-700' :
        'bg-blue-100 border border-blue-400 text-blue-700'
    }`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        notification.remove();
    }, 5000);
}
// Share functionality
document.addEventListener('click', async (e) => {
    const shareBtn = e.target.closest('.share-btn');
    if (shareBtn) {
        const songId = shareBtn.dataset.songId;
        const title = shareBtn.dataset.title;
        const artist = shareBtn.dataset.artist;
        
        try {
            // Create share URL
            const shareUrl = `${window.location.origin}/?share=${songId}`;
            const shareText = `Check out "${title}" by ${artist} on Shallarr Music!`;
            
            // Use Web Share API if available
            if (navigator.share) {
                await navigator.share({
                    title: 'Shallarr Music',
                    text: shareText,
                    url: shareUrl
                });
            } else {
                // Fallback: copy to clipboard
                await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
                alert('Link copied to clipboard!');
            }
        } catch (error) {
            console.error('Error sharing:', error);
            // Fallback: copy to clipboard
            const shareUrl = `${window.location.origin}/?share=${songId}`;
            const shareText = `Check out "${title}" by ${artist} on Shallarr Music!`;
            await navigator.clipboard.writeText(`${shareText} ${shareUrl}`);
            alert('Link copied to clipboard!');
        }
    }
});

// Close flash messages
document.querySelectorAll('.close-flash').forEach(btn => {
    btn.addEventListener('click', (e) => {
        e.currentTarget.parentElement.style.display = 'none';
    });
});

// Auto-hide flash messages after 5 seconds
setTimeout(() => {
    document.querySelectorAll('.fixed.top-4.right-4 > div').forEach(flash => {
        flash.style.display = 'none';
    });
}, 5000);

// Initialize volume
if (audio) {
    audio.volume = 0.8;
}

// Handle page visibility changes for audio playback
document.addEventListener('visibilitychange', () => {
    if (document.hidden && isPlaying) {
        audio.pause();
    } else if (!document.hidden && !isPlaying && currentSong) {
        audio.play().catch(console.error);
    }
});

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

// Handle share parameter in URL
function handleShareParameter() {
    const urlParams = new URLSearchParams(window.location.search);
    const shareId = urlParams.get('share');
    
    if (shareId) {
        // Scroll to the shared song if it exists
        const sharedSong = document.querySelector(`.play-btn[data-song-id="${shareId}"]`);
        if (sharedSong) {
            sharedSong.scrollIntoView({ behavior: 'smooth' });
            // Highlight the shared song
            sharedSong.closest('.bg-white').classList.add('ring-2', 'ring-purple-500');
            setTimeout(() => {
                sharedSong.closest('.bg-white').classList.remove('ring-2', 'ring-purple-500');
            }, 3000);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    handleShareParameter();
    
    // Preload audio for better performance
    if (audio) {
        audio.preload = 'metadata';
    }
});