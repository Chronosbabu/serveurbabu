document.addEventListener('DOMContentLoaded', () => {
    function toggleLike(button) {
        const post = button.closest('.post');
        const countEl = post.querySelector('.like-count');
        let count = parseInt(countEl.textContent);
        if (button.classList.contains('liked')) {
            button.classList.remove('liked');
            count--;
        } else {
            button.classList.add('liked');
            count++;
        }
        countEl.textContent = count;
        // Ici, tu peux ajouter un fetch pour mettre à jour le serveur
        // fetch(`/like/${post.dataset.postId}`, { method: 'POST' });
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

    observer.observe(document.getElementById('posts'), { childList: true });
});
