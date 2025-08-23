
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

          // --- vidéos ajoutées dynamiquement
          const vids = node.querySelectorAll('video');
          vids.forEach(v => observeVideo(v));
        }
      });
    });
  });

  const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
  if (postsContainer) observer.observe(postsContainer, { childList: true, subtree: true });

  const socket = io();
  socket.on('update_like', data => {
    const post = document.querySelector(`.post[data-post-id="${data.post_id}"]`);
    if (post) {
      const countEl = post.querySelector('.like-count');
      countEl.textContent = data.likes;

      const btn = post.querySelector('.like-btn');
      if (btn && data.user === currentUsername) {
        btn.classList.toggle('liked');
      }
    }
  });

  // ------------------ GESTION DES VIDÉOS ------------------
  const videos = new Set();
  let current = null;

  function observeVideo(vid) {
    if (!videos.has(vid)) {
      videos.add(vid);
      io.observe(vid);
      vid.pause(); // arrêt par défaut
      vid.addEventListener('play', () => {
        videos.forEach(v => { if (v !== vid && !v.paused) v.pause(); });
        current = vid;
      });
    }
  }

  const io = new IntersectionObserver((entries) => {
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



