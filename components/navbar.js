// components/navbar.js
class CustomNavbar extends HTMLElement {
  connectedCallback() {
    this.innerHTML = `
      <nav class="custom-navbar flex justify-between items-center px-6 py-4 bg-white dark:bg-slate-900 shadow-md">
        <a href="/" class="text-2xl font-bold text-primary-600 hover:text-primary-700 transition">
          VisageTrack AI
        </a>
        <ul class="flex space-x-8">
          <li><a href="/" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Home</a></li>
          <li><a href="/attendance" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Attendance</a></li>
          <li><a href="/enroll" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Enroll</a></li>
          <li><a href="/dashboard" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Dashboard</a></li>
          <li><a href="/admin" class="text-slate-700 dark:text-slate-300 hover:text-primary-600 transition">Admin</a></li>
        </ul>
      </nav>
    `;
  }
}

customElements.define('custom-navbar', CustomNavbar);
