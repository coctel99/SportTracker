/**
 * main.js – global UI behaviour
 *
 * Session form logic lives in the session_new.html inline <script>
 * so that it can reference Jinja template data directly.
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

});
