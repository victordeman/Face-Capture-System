// components/navbar.js
class CustomNavbar extends HTMLElement {
  connectedCallback() {
    this.render();
  }

  render() {
    const token = localStorage.getItem('jwt_token');
    const role = localStorage.getItem('user_role');
    const isLoggedIn = !!token;
    const currentPath = window.location.pathname;

    const navLinks = [
      { name: 'Home', href: '/', show: true },
      { name: 'Attendance', href: '/attendance', show: isLoggedIn },
      { name: 'Enroll', href: '/enroll', show: isLoggedIn },
      { name: 'Dashboard', href: '/dashboard', show: isLoggedIn },
      { name: 'Admin', href: '/admin', show: isLoggedIn && role === 'admin' },
    ];

    const linksHtml = navLinks
      .filter(link => link.show)
      .map(link => {
        const isActive = currentPath === link.href || (link.href !== '/' && currentPath.startsWith(link.href));
        return `
          <li>
            <a href="${link.href}" class="block py-2 px-3 md:p-0 rounded transition ${
              isActive 
                ? 'text-primary-600 font-bold md:underline underline-offset-8 decoration-2' 
                : 'text-slate-700 dark:text-slate-300 hover:text-primary-600'
            }">
              ${link.name}
            </a>
          </li>
        `;
      })
      .join('');

    this.innerHTML = `
      <nav class="fixed w-full z-50 top-0 start-0 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-700 shadow-sm transition-colors duration-300">
        <div class="max-w-7xl flex flex-wrap items-center justify-between mx-auto p-4 px-6">
          <a href="/" class="flex items-center space-x-3 rtl:space-x-reverse">
            <span class="self-center text-2xl font-bold whitespace-nowrap bg-clip-text text-transparent bg-gradient-to-r from-primary-600 to-secondary-600">
              VisageTrack AI
            </span>
          </a>
          
          <div class="flex md:order-2 space-x-3 md:space-x-4 rtl:space-x-reverse items-center">
            <button id="nav-theme-toggle" type="button" class="p-2 text-slate-500 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors focus:outline-none">
                <i data-feather="moon" class="w-5 h-5 hidden dark:block"></i>
                <i data-feather="sun" class="w-5 h-5 block dark:hidden"></i>
            </button>

            ${isLoggedIn ? `
              <button id="logout-btn" class="hidden md:flex text-white bg-red-500 hover:bg-red-600 focus:ring-4 focus:outline-none focus:ring-red-300 font-medium rounded-lg text-sm px-4 py-2 text-center transition-all items-center gap-2">
                <i data-feather="log-out" class="w-4 h-4"></i>
                Logout
              </button>
            ` : `
              <a href="/" class="hidden md:block text-white bg-primary-600 hover:bg-primary-700 focus:ring-4 focus:outline-none focus:ring-primary-300 font-medium rounded-lg text-sm px-4 py-2 text-center transition-all">
                Login
              </a>
            `}

            <button id="mobile-menu-toggle" type="button" class="inline-flex items-center p-2 w-10 h-10 justify-center text-sm text-slate-500 rounded-lg md:hidden hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-slate-200 dark:text-slate-400 dark:hover:bg-slate-700 dark:focus:ring-slate-600">
              <span class="sr-only">Open main menu</span>
              <i data-feather="menu" class="w-6 h-6"></i>
            </button>
          </div>

          <div class="items-center justify-between hidden w-full md:flex md:w-auto md:order-1" id="mobile-menu">
            <ul class="flex flex-col p-4 md:p-0 mt-4 font-medium border border-slate-100 dark:border-slate-800 rounded-lg md:space-x-8 rtl:space-x-reverse md:flex-row md:mt-0 md:border-0 bg-slate-50 md:bg-transparent dark:bg-slate-800 md:dark:bg-transparent">
              ${linksHtml}
              ${isLoggedIn ? `
                <li class="md:hidden mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                  <button id="logout-btn-mobile" class="w-full text-left py-2 px-3 text-red-500 font-bold flex items-center gap-2">
                    <i data-feather="log-out" class="w-4 h-4"></i>
                    Logout
                  </button>
                </li>
              ` : `
                <li class="md:hidden mt-2 pt-2 border-t border-slate-200 dark:border-slate-700">
                  <a href="/" class="block py-2 px-3 text-primary-600 font-bold">
                    Login
                  </a>
                </li>
              `}
            </ul>
          </div>
        </div>
      </nav>
      <!-- Spacer to prevent content from going under the fixed navbar -->
      <div class="h-16 md:h-20"></div>
    `;

    // Initialize Feather Icons
    if (window.feather) {
      feather.replace();
    }

    // Handlers
    this.initHandlers();
  }

  initHandlers() {
    // Theme toggle
    const themeBtn = this.querySelector('#nav-theme-toggle');
    if (themeBtn) {
      themeBtn.addEventListener('click', () => {
        document.body.classList.toggle('dark');
        const isDark = document.body.classList.contains('dark');
        localStorage.setItem('theme', isDark ? 'dark' : 'light');
        this.render(); // Re-render to update icons and state if needed
      });
    }

    // Mobile menu toggle
    const menuBtn = this.querySelector('#mobile-menu-toggle');
    const menu = this.querySelector('#mobile-menu');
    if (menuBtn && menu) {
      menuBtn.addEventListener('click', () => {
        menu.classList.toggle('hidden');
      });
    }

    // Logout
    const logoutBtns = this.querySelectorAll('#logout-btn, #logout-btn-mobile');
    logoutBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            localStorage.removeItem('jwt_token');
            localStorage.removeItem('user_role');
            // Also clear session via server call if possible, but for now just redirect
            window.location.href = '/';
        });
    });
  }
}

customElements.define('custom-navbar', CustomNavbar);
