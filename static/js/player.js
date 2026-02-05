// Alpine.js Music Player Component
function musicPlayer() {
    return {
        // State
        currentSong: null,
        queue: [],
        isPlaying: false,
        currentTime: 0,
        duration: 0,
        volume: 80,
        isMuted: false,
        shuffle: false,
        repeatMode: 'off', // 'off', 'all', 'one'
        showQueue: false,
        currentIndex: 0,

        // Initialize
        init() {
            // Load saved state from localStorage
            this.loadState();
            
            // Set initial volume
            this.$refs.audio.volume = this.volume / 100;
            
            // Listen for global play events from song cards
            window.addEventListener('play-song', (e) => {
                this.playSong(e.detail.song);
            });

            // Listen for add to queue events
            window.addEventListener('add-to-queue', (e) => {
                this.addToQueue(e.detail.song);
            });

            // Save state when page unloads
            window.addEventListener('beforeunload', () => {
                this.saveState();
            });

            // Keyboard shortcuts
            document.addEventListener('keydown', (e) => {
                if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
                
                if (e.code === 'Space' && this.currentSong) {
                    e.preventDefault();
                    this.togglePlay();
                } else if (e.code === 'ArrowRight' && this.currentSong) {
                    e.preventDefault();
                    this.nextTrack();
                } else if (e.code === 'ArrowLeft' && this.currentSong) {
                    e.preventDefault();
                    this.previousTrack();
                }
            });
        },

        // Play a song
        playSong(song) {
            if (!song) return;

            // If song is not in queue, add it and play
            const songInQueue = this.queue.findIndex(s => s.id === song.id);
            
            if (songInQueue === -1) {
                this.queue.push(song);
                this.currentIndex = this.queue.length - 1;
            } else {
                this.currentIndex = songInQueue;
            }

            this.currentSong = song;
            this.$refs.audio.src = song.audio_url;
            this.$refs.audio.play().then(() => {
                this.isPlaying = true;
                this.incrementStreamCount(song.id);
            }).catch(error => {
                console.error('Error playing song:', error);
            });

            this.saveState();
        },

        // Add song to queue
        addToQueue(song) {
            if (!song) return;
            
            const exists = this.queue.find(s => s.id === song.id);
            if (!exists) {
                this.queue.push(song);
                this.saveState();
                this.showNotification(`Added "${song.title}" to queue`);
            } else {
                this.showNotification(`"${song.title}" is already in queue`);
            }
        },

        // Play song from queue by index
        playSongFromQueue(index) {
            if (index >= 0 && index < this.queue.length) {
                this.currentIndex = index;
                this.playSong(this.queue[index]);
            }
        },

        // Remove from queue
        removeFromQueue(index) {
            if (index === this.currentIndex && this.isPlaying) {
                this.showNotification("Can't remove currently playing song");
                return;
            }

            this.queue.splice(index, 1);
            
            // Adjust current index if needed
            if (index < this.currentIndex) {
                this.currentIndex--;
            }

            this.saveState();
        },

        // Clear queue
        clearQueue() {
            if (confirm('Clear entire queue?')) {
                const currentSong = this.currentSong;
                this.queue = currentSong ? [currentSong] : [];
                this.currentIndex = 0;
                this.saveState();
            }
        },

        // Toggle play/pause
        togglePlay() {
            if (!this.currentSong) return;

            if (this.isPlaying) {
                this.$refs.audio.pause();
                this.isPlaying = false;
            } else {
                this.$refs.audio.play().then(() => {
                    this.isPlaying = true;
                }).catch(error => {
                    console.error('Error playing:', error);
                });
            }
        },

        // Next track
        nextTrack() {
            if (this.queue.length === 0) return;

            if (this.shuffle) {
                // Random next song (but not current)
                let nextIndex;
                do {
                    nextIndex = Math.floor(Math.random() * this.queue.length);
                } while (nextIndex === this.currentIndex && this.queue.length > 1);
                
                this.currentIndex = nextIndex;
            } else {
                this.currentIndex = (this.currentIndex + 1) % this.queue.length;
            }

            this.playSong(this.queue[this.currentIndex]);
        },

        // Previous track
        previousTrack() {
            if (this.queue.length === 0) return;

            // If more than 3 seconds played, restart current song
            if (this.currentTime > 3) {
                this.$refs.audio.currentTime = 0;
                return;
            }

            if (this.shuffle) {
                // Random previous
                let prevIndex;
                do {
                    prevIndex = Math.floor(Math.random() * this.queue.length);
                } while (prevIndex === this.currentIndex && this.queue.length > 1);
                
                this.currentIndex = prevIndex;
            } else {
                this.currentIndex = this.currentIndex - 1;
                if (this.currentIndex < 0) {
                    this.currentIndex = this.queue.length - 1;
                }
            }

            this.playSong(this.queue[this.currentIndex]);
        },

        // Handle song end
        handleSongEnd() {
            if (this.repeatMode === 'one') {
                this.$refs.audio.currentTime = 0;
                this.$refs.audio.play();
            } else if (this.repeatMode === 'all' || this.currentIndex < this.queue.length - 1) {
                this.nextTrack();
            } else {
                this.isPlaying = false;
            }
        },

        // Toggle shuffle
        toggleShuffle() {
            this.shuffle = !this.shuffle;
            this.saveState();
            this.showNotification(this.shuffle ? 'Shuffle enabled' : 'Shuffle disabled');
        },

        // Cycle repeat mode
        cycleRepeat() {
            const modes = ['off', 'all', 'one'];
            const currentModeIndex = modes.indexOf(this.repeatMode);
            this.repeatMode = modes[(currentModeIndex + 1) % modes.length];
            this.saveState();
            
            const messages = {
                'off': 'Repeat off',
                'all': 'Repeat all',
                'one': 'Repeat one'
            };
            this.showNotification(messages[this.repeatMode]);
        },

        // Toggle queue panel
        toggleQueue() {
            this.showQueue = !this.showQueue;
        },

        // Update progress
        updateProgress() {
            this.currentTime = this.$refs.audio.currentTime;
        },

        // Audio loaded
        audioLoaded() {
            this.duration = this.$refs.audio.duration;
        },

        // Seek to position
        seek(event) {
            const rect = event.currentTarget.getBoundingClientRect();
            const percent = (event.clientX - rect.left) / rect.width;
            this.$refs.audio.currentTime = percent * this.duration;
        },

        // Set volume
        setVolume() {
            this.$refs.audio.volume = this.volume / 100;
            this.isMuted = false;
            this.saveState();
        },

        // Toggle mute
        toggleMute() {
            if (this.isMuted) {
                this.$refs.audio.volume = this.volume / 100;
                this.isMuted = false;
            } else {
                this.$refs.audio.volume = 0;
                this.isMuted = true;
            }
        },

        // Format time (seconds to MM:SS)
        formatTime(seconds) {
            if (isNaN(seconds)) return '0:00';
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}:${secs.toString().padStart(2, '0')}`;
        },

        // Progress percentage
        get progress() {
            return this.duration > 0 ? (this.currentTime / this.duration) * 100 : 0;
        },

        // Save state to localStorage
        saveState() {
            const state = {
                currentSong: this.currentSong,
                queue: this.queue,
                volume: this.volume,
                shuffle: this.shuffle,
                repeatMode: this.repeatMode,
                currentIndex: this.currentIndex
            };
            localStorage.setItem('musicPlayerState', JSON.stringify(state));
        },

        // Load state from localStorage
        loadState() {
            const saved = localStorage.getItem('musicPlayerState');
            if (saved) {
                try {
                    const state = JSON.parse(saved);
                    this.currentSong = state.currentSong || null;
                    this.queue = state.queue || [];
                    this.volume = state.volume || 80;
                    this.shuffle = state.shuffle || false;
                    this.repeatMode = state.repeatMode || 'off';
                    this.currentIndex = state.currentIndex || 0;

                    // Load the current song but don't auto-play
                    if (this.currentSong) {
                        this.$nextTick(() => {
                            this.$refs.audio.src = this.currentSong.audio_url;
                        });
                    }
                } catch (error) {
                    console.error('Error loading player state:', error);
                }
            }
        },

        // Increment stream count
        incrementStreamCount(songId) {
            fetch(`/stream/${songId}`, { method: 'POST' })
                .catch(error => console.error('Error incrementing stream count:', error));
        },

        // Show notification
        showNotification(message) {
            // Create a simple toast notification
            const toast = document.createElement('div');
            toast.className = 'fixed bottom-24 right-4 bg-gray-900 text-white px-4 py-2 rounded-lg shadow-lg z-50 animate-fade-in';
            toast.textContent = message;
            document.body.appendChild(toast);

            setTimeout(() => {
                toast.classList.add('animate-fade-out');
                setTimeout(() => toast.remove(), 300);
            }, 2000);
        }
    };
}

// Register Alpine.js component globally
document.addEventListener('alpine:init', () => {
    Alpine.data('musicPlayer', musicPlayer);
});
