document.addEventListener('DOMContentLoaded', () => {
    const postsContainer = document.getElementById('posts');
    const commentModal = document.getElementById('comment-modal');
    const commentsList = document.getElementById('comments-list');
    const newCommentInput = document.getElementById('new-comment');
    const submitCommentBtn = document.getElementById('submit-comment');
    let currentPostId = null;

    const socket = io();

    // --- Likes ---
    async function toggleLike(button) {
        const post = button.closest('.post');
        const postId = post.dataset.postId;
        const countEl = post.querySelector('.like-count');

        try {
            const res = await fetch(`/like/${postId}`, { method: 'POST' });
            if (!res.ok) return;

            const data = await res.json();
            countEl.textContent = data.likes;
            button.classList.toggle('liked', data.liked);
        } catch (err) {
            console.error("Erreur like:", err);
        }
    }

    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', () => toggleLike(btn));
    });

    // --- Comment Modal ---
    function openCommentModal(postId) {
        currentPostId = postId;
        commentsList.innerHTML = '';
        commentModal.classList.remove('hidden');

        // Charger les commentaires
        const post = document.querySelector(`.post[data-post-id='${postId}']`);
        const comments = post.dataset.comments ? JSON.parse(post.dataset.comments) : [];
        comments.forEach(c => {
            const div = document.createElement('div');
            div.className = 'comment-item';
            div.innerHTML = `
                <img src="${c.avatar ? '/avatars/' + c.avatar : ''}" class="comment-avatar" />
                <strong>${c.username}</strong>: ${c.text}
            `;
            commentsList.appendChild(div);
        });
    }

    document.querySelectorAll('.comment-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const postId = e.target.closest('.post').dataset.postId;
            openCommentModal(postId);
        });
    });

    document.getElementById('close-comment').addEventListener('click', () => {
        commentModal.classList.add('hidden');
        newCommentInput.value = '';
    });

    submitCommentBtn.addEventListener('click', async () => {
        if (!currentPostId || !newCommentInput.value.trim()) return;

        try {
            const res = await fetch(`/comment/${currentPostId}`, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({ comment: newCommentInput.value.trim() })
            });
            if (!res.ok) return;
            const data = await res.json();
            const div = document.createElement('div');
            div.className = 'comment-item';
            div.innerHTML = `
                <img src="${data.avatar ? '/avatars/' + data.avatar : ''}" class="comment-avatar" />
                <strong>${data.username}</strong>: ${data.text}
            `;
            commentsList.appendChild(div);
            newCommentInput.value = '';
        } catch(err) {
            console.error('Erreur commentaire:', err);
        }
    });

    // --- Socket pour nouveaux posts ---
    socket.on('new_post', (post) => {
        const div = document.createElement('div');
        div.className = 'post';
        div.dataset.postId = post.id || "";
        div.innerHTML = `
            <div class="user-info">
                ${post.avatar
                    ? `<a class="avatar-link" href="${post.username ? '/profile/' + post.username : '#'}">
                            <img src="/avatars/${post.avatar}" alt="avatar" class="avatar-post" />
                       </a>`
                    : `<a class="avatar-link" href="${post.username ? '/profile/' + post.username : '#'}">
                            <div class="avatar-fallback">${(post.username || '').charAt(0).toUpperCase()}</div>
                       </a>`
                }
                <a class="username-link" href="${post.username ? '/profile/' + post.username : '#'}">
                    <p class="username">${post.username}</p>
                </a>
            </div>
            <p class="description">${post.description}</p>
            ${post.type === 'image'
                ? `<img src="/uploads/${post.file}" alt="image" class="post-image">`
                : `<video src="/uploads/${post.file}" controls muted loop></video>`}
            <div class="post-actions">
                <button class="like-btn">❤️</button>
                <span class="like-count">0</span>
                <button class="comment-btn">💬</button>
            </div>
            <p class="date">Publié le ${post.date}</p>
        `;
        postsContainer.prepend(div);

        div.querySelector('.like-btn').addEventListener('click', () => toggleLike(div.querySelector('.like-btn')));
        div.querySelector('.comment-btn').addEventListener('click', (e) => {
            const postId = e.target.closest('.post').dataset.postId;
            openCommentModal(postId);
        });

        const video = div.querySelector('video');
        if (video) {
            const observer = new IntersectionObserver(entries => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) entry.target.play();
                    else entry.target.pause();
                });
            }, { threshold: 0.6 });
            observer.observe(video);
        }
    });
});

