document.addEventListener('DOMContentLoaded', () => {
    // --- Gestion des likes ---
    async function toggleLike(button) {
        const post = button.closest('.post');
        const postId = post.dataset.postId;
        const countEl = post.querySelector('.like-count');

        try {
            const res = await fetch(`/like/${postId}`, { method: 'POST' });
            if (!res.ok) return;

            const data = await res.json();
            countEl.textContent = data.likes;
            if (data.liked) {
                button.classList.add('liked');
            } else {
                button.classList.remove('liked');
            }
        } catch (err) {
            console.error("Erreur like:", err);
        }
    }

    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', () => toggleLike(btn));
    });

    // --- Observer pour les posts ajoutés dynamiquement ---
    const observer = new MutationObserver(mutations => {
        mutations.forEach(m => {
            m.addedNodes.forEach(node => {
                if (node.classList && node.classList.contains('post')) {
                    const likeBtn = node.querySelector('.like-btn');
                    if (likeBtn) {
                        likeBtn.addEventListener('click', () => toggleLike(likeBtn));
                    }

                    // Gérer la lecture/pause des vidéos pour les nouveaux posts
                    const video = node.querySelector('video');
                    if (video) {
                        setupVideoObserver(video);
                    }
                }
            });
        });
    });

    const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
    if (postsContainer) {
        observer.observe(postsContainer, { childList: true });
    }

    // --- Gestion des vidéos ---
    function setupVideoObserver(video) {
        const io = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    // Pause toutes les autres vidéos
                    document.querySelectorAll('video').forEach(v => {
                        if (v !== video) {
                            v.pause();
                        }
                    });
                    // Lire seulement si visible
                    video.play().catch(err => console.log("Lecture vidéo bloquée:", err));
                } else {
                    // Arrêter dès qu'on sort du viewport
                    video.pause();
                }
            });
        }, { threshold: 0.6 }); // la vidéo doit être au moins à 60% visible

        io.observe(video);
    }

    // Initialiser les vidéos déjà présentes dans la page
    document.querySelectorAll('video').forEach(video => {
        setupVideoObserver(video);
    });

    // --- Sauvegarde et restauration du scroll ---
    const SCROLL_KEY = "scrollPosition";

    // Restaurer le scroll quand on revient sur la page
    if (sessionStorage.getItem(SCROLL_KEY)) {
        window.scrollTo(0, parseInt(sessionStorage.getItem(SCROLL_KEY), 10));
    }

    // Sauvegarder le scroll avant de quitter/naviguer
    window.addEventListener("beforeunload", () => {
        sessionStorage.setItem(SCROLL_KEY, window.scrollY);
    });
});

