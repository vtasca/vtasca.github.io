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

    // Close menu when clicking outside
    mobileMenu.addEventListener('click', (e) => {
        if (e.target === mobileMenu) {
            toggleMenu();
        }
    });

    return function cleanup() {
        hamburger.removeEventListener('click', toggleMenu);
        mobileMenu.removeEventListener('click', toggleMenu);
    };
}

const cleanupMobileMenu = setupMobileMenu();

function setupHeadingAnchors() {
    const article = document.querySelector('article');
    if (!article) return;

    // Function to create a slug from text
    function slugify(text) {
        return text
            .toLowerCase()
            .trim()
            .replace(/[^\w\s-]/g, '') // Remove special characters
            .replace(/[\s_-]+/g, '-') // Replace spaces and underscores with hyphens
            .replace(/^-+|-+$/g, ''); // Remove leading/trailing hyphens
    }

    // Find all headings (h2-h6) within the article
    const headings = article.querySelectorAll('h2, h3, h4, h5, h6');
    const usedIds = new Set();
    
    headings.forEach((heading) => {
        // Skip if heading already has an ID
        if (heading.id) {
            usedIds.add(heading.id);
            return;
        }

        // Generate ID from heading text
        let id = slugify(heading.textContent);
        if (!id) return;

        // Handle duplicate IDs by appending a number
        let baseId = id;
        let counter = 1;
        while (usedIds.has(id)) {
            id = `${baseId}-${counter}`;
            counter++;
        }
        usedIds.add(id);

        // Set the ID on the heading
        heading.id = id;

        // Make heading clickable
        heading.addEventListener('click', (e) => {
            e.preventDefault();
            window.history.pushState(null, '', `#${id}`);
            
            // Scroll to heading with smooth behavior
            heading.scrollIntoView({ behavior: 'smooth', block: 'start' });
        });
    });

    return function cleanup() {
        // Cleanup would go here if needed
    };
}

const cleanupHeadingAnchors = setupHeadingAnchors();
