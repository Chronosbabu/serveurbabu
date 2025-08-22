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
});
