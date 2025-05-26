function setupFaviconSwitch() {
  // Get the base path for static assets
  const getStaticPath = () => {
    // Check if we're in a subdirectory by looking at pathname
    const isSubdirectory = window.location.pathname.split('/').length > 2;
    return isSubdirectory ? '../static' : 'static';
  };

  const staticPath = getStaticPath();

  const switchToInactive = function () {
    changeFavicon(`${staticPath}/earth-night.png`, "image/png");
  };

  const switchToActive = function () {
    changeFavicon(`${staticPath}/earth-day.png`, "image/png");
  };

  function changeFavicon(iconPath, iconType) {
    let link = document.querySelector("link[rel='icon']");

    if (!link) {
      link = document.createElement("link");
      link.rel = "icon";
      document.head.appendChild(link);
    }

    link.href = iconPath;
    link.type = iconType;
  }

  window.addEventListener("blur", switchToInactive);
  window.addEventListener("focus", switchToActive);

  if (!document.hasFocus()) {
    switchToInactive();
  }

  return function cleanup() {
    window.removeEventListener("blur", switchToInactive);
    window.removeEventListener("focus", switchToActive);
  };
}

const cleanupFaviconSwitch = setupFaviconSwitch();

function setupMobileMenu() {
    const hamburger = document.querySelector('.hamburger-menu');
    const mobileMenu = document.querySelector('.mobile-menu');
    const body = document.body;

    function toggleMenu() {
        const isOpen = mobileMenu.classList.contains('active');
        
        if (isOpen) {
            mobileMenu.classList.remove('active');
            body.style.overflow = '';
            hamburger.classList.remove('active');
        } else {
            mobileMenu.classList.add('active');
            body.style.overflow = 'hidden';
            hamburger.classList.add('active');
        }
    }

    hamburger.addEventListener('click', toggleMenu);

    // Close menu when clicking a link
    const mobileLinks = document.querySelectorAll('.mobile-nav-link');
    mobileLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (mobileMenu.classList.contains('active')) {
                toggleMenu();
            }
        });
    });

    // Close menu when clicking outside
    mobileMenu.addEventListener('click', (e) => {
        if (e.target === mobileMenu) {
            toggleMenu();
        }
    });

    return function cleanup() {
        hamburger.removeEventListener('click', toggleMenu);
        mobileLinks.forEach(link => {
            link.removeEventListener('click', toggleMenu);
        });
        mobileMenu.removeEventListener('click', toggleMenu);
    };
}

const cleanupMobileMenu = setupMobileMenu();
