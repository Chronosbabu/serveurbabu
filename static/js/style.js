document.addEventListener('DOMContentLoaded', () => {
    const currentUsername = document.body.dataset.username; // Assurez-vous de passer le username dans body

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
            // --- Ne changer la couleur que pour l'utilisateur qui a cliqué ---
            if (btn && data.user === currentUsername) {
                btn.classList.toggle('liked');
            }
        }
    });

    // ------------------ Gestion des vidéos ------------------
    const allVideos = new Set(); // Stocke toutes les vidéos
    document.querySelectorAll('.post video').forEach(video => allVideos.add(video));

    function stopAllVideosExcept(currentVideo) {
        allVideos.forEach(video => {
            if (video !== currentVideo) {
                video.pause();
                video.currentTime = 0; // Optionnel : remettre au début
            }
        });
    }

    function handleVideoVisibility() {
        const posts = document.querySelectorAll('.post');
        posts.forEach(post => {
            const video = post.querySelector('video');
            if (video) {
                const rect = post.getBoundingClientRect();
                if (rect.top >= 0 && rect.bottom <= window.innerHeight) {
                    // Vidéo visible à l'écran
                    stopAllVideosExcept(video);
                    video.play();
                } else {
                    video.pause();
                }
            }
        });
    }

    window.addEventListener('scroll', handleVideoVisibility);
    window.addEventListener('resize', handleVideoVisibility);
    handleVideoVisibility(); // Vérification au chargement initial
});

