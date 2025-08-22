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

    // Observer pour les posts ajoutés dynamiquement
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

    // Socket.io pour temps réel
    const socket = io();

    // Réception en temps réel des nouveaux posts
    socket.on('new_post', function(post) {
        const postDiv = document.createElement('div');
        postDiv.classList.add('post');
        postDiv.dataset.postId = post.id;
        postDiv.innerHTML = `
            <div class="user-info">
                <a class="avatar-link" href="/profile/${post.username}">
                    ${post.avatar ? `<img src="/avatars/${post.avatar}" class="avatar-post" />` : `<div class="avatar-fallback">${post.username[0].toUpperCase()}</div>`}
                </a>
                <a class="username-link" href="/profile/${post.username}">
                    <p class="username">${post.username}</p>
                </a>
            </div>
            <p class="description">${post.description}</p>
            ${post.type === 'image' ? `<img src="/uploads/${post.file}" class="post-image" />` : `<video src="/uploads/${post.file}" controls muted loop></video>`}
            <div class="post-actions">
                <button class="like-btn">❤️</button>
                <span class="like-count">${post.likes}</span>
                <a href="/comments/${post.id}" class="comment-btn">💬 Commentaires</a>
            </div>
            <p class="date">Publié le ${post.date}</p>
        `;
        postsContainer.prepend(postDiv);
    });

    // Réception en temps réel des likes
    socket.on('update_like', function(data) {
        const postEl = document.querySelector(`.post[data-post-id='${data.post_id}']`);
        if(postEl){
            postEl.querySelector('.like-count').textContent = data.likes;
            const likeBtn = postEl.querySelector('.like-btn');
            if(data.liked) likeBtn.classList.add('liked');
            else likeBtn.classList.remove('liked');
        }
    });
});

