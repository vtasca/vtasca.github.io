function setupFaviconSwitch() {
  const switchToInactive = function () {
    changeFavicon("inactive-favicon.svg", "image/svg+xml");
  };

  const switchToActive = function () {
    changeFavicon("favicon.svg", "image/svg+xml");
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
