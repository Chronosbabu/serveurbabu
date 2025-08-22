document.addEventListener('DOMContentLoaded', () => {
    const currentUsername = document.body.dataset.username;

    // ------------------ Gestion des likes ------------------
    async function toggleLike(button) {
        const post = button.closest('.post');
        const postId = post.dataset.postId;
        const countEl = post.querySelector('.like-count');

        try {
            const res = await fetch(`/like/${postId}`, { method: 'POST' });
            if (!res.ok) return;
            const data = await res.json();
            countEl.textContent = data.likes;
            if (data.liked) button.classList.add('liked');
            else button.classList.remove('liked');
        } catch (err) {
            console.error("Erreur like:", err);
        }
    }

    document.querySelectorAll('.post').forEach(post => {
        const likeBtn = post.querySelector('.like-btn');
        if (likeBtn) likeBtn.addEventListener('click', () => toggleLike(likeBtn));
    });

    const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');

    // ------------------ Gestion des vidéos ------------------
    const allVideos = new Set(document.querySelectorAll('.post video'));

    function stopAllVideosExcept(currentVideo) {
        allVideos.forEach(video => {
            if (video !== currentVideo) {
                video.pause();
                video.currentTime = 0;
            }
        });
    }

    function handleVideoVisibility() {
        let videoToPlay = null;
        allVideos.forEach(video => {
            const rect = video.getBoundingClientRect();
            const partiallyVisible = rect.bottom > 0 && rect.top < window.innerHeight;
            if (partiallyVisible && !videoToPlay) videoToPlay = video;
        });
        allVideos.forEach(video => {
            if (video === videoToPlay) video.play();
            else {
                video.pause();
                video.currentTime = 0;
            }
        });
    }

    // Observer pour ajouter dynamiquement les vidéos
    if (postsContainer) {
        const observer = new MutationObserver(mutations => {
            mutations.forEach(m => {
                m.addedNodes.forEach(node => {
                    if (node.nodeType === 1 && node.classList.contains('post')) {
                        const video = node.querySelector('video');
                        if (video) allVideos.add(video);

                        const likeBtn = node.querySelector('.like-btn');
                        if (likeBtn) likeBtn.addEventListener('click', () => toggleLike(likeBtn));
                    }
                });
            });
            handleVideoVisibility(); // Vérifie à chaque ajout
        });
        observer.observe(postsContainer, { childList: true, subtree: true });
    }

    window.addEventListener('scroll', handleVideoVisibility);
    window.addEventListener('resize', handleVideoVisibility);
    handleVideoVisibility(); // Vérification initiale
});

