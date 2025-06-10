document.addEventListener('DOMContentLoaded', () => {
    // Create lightbox element
    const lightbox = document.createElement('div');
    lightbox.className = 'lightbox';
    document.body.appendChild(lightbox);

    // SVG for expand icon
    const expandSVG = `
        <svg width="24px" height="24px" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M14 10L21 3M21 3H16.5M21 3V7.5M10 14L3 21M3 21H7.5M3 21L3 16.5" stroke="#fff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
    `;

    // Add wrappers and expand icons to all article images inside p tags
    document.querySelectorAll('article p img').forEach(img => {
        // Create wrapper
        const wrapper = document.createElement('span');
        wrapper.className = 'article-image-wrapper';
        img.parentNode.insertBefore(wrapper, img);
        wrapper.appendChild(img);

        // Create expand icon
        const icon = document.createElement('span');
        icon.className = 'expand-icon';
        icon.innerHTML = expandSVG;
        icon.title = 'Expand image';
        wrapper.appendChild(icon);

        // Open lightbox on icon or image click
        function openLightbox() {
            const clone = img.cloneNode();
            lightbox.innerHTML = '';
            lightbox.appendChild(clone);
            lightbox.classList.add('active');
        }
        icon.addEventListener('click', e => {
            e.stopPropagation();
            openLightbox();
        });
        img.addEventListener('click', openLightbox);
    });

    // Close lightbox on click
    lightbox.addEventListener('click', () => {
        lightbox.classList.remove('active');
    });
}); 