document.addEventListener('DOMContentLoaded', () => {
    const socket = io();

    async function toggleLike(button) {
        const post = button.closest('.post');
        const postId = post.dataset.postId;

        try {
            const res = await fetch(`/like/${postId}`, { method: 'POST' });
            if (!res.ok) return;

            const data = await res.json();
            socket.emit('like_updated', { post_id: postId, likes: data.likes, liked: data.liked });
        } catch (err) {
            console.error("Erreur like:", err);
        }
    }

    function updateLikeUI(postId, likes, liked) {
        const post = document.querySelector(`.post[data-post-id="${postId}"]`);
        if (!post) return;
        const countEl = post.querySelector('.like-count');
        const btn = post.querySelector('.like-btn');
        countEl.textContent = likes;
        if (liked) btn.classList.add('liked');
        else btn.classList.remove('liked');
    }

    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', () => toggleLike(btn));
    });

    // Observer pour posts dynamiques
    const observer = new MutationObserver(mutations => {
        mutations.forEach(m => {
            m.addedNodes.forEach(node => {
                if (node.classList && node.classList.contains('post')) {
                    const likeBtn = node.querySelector('.like-btn');
                    if (likeBtn) {
                        likeBtn.addEventListener('click', () => toggleLike(likeBtn));
                    }
                }
            });
        });
    });

    const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
    if(postsContainer){
        observer.observe(postsContainer, { childList: true });
    }

    // Socket.IO: réception des mises à jour en temps réel
    socket.on('like_updated', data => updateLikeUI(data.post_id, data.likes, data.liked));
    socket.on('new_post', postHTML => {
        postsContainer.insertAdjacentHTML('afterbegin', postHTML);
    });
    socket.on('new_comment', commentData => {
        const post = document.querySelector(`.post[data-post-id="${commentData.post_id}"]`);
        if (!post) return;
        // ajouter le commentaire dynamiquement si tu veux
        // ici on peut appeler une fonction pour afficher le commentaire
    });

    // Publication en temps réel
    const form = document.getElementById('post-form');
    if(form){
        form.addEventListener('submit', async e => {
            e.preventDefault();
            const formData = new FormData(form);
            try {
                const res = await fetch(form.action, { method: 'POST', body: formData });
                if (!res.ok) return;
                const data = await res.text();
                socket.emit('new_post', data); // envoyer HTML du post aux autres
                form.reset();
            } catch(err){
                console.error("Erreur publication:", err);
            }
        });
    }
});

