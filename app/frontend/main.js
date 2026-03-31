/**
 * session_form.js – Log Session interactive exercise picker
 *
 * Each exercise is rendered as a toggle card.  Clicking it marks it active
 * and reveals a reps input.  Hidden inputs carry the data on submit.
 * The form validates that at least one exercise is active before submitting.
 */

document.addEventListener('DOMContentLoaded', () => {

  // ── Mobile nav toggle ───────────────────────────────────────────────────
  const navToggle = document.getElementById('nav-toggle');
  const navMenu   = document.getElementById('nav-menu');
  if (navToggle && navMenu) {
    navToggle.addEventListener('click', () => {
      navMenu.classList.toggle('hidden');
    });
  }

  // ── Session form – exercise card picker ─────────────────────────────────
  const form = document.getElementById('session-form');
  if (!form) return;

  const cards     = form.querySelectorAll('.exercise-card');
  const submitBtn = form.querySelector('[type="submit"]');

  cards.forEach(card => {
    card.addEventListener('click', e => {
      // Don't toggle when clicking inside the reps input itself
      if (e.target.tagName === 'INPUT') return;

      const isActive = card.classList.toggle('active');
      const hiddenId = card.querySelector('.hidden-exercise-id');
      const repsInput = card.querySelector('.reps-input');

      if (isActive) {
        hiddenId.disabled  = false;
        repsInput.disabled = false;
        repsInput.focus();
      } else {
        hiddenId.disabled  = true;
        repsInput.disabled = true;
        repsInput.value    = '';
      }
    });
  });

  // Prevent submit if nothing selected
  form.addEventListener('submit', e => {
    const active = form.querySelectorAll('.exercise-card.active');
    if (active.length === 0) {
      e.preventDefault();
      const msg = document.getElementById('no-exercise-msg');
      if (msg) msg.classList.remove('hidden');
      return;
    }
    // Validate each active card has reps filled
    for (const card of active) {
      const reps = card.querySelector('.reps-input');
      if (!reps.value.trim()) {
        e.preventDefault();
        reps.focus();
        reps.classList.add('ring-2', 'ring-red-400');
        return;
      }
    }
  });

});

