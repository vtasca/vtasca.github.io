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
