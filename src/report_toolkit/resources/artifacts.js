/* Proportional artifact sizing and expanded views. */
(() => {
  if (window.reporttktArtifacts) {
    window.reporttktArtifacts();
    return;
  }
  const initialized = new WeakSet();
  const icons = {
    'Expand': '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 3l6 6m12-6-6 6M3 21l6-6m12 6-6-6"/>',
    'Close': '<path d="m6 6 12 12M6 18 18 6"/>',
    'Zoom out': '<circle cx="10" cy="10" r="6.5"/><path d="m15 15 5.5 5.5M7 10h6"/>',
    'Zoom in': '<circle cx="10" cy="10" r="6.5"/><path d="m15 15 5.5 5.5M7 10h6m-3-3v6"/>',
    'Reset': '<path d="M3 10a9 9 0 1 1 2.5 8M3 4v6h6"/>',
  };
  function initialize(figure) {
    if (initialized.has(figure)) return;
    initialized.add(figure);
    figure.dataset.scaling = 'proportional';
    const inlineViewport = figure.querySelector('.report-artifact-viewport');
    const frame = document.createElement('div');
    frame.className = 'report-artifact-frame';
    inlineViewport.before(frame);
    frame.append(inlineViewport);
    const space = figure.querySelector('.report-artifact-space');
    const content = figure.querySelector('.report-artifact-content');
    let viewport = inlineViewport;
    let dialog = null;
    let previewZoom = 1;
    let previewControls = null;
    let pending = false;
    let printing = false;
    let restoreDialog = () => {};
    let centeredSize = null;
    const full = figure.dataset.width === 'full';
    function button(label, action, parent) {
      const element = document.createElement('button');
      element.type = 'button';
      element.className = 'report-artifact-icon';
      element.setAttribute('aria-label', label);
      element.title = label;
      element.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${icons[label]}</svg>`;
      element.addEventListener('click', action);
      parent.append(element);
      return element;
    }
    function schedule() {
      if (pending || printing) return;
      pending = true;
      requestAnimationFrame(() => {
        pending = false;
        measure();
      });
    }
    function positionExpand() {
      if (dialog) return;
      const visible = inlineViewport.getBoundingClientRect();
      const bounds = space.getBoundingClientRect();
      frame.style.setProperty('--reporttkt-expand-right', `${Math.max(0, visible.right - Math.min(bounds.right, visible.right))}px`);
      frame.style.setProperty('--reporttkt-expand-bottom', `${Math.max(0, visible.bottom - Math.min(bounds.bottom, visible.bottom))}px`);
    }
    function measure() {
      if (!figure.isConnected || printing) return;
      const available = viewport.clientWidth;
      if (!available) return;
      const width = Math.max(content.offsetWidth, content.scrollWidth);
      const height = Math.max(content.offsetHeight, content.scrollHeight);
      const fit = full && width > 0 ? available / width : 1;
      if (!dialog) inlineViewport.style.setProperty('--reporttkt-viewport-height', `${height * fit}px`);
      const scale = fit * (dialog ? previewZoom : 1);
      content.style.setProperty('--reporttkt-artifact-scale', scale);
      space.style.setProperty('--reporttkt-space-width', `${width * scale}px`);
      space.style.setProperty('--reporttkt-space-height', `${height * scale}px`);
      space.style.marginInline = (dialog || figure.dataset.center === 'true') && width * scale < available ? 'auto' : '0';
      space.style.marginTop = dialog ? `${Math.max(0, (viewport.clientHeight - height * scale) / 2)}px` : '0';
      space.classList.add('report-artifact-ready');
      if (dialog) {
        previewControls.minus.disabled = previewZoom <= .25;
        previewControls.plus.disabled = previewZoom >= 4;
        previewControls.status.value = `${Math.round(previewZoom * 100)}%`;
        const size = `${available},${viewport.clientHeight},${width * scale},${height * scale}`;
        if (centeredSize !== size) {
          // Recenter after zoom/resizing; preserve subsequent manual panning.
          viewport.scrollLeft = Math.max(0, (width * scale - available) / 2);
          viewport.scrollTop = Math.max(0, (height * scale - viewport.clientHeight) / 2);
          centeredSize = size;
        }
      }
      if (!dialog) {
        expandButton.hidden = figure.dataset.expand === 'never' || (
          figure.dataset.expand === 'auto' && width * fit <= available + 1 && height * fit <= viewport.clientHeight + 1
        );
        positionExpand();
      }
    }
    const expandButton = button('Expand', () => {
      if (dialog) return;
      dialog = document.createElement('dialog');
      dialog.className = 'report-artifact-dialog';
      dialog.setAttribute('aria-label', figure.querySelector('figcaption')?.textContent || 'Enlarged artifact');
      const controls = document.createElement('div');
      controls.className = 'report-artifact-toolbar';
      controls.setAttribute('role', 'group');
      controls.setAttribute('aria-label', 'Enlarged artifact controls');
      button('Close', () => dialog.close(), controls);
      const changeZoom = delta => {
        previewZoom = Math.min(4, Math.max(.25, previewZoom + delta));
        schedule();
      };
      const minus = button('Zoom out', () => changeZoom(-.25), controls);
      const plus = button('Zoom in', () => changeZoom(.25), controls);
      button('Reset', () => {
        previewZoom = 1;
        centeredSize = null;
        schedule();
      }, controls);
      const status = document.createElement('output');
      status.setAttribute('aria-label', 'Preview zoom');
      status.setAttribute('aria-live', 'polite');
      controls.append(status);
      previewControls = {minus, plus, status};
      const host = document.createElement('div');
      host.className = 'report-artifact';
      Object.assign(host.dataset, figure.dataset);
      host.dataset.center = 'true';
      viewport = document.createElement('div');
      viewport.className = 'report-artifact-viewport';
      viewport.tabIndex = 0;
      viewport.setAttribute('aria-label', 'Enlarged artifact content');
      host.append(viewport);
      dialog.append(controls, host);
      figure.closest('article.reporttkt').append(dialog);
      viewport.append(space);
      dialog.addEventListener('keydown', event => {
        if (event.key !== 'Tab') return;
        const focusable = Array.from(dialog.querySelectorAll(
          'button:not(:disabled), a[href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])'
        )).filter(element => element.getClientRects().length && !element.hidden);
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      });
      restoreDialog = () => {
        if (!dialog) return;
        observer.unobserve(viewport);
        inlineViewport.append(space);
        viewport = inlineViewport;
        dialog.remove();
        dialog = null;
        previewControls = null;
        centeredSize = null;
        measure();
        expandButton.focus();
      };
      dialog.addEventListener('close', restoreDialog, {once: true});
      dialog.showModal();
      observer.observe(viewport);
      measure();
    }, frame);
    expandButton.classList.add('report-artifact-expand');
    expandButton.hidden = true;
    inlineViewport.addEventListener('scroll', positionExpand, {passive: true});
    const observer = new ResizeObserver(schedule);
    observer.observe(content);
    observer.observe(inlineViewport);
    // Asynchronous charts can change their descendants without resizing the host.
    new MutationObserver(schedule).observe(content, {childList: true, subtree: true});
    content.addEventListener('load', schedule, true);
    content.addEventListener('reporttkt:ready', schedule);
    window.addEventListener('resize', schedule);
    window.addEventListener('beforeprint', () => {
      if (dialog) { dialog.close(); restoreDialog(); }
      printing = true;
    });
    window.addEventListener('afterprint', () => {
      printing = false;
      schedule();
    });
    measure();
  }
  window.reporttktArtifacts = () => document.querySelectorAll('figure.report-artifact').forEach(initialize);
  window.reporttktArtifacts();
})();
