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

            // --- Gestion apparence bouton like/love ---
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

    // --- Observer pour posts ajoutés dynamiquement ---
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

    // --- Sauvegarde/restauration scroll ---
    const SCROLL_KEY = "scrollPosition";
    if (sessionStorage.getItem(SCROLL_KEY)) window.scrollTo(0, parseInt(sessionStorage.getItem(SCROLL_KEY), 10));
    window.addEventListener("beforeunload", () => { sessionStorage.setItem(SCROLL_KEY, window.scrollY); });

    // --- SocketIO pour likes et commentaires en temps réel ---
    const socket = io();

    socket.on('update_like', data => {
        const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
        if (post) {
            const countEl = post.querySelector('.like-count');
            countEl.textContent = data.likes;
            const btn = post.querySelector('.like-btn');
            if (btn) data.liked ? btn.classList.add('liked') : btn.classList.remove('liked');
        }
    });

    socket.on('new_comment', data => {
        const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
        if (post) {
            const commentsList = post.querySelector('.comments-list');
            if (commentsList) {
                const commentEl = document.createElement('div');
                commentEl.classList.add('comment');
                commentEl.innerHTML = `
                    <img src="${data.avatar ? '/avatars/' + data.avatar : '/avatars/default.png'}" class="avatar-comment">
                    <span class="comment-content"><strong>${data.username}</strong>: ${data.content}</span>
                `;
                commentsList.appendChild(commentEl);

                const counter = post.querySelector('.comment-count');
                if (counter) counter.textContent = parseInt(counter.textContent || "0") + 1;
            }
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

