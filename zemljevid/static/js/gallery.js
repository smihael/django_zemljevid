// gallery.js
async function fetchImagesJson(model_name = 'partisanmemorial', object_id = 2) {
    const url = `/api/get_images?model_name=${encodeURIComponent(model_name)}&object_id=${encodeURIComponent(object_id)}`;
    const response = await fetch(url);
    return await response.json();
}

let gb; // Exported GLightbox instance

function renderGallery(data) {
    const gallery = document.getElementById('gallery');
    gallery.innerHTML = '';
    data.images.forEach(img => {
        const a = document.createElement('a');
        a.href = img.url;
        a.setAttribute('data-gallery', 'gallery1');
        a.setAttribute('class', 'gallery-item glightbox');
        // Compose caption: filename, caption, author, licence
        const captionParts = [img.filename];
        if (img.caption) captionParts.push(img.caption);
        if (img.author) captionParts.push(img.author);
        if (img.license) captionParts.push(img.license);
        const fullCaption = captionParts.join(' | ');
        a.setAttribute('data-title', fullCaption);
        const image = document.createElement('img');
        image.src = img.thumbnail_url || img.url; // Fallback to full image if thumbnail is not available
        //image.alt = fullCaption;
        a.appendChild(image);
        gallery.appendChild(a);
    });
    gb = GLightbox({
        selector: '.glightbox',
        touchNavigation: true,
        loop: true,
        zoomable: true,
        autoplayVideos: false
    });

    // Add info icon to GLightbox caption and show modal on click
    function injectExifIconToLightbox() {
        const slide = gb.getActiveSlide();
        if (!slide) return;
        // Try to find the caption area (title or desc)
        let caption = slide.querySelector('.gslide-title') || slide.querySelector('.gdesc');
        if (!caption) return;
        // Remove previous icon if any
        let prevIcon = document.getElementById('glightbox-exif-icon');
        if (prevIcon) prevIcon.remove();
        // Create info icon
        const exifIcon = document.createElement('span');
        exifIcon.id = 'glightbox-exif-icon';
        exifIcon.innerHTML = '&#128712;';
        exifIcon.title = 'Show EXIF info';
        exifIcon.style.marginLeft = '12px';
        exifIcon.style.background = 'rgba(255,255,255,0.8)';
        exifIcon.style.borderRadius = '50%';
        exifIcon.style.padding = '2px 8px';
        exifIcon.style.cursor = 'pointer';
        exifIcon.style.fontSize = '1.2em';
        exifIcon.style.verticalAlign = 'middle';
        exifIcon.style.display = 'inline-block';
        // On click, fetch and show EXIF modal
        exifIcon.onclick = async (e) => {
            console.log('EXIF icon clicked');
            // Prevent GLightbox from closing the modal
            e.stopPropagation();
            e.preventDefault();

            const imgElement = slide.querySelector('img');
            if (imgElement) {
                try {
                    const response = await fetch(imgElement.src);
                    const blob = await response.blob();
                    const exifData = await exifr.parse(blob);
                    let modal = document.getElementById('exif-modal');
                    if (!modal) {
                        modal = document.createElement('div');
                        modal.id = 'exif-modal';
                        modal.style.position = 'fixed';
                        modal.style.top = '50%';
                        modal.style.left = '50%';
                        modal.style.transform = 'translate(-50%, -50%)';
                        modal.style.background = 'rgba(255,255,255,0.98)';
                        modal.style.padding = '20px';
                        modal.style.zIndex = '2147483647'; // max z-index
                        modal.style.maxWidth = '90vw';
                        modal.style.maxHeight = '80vh';
                        modal.style.overflowY = 'auto';
                        modal.style.borderRadius = '8px';
                        modal.style.boxShadow = '0 2px 16px rgba(0,0,0,0.3)';
                        modal.innerHTML = '<button id="exif-close" style="float:right;font-size:1.2em;">&times;</button><div id="exif-content"></div>';
                        document.body.appendChild(modal);
                        document.getElementById('exif-close').onclick = closeExifModal;
                    }
                    let exifInfo = 'No EXIF data found.';
                    if (exifData && Object.keys(exifData).length > 0) {
                        // Filter out fields that are numerical arrays (e.g., Uint8Array, Int16Array, etc.)
                        const filteredEntries = Object.entries(exifData).filter(([key, value]) => {
                            // Hide if value is a typed array or Array of numbers
                            if (Array.isArray(value) && value.every(v => typeof v === 'number')) return false;
                            if (value && typeof value === 'object' && value.buffer instanceof ArrayBuffer) return false;
                            if (value && value.constructor && value.constructor.name.endsWith('Array')) return false;
                            return true;
                        });
                        if (filteredEntries.length > 0) {
                            exifInfo = '<h3>EXIF Data</h3><table>' +
                                filteredEntries
                                    .map(([key, value]) => `<tr><td><b>${key}</b></td><td>${value}</td></tr>`)
                                    .join('') +
                                '</table>';
                        }
                    }
                    document.getElementById('exif-content').innerHTML = exifInfo;
                    modal.style.display = 'block';
                } catch (error) {
                    console.error('Error fetching image for exifr data:', error);
                }
            }
        };
        caption.appendChild(exifIcon);
    }
    gb.on('open', injectExifIconToLightbox);
    gb.on('slide_changed', injectExifIconToLightbox);
}

// Function to close the EXIF modal
function closeExifModal() {
    const modal = document.getElementById('exif-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}