document.addEventListener('DOMContentLoaded', () => {
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

    // Pour les posts ajoutés dynamiquement
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
});


