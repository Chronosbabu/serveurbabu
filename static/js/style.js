document.addEventListener('DOMContentLoaded', () => {
    const currentUsername = document.body.dataset.username; // injecté via template

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

            // --- Apparence bouton pour CE client seulement ---
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

    // --- Observer posts dynamiques ---
    const observer = new MutationObserver(mutations => {
        mutations.forEach(m => {
            m.addedNodes.forEach(node => {
                if (node.classList && node.classList.contains('post')) {
                    const likeBtn = node.querySelector('.like-btn');
                    if (likeBtn) likeBtn.addEventListener('click', () => toggleLike(likeBtn));

                    const video = node.querySelector('video');
                    if (video) setupVideoObserver(video);

                    const commentForm = node.querySelector('.comment-form');
                    if (commentForm) setupCommentForm(commentForm);
                }
            });
        });
    });

    const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
    if (postsContainer) observer.observe(postsContainer, { childList: true });

    // --- Gestion vidéos ---
    function setupVideoObserver(video) {
        const io = new IntersectionObserver(entries => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    document.querySelectorAll('video').forEach(v => { if (v !== video) v.pause(); });
                    video.play().catch(err => console.log("Lecture vidéo bloquée:", err));
                } else video.pause();
            });
        }, { threshold: 0.6 });
        io.observe(video);
    }
    document.querySelectorAll('video').forEach(video => setupVideoObserver(video));

    // --- SocketIO ---
    const socket = io();

    socket.on('update_like', data => {
        const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
        if (!post) return;

        const countEl = post.querySelector('.like-count');
        countEl.textContent = data.likes;

        // --- Apparence bouton seulement pour CE client ---
        if (data.user === currentUsername) {
            const btn = post.querySelector('.like-btn');
            if (btn) btn.classList.toggle('liked');
        }
    });

    socket.on('new_comment', data => {
        const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
        if (!post) return;

        const commentsList = post.querySelector('.comments-list');
        if (commentsList) {
            const commentEl = document.createElement('div');
            commentEl.classList.add('comment');
            commentEl.innerHTML = `
                <img src="${data.avatar ? '/avatars/' + data.avatar : '/avatars/default.png'}" class="comment-avatar">
                <span class="comment-content"><strong>${data.username}</strong>: ${data.content}</span>
            `;
            commentsList.appendChild(commentEl);

            const counter = post.querySelector('.comment-count');
            if (counter) counter.textContent = parseInt(counter.textContent || "0") + 1;
        }
    });

    function setupCommentForm(form) {
        form.addEventListener('submit', e => {
            e.preventDefault();
            const post = form.closest('.post');
            const postId = post.dataset.postId;
            const input = form.querySelector('input[name="comment"]');
            const content = input.value.trim();
            if (!content) return;

            socket.emit('send_comment', { post_id: postId, content });
            input.value = '';
        });
    }

    document.querySelectorAll('.comment-form').forEach(form => setupCommentForm(form));
});

