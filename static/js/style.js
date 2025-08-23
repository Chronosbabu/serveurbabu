document.addEventListener('DOMContentLoaded', () => {
  const currentUsername = document.body.dataset.username; // username du client

  // ------------------ GESTION DES LIKES ------------------
  async function toggleLike(button) {
    const post = button.closest('.post');
    const postId = post.dataset.postId;
    const countEl = post.querySelector('.like-count');

    try {
      const res = await fetch(`/like/${postId}`, { method: 'POST' });
      if (!res.ok) return;

      const data = await res.json();
      countEl.textContent = data.likes;

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

  // ------------------ MUTATION OBSERVER (posts dynamiques) ------------------
  const mutationObserver = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.classList && node.classList.contains('post')) {
          const likeBtn = node.querySelector('.like-btn');
          if (likeBtn) likeBtn.addEventListener('click', () => toggleLike(likeBtn));

          const vids = node.querySelectorAll('video');
          vids.forEach(v => observeVideo(v));

          const commentForm = node.querySelector('.comment-form');
          if (commentForm) bindCommentForm(commentForm);
        }
      });
    });
  });

  const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
  if (postsContainer) mutationObserver.observe(postsContainer, { childList: true, subtree: true });

  // ------------------ SOCKET.IO ------------------
  const socket = io();

  // ---- likes en temps réel ----
  socket.on('update_like', data => {
    const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
    if (post) {
      const countEl = post.querySelector('.like-count');
      countEl.textContent = data.likes;

      const btn = post.querySelector('.like-btn');
      if (btn && data.user === currentUsername) btn.classList.toggle('liked');
    }
  });

  // ---- commentaires en temps réel ----
  socket.on('new_comment', data => {
    const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
    if (post) {
      const countEl = post.querySelector('.comment-count');
      if (countEl) countEl.textContent = parseInt(countEl.textContent || "0") + 1;

      const list = post.querySelector('.comments-list');
      if (list) {
        const li = document.createElement('li');
        li.innerHTML = `<strong>${data.username}</strong>: ${data.content}`;
        list.appendChild(li);
      }
    }
  });

  // ---- MESSAGES EN TEMPS RÉEL ----
  socket.on('new_message', data => {
    // si on est sur chat.html et que la conversation correspond
    const chatContainer = document.getElementById('chat-messages');
    if (chatContainer && data.conversation_id == chatContainer.dataset.conversationId) {
      const msgEl = document.createElement('div');
      msgEl.className = 'chat-message';
      msgEl.innerHTML = `<strong>${data.from}</strong>: ${data.content}`;
      chatContainer.appendChild(msgEl);
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  });

  function bindChatForm(form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = form.querySelector('input[name="message"]');
      const content = input.value.trim();
      if (content) {
        const conversationId = form.dataset.conversationId;
        socket.emit('send_message', { conversation_id: parseInt(conversationId), content });
        input.value = "";
      }
    });
  }

  document.querySelectorAll('.chat-form').forEach(bindChatForm);

  // ------------------ FORMULAIRE COMMENTAIRES ------------------
  function bindCommentForm(form) {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const input = form.querySelector('input[name="comment"]');
      const content = input.value.trim();
      if (content) {
        const postId = form.dataset.postId;
        socket.emit('send_comment', { post_id: parseInt(postId), content });
        input.value = "";
      }
    });
  }
  document.querySelectorAll('.comment-form').forEach(bindCommentForm);

  // ------------------ OBSERVER VIDÉOS ------------------
  const videos = new Set();
  let current = null;

  function observeVideo(vid) {
    if (!videos.has(vid)) {
      videos.add(vid);
      intersectionObserver.observe(vid);
      vid.pause();
      vid.addEventListener('play', () => {
        videos.forEach(v => { if (v !== vid && !v.paused) v.pause(); });
        current = vid;
      });
    }
  }

  const intersectionObserver = new IntersectionObserver((entries) => {
    entries.sort((a, b) => b.intersectionRatio - a.intersectionRatio);

    let best = null;
    for (const entry of entries) {
      const vid = entry.target;
      const visible = entry.isIntersecting && entry.intersectionRatio >= 0.6;
      if (visible && !best) best = vid;
      if (!visible && !vid.paused) vid.pause();
    }

    if (best) {
      if (current && current !== best) current.pause();
      videos.forEach(v => { if (v !== best && !v.paused) v.pause(); });
      current = best;
      const p = best.play();
      if (p && typeof p.catch === 'function') p.catch(() => {});
    } else {
      videos.forEach(v => { if (!v.paused) v.pause(); });
      current = null;
    }
  }, { threshold: [0, 0.25, 0.5, 0.6, 0.75, 1] });

  document.querySelectorAll('.post video').forEach(observeVideo);

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
      videos.forEach(v => v.pause());
      current = null;
    }
  });
  window.addEventListener('blur', () => {
    videos.forEach(v => v.pause());
    current = null;
  });
});

