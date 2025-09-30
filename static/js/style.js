document.addEventListener('DOMContentLoaded', () => {
  const currentUsername = document.body.dataset.username; // username du client

  // ------------------ MUTATION OBSERVER (posts dynamiques) ------------------
  const mutationObserver = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.classList && node.classList.contains('post')) {
          // Commentaires
          const commentForm = node.querySelector('.comment-form');
          if (commentForm) bindCommentForm(commentForm);

          // Vidéos
          const vids = node.querySelectorAll('video');
          vids.forEach(v => observeVideo(v));
        }
      });
    });
  });

  const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
  if (postsContainer) mutationObserver.observe(postsContainer, { childList: true, subtree: true });

  // ------------------ SOCKET.IO ------------------
  const socket = io();

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
    const chatContainer = document.getElementById('messages'); // zone de chat
    if (chatContainer && (data.recipient === currentUsername || data.sender === currentUsername)) {
      const div = document.createElement('div');
      div.className = data.sender === currentUsername ? 'message from-me' : 'message from-other';
      div.textContent = data.content;
      chatContainer.appendChild(div);
      chatContainer.scrollTop = chatContainer.scrollHeight;
    }
  });

  // ---- envoi de message depuis chat.html ----
  const input = document.getElementById('messageInput');
  const btn = document.getElementById('sendBtn');
  const messagesDiv = document.getElementById('messages');

  if (btn) {
    btn.addEventListener('click', () => {
      const text = input.value.trim();
      if (!text) return;

      socket.emit('send_message', { recipient: "{{ chat_user }}", content: text });

      const div = document.createElement('div');
      div.className = 'message from-me';
      div.textContent = text;
      messagesDiv.appendChild(div);
      messagesDiv.scrollTop = messagesDiv.scrollHeight;
      input.value = '';
    });
  }

  if (input) {
    input.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        btn.click();
      }
    });
  }

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
  const videos = document.querySelectorAll('.post video');
  let current = null;

  const intersectionObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const vid = entry.target;
      if (entry.isIntersecting && entry.intersectionRatio >= 0.6) {
        // pause toute autre vidéo
        if (current && current !== vid) current.pause();
        videos.forEach(v => { if (v !== vid && !v.paused) v.pause(); });

        // joue celle-ci
        current = vid;
        const p = vid.play();
        if (p && typeof p.catch === 'function') p.catch(() => {});
      } else {
        if (!vid.paused) vid.pause();
      }
    });
  }, { threshold: [0.6] });

  videos.forEach(v => {
    v.pause();
    intersectionObserver.observe(v);
  });

  // ---- pause quand on change d’onglet ----
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

  // ---- pause aussi quand on clique sur une image ----
  document.querySelectorAll('.post img').forEach(img => {
    img.addEventListener('click', () => {
      videos.forEach(v => v.pause());
      current = null;
    });
  });

  // ------------------ FONCTIONS UTILES ------------------
  function observeVideo(v) {
    // placeholder si besoin d'ajouter d'autres comportements pour vidéos
  }
});

