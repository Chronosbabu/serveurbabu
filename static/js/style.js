document.addEventListener('DOMContentLoaded', () => {
    const currentUsername = document.body.dataset.username; // username du client

    async function toggleLike(button) {
        const post = button.closest('.post');
        const postId = post.dataset.postId;
        const countEl = post.querySelector('.like-count');

        try {
            const res = await fetch(`/like/${postId}`, { method: 'POST' });
            if (!res.ok) return;

            const data = await res.json();
            countEl.textContent = data.likes;

            // Apparence bouton seulement pour CE client
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

    const observer = new MutationObserver(mutations => {
        mutations.forEach(m => {
            m.addedNodes.forEach(node => {
                if (node.classList && node.classList.contains('post')) {
                    const likeBtn = node.querySelector('.like-btn');
                    if (likeBtn) likeBtn.addEventListener('click', () => toggleLike(likeBtn));

                    // --- NOUVEAU : brancher les nouvelles vidéos ajoutées dynamiquement
                    const vid = node.querySelector('video');
                    if (vid) observeVideo(vid);
                }
            });
        });
    });

    const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
    if (postsContainer) observer.observe(postsContainer, { childList: true });

    const socket = io();

    socket.on('update_like', data => {
        const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
        if (post) {
            const countEl = post.querySelector('.like-count');
            countEl.textContent = data.likes;

            const btn = post.querySelector('.like-btn');
            // Ne changer la couleur que pour l'utilisateur qui a cliqué
            if (btn && data.user === currentUsername) {
                btn.classList.toggle('liked');
            }
        }
    });

    // ------------------ Gestion des vidéos (UNE SEULE lit à la fois) ------------------
    const allVideos = new Set();
    let playingVideo = null;

    function stopAllExcept(current) {
        allVideos.forEach(v => {
            if (v !== current && !v.paused) v.pause();
        });
    }

    const io = new IntersectionObserver((entries) => {
        // Traiter d'abord ce qui est le plus visible
        entries.sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        entries.forEach(entry => {
            const video = entry.target;

            if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
                // Cette vidéo est vraiment visible => lecture exclusive
                stopAllExcept(video);
                if (playingVideo && playingVideo !== video) playingVideo.pause();
                playingVideo = video;
                const p = video.play();
                if (p && typeof p.catch === 'function') p.catch(() => {});
            } else {
                // Plus assez visible => pause
                if (!video.paused) video.pause();
                if (playingVideo === video) playingVideo = null;
            }
        });
    }, { threshold: [0, 0.25, 0.5, 0.6, 0.75, 1] });

    function observeVideo(video) {
        if (!allVideos.has(video)) {
            allVideos.add(video);
            io.observe(video);
        }
    }

    // Brancher toutes les vidéos présentes au chargement
    document.querySelectorAll('.post video').forEach(observeVideo);

    // Quand l’onglet perd le focus, on coupe la lecture
    document.addEventListener('visibilitychange', () => {
        if (document.hidden && playingVideo) {
            playingVideo.pause();
            playingVideo = null;
        }
    });
});

