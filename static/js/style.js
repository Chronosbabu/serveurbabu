
document.addEventListener('DOMContentLoaded', () => {
  // … tout ton code existant (likes, socket, etc.) reste identique …

  // ------------------ Gestion des vidéos : UNE SEULE lit à la fois ------------------
  const videos = new Set();
  let current = null;

  // Observe aussi les posts ajoutés dynamiquement (on réutilise ton observer existant si tu l'as)
  function observeVideo(vid) {
    if (!videos.has(vid)) {
      videos.add(vid);
      io.observe(vid);
      vid.pause(); // par défaut à l'arrêt
      // si l’utilisateur clique manuellement une vidéo, on coupe les autres
      vid.addEventListener('play', () => {
        videos.forEach(v => { if (v !== vid && !v.paused) v.pause(); });
        current = vid;
      });
    }
  }

  // IntersectionObserver : joue la vidéo la plus visible (>60%), sinon pause toutes
  const io = new IntersectionObserver((entries) => {
    // on trie par taux de visibilité décroissant
    entries.sort((a, b) => b.intersectionRatio - a.intersectionRatio);

    // vidéo “candidate” à lire (la plus visible au-dessus du seuil)
    let best = null;
    for (const entry of entries) {
      const vid = entry.target;
      const visible = entry.isIntersecting && entry.intersectionRatio >= 0.6;
      if (visible && !best) best = vid;
      // si elle n’est plus suffisamment visible -> pause
      if (!visible && !vid.paused) vid.pause();
    }

    if (best) {
      // lecture exclusive
      if (current && current !== best) current.pause();
      videos.forEach(v => { if (v !== best && !v.paused) v.pause(); });
      current = best;
      const p = best.play();
      if (p && typeof p.catch === 'function') p.catch(() => {}); // ignore autoplay block
    } else {
      // aucune vidéo au-dessus du seuil => toutes en pause
      videos.forEach(v => { if (!v.paused) v.pause(); });
      current = null;
    }
  }, { threshold: [0, 0.25, 0.5, 0.6, 0.75, 1] });

  // Brancher les vidéos présentes
  document.querySelectorAll('.post video').forEach(observeVideo);

  // Si tu as déjà un MutationObserver pour les posts, ajoute juste :
  const postsContainer = document.getElementById('posts') || document.getElementById('profile-posts');
  if (postsContainer) {
    const mo = new MutationObserver(muts => {
      muts.forEach(m => {
        m.addedNodes.forEach(node => {
          if (node.nodeType === 1) {
            node.querySelectorAll && node.querySelectorAll('video').forEach(observeVideo);
            if (node.matches && node.matches('video')) observeVideo(node);
          }
        });
      });
    });
    mo.observe(postsContainer, { childList: true, subtree: true });
  }

  // Quand l’onglet ou la fenêtre perd le focus -> pause tout
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


