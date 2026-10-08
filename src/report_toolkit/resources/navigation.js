/* Each fragment owns its heading lookup and navigation state. */
(() => {
    document.querySelectorAll('nav[data-reporttkt-navigation], .report-reader:not(:has(nav[data-reporttkt-navigation]))').forEach(owner => {
        const nav = owner.matches('.report-reader') ? document.createElement('nav') : owner;
        if (nav.dataset.reporttktNavigationReady) return;
        const scope = owner.closest('.report-layout') || owner.closest('article.reporttkt');
        const report = scope.matches('article') ? scope : scope.querySelector('article.reporttkt');
        if (!report) return;
        const headings = Array.from(report.querySelectorAll('[data-reporttkt-heading]'))
            .filter(heading => heading.closest('article.reporttkt') === report);
        const links = Array.from(nav.querySelectorAll('a'));
        const byId = new Map(headings.map(heading => [heading.id, heading]));
        const resolveHash = hash => {
            try { return byId.get(decodeURIComponent(hash.slice(1))); }
            catch { return null; }
        };
        const byHeading = new Map(links.map(link => [resolveHash(link.hash), link]));
        // Mirror the writer's level hierarchy, including headings beyond toc_depth.
        const paths = new Map();
        const stack = [];
        const included = new Map();
        headings.forEach(heading => {
            const level = Number(heading.dataset.reporttktHeading);
            while (stack.length && stack[stack.length - 1].level >= level) stack.pop();
            const link = byHeading.get(heading) || (stack.length ? stack[stack.length - 1].link : null);
            included.set(heading, link);
            paths.set(heading, [...stack.map(entry => entry.heading), heading]);
            stack.push({level, link, heading});
        });
        nav.dataset.reporttktNavigationReady = 'true';
        const buttons = Array.from(nav.querySelectorAll('.report-toc-toggle'));
        const setExpanded = (button, expanded) => {
            button.setAttribute('aria-expanded', String(expanded));
            const label = button.parentElement.querySelector(':scope > a').textContent;
            button.setAttribute('aria-label', `${expanded ? 'Collapse' : 'Expand'} ${label}`);
            button.parentElement.querySelector(':scope > ul').hidden = !expanded;
        };
        buttons.forEach(button => {
            button.hidden = false;
            setExpanded(button, false);
            button.addEventListener('click', () => {
                setExpanded(button, button.getAttribute('aria-expanded') !== 'true');
            });
        });
        const reader = scope.matches('.report-reader');
        const bar = reader ? scope.querySelector('.report-reader-bar') : null;
        const breadcrumbs = reader ? scope.querySelector('.report-breadcrumbs') : null;
        const sidebar = reader ? scope.querySelector('.report-sidebar') : null;
        const toggle = reader ? scope.querySelector('.report-reader-toggle') : null;
        const desktop = matchMedia('(min-width: 1100px)');
        let barHeight = 0;
        let desktopOpen = true;
        let drawerOpen = false;
        let reflowing = false;
        let returnFocus = null;
        let savedOverflow = '';
        const readingLine = () => reader ? bar.getBoundingClientRect().bottom + 24 : 24;
        const capturePosition = () => {
            const line = readingLine();
            const blocks = [...report.querySelectorAll('h1,h2,h3,h4,h5,h6,p,figure,table,pre,li,blockquote,section > div')];
            const anchor = blocks.find(block => {
                const box = block.getBoundingClientRect();
                return box.top <= line && box.bottom > line;
            }) || blocks.find(block => block.getBoundingClientRect().top >= line);
            return anchor ? {anchor, offset: anchor.getBoundingClientRect().top} : null;
        };
        let readingPosition = null;
        let viewportWidth = window.innerWidth;
        let pendingPosition = null;
        let restorationVersion = 0;
        const cancelRestoration = () => {
            restorationVersion++;
            pendingPosition = null;
            reflowing = false;
        };
        const restorePosition = position => {
            if (!pendingPosition) pendingPosition = position;
            const version = ++restorationVersion;
            reflowing = true;
            requestAnimationFrame(() => requestAnimationFrame(() => {
                if (version !== restorationVersion) return;
                if (pendingPosition && pendingPosition.anchor.isConnected && !matchMedia('print').matches) {
                    window.scrollBy(0, pendingPosition.anchor.getBoundingClientRect().top - pendingPosition.offset);
                }
                pendingPosition = null;
                reflowing = false;
                schedule();
            }));
        };
        const measure = () => {
            if (!reader || matchMedia('print').matches) return;
            barHeight = bar.getBoundingClientRect().height;
            scope.style.setProperty('--reporttkt-bar-height', barHeight + 'px');
        };
        const labelControl = (button, label) => {
            button.setAttribute('aria-label', label);
            button.querySelector('.report-reader-tooltip').textContent = label;
        };
        const syncSidebar = () => {
            if (!sidebar) return;
            const open = desktop.matches ? desktopOpen : drawerOpen;
            scope.classList.toggle('report-reader-sidebar-hidden', !open);
            scope.classList.toggle('report-reader-drawer-open', drawerOpen);
            sidebar.inert = !open;
            sidebar.setAttribute('role', desktop.matches ? 'complementary' : 'dialog');
            sidebar.setAttribute('aria-label', 'Table of contents');
            if (drawerOpen) sidebar.setAttribute('aria-modal', 'true');
            else sidebar.removeAttribute('aria-modal');
            toggle.setAttribute('aria-expanded', String(open));
            labelControl(toggle, open ? 'Hide table of contents' : 'Show table of contents');
        };
        const closeDrawer = (restore = true) => {
            if (!drawerOpen) return;
            drawerOpen = false;
            document.body.style.overflow = savedOverflow;
            report.inert = false;
            bar.inert = false;
            syncSidebar();
            if (restore && returnFocus && returnFocus.isConnected) returnFocus.focus();
        };
        if (reader) {
            scope.dataset.readerReady = 'true';
            let touchInteraction = false;
            scope.addEventListener('pointerdown', event => {
                touchInteraction = event.pointerType === 'touch';
            }, true);
            scope.addEventListener('keydown', () => { touchInteraction = false; }, true);
            scope.querySelectorAll('.report-reader-bar button, .report-reader-toc-header button').forEach(button => {
                const tooltip = button.querySelector('.report-reader-tooltip');
                let dismissed = false;
                const hide = () => { tooltip.hidden = true; };
                const show = () => {
                    if (dismissed || touchInteraction || button.closest('[inert]') || matchMedia('print').matches) return;
                    tooltip.hidden = false;
                    const box = button.getBoundingClientRect();
                    tooltip.style.top = box.bottom + 6 + 'px';
                    tooltip.style.left = Math.max(8, Math.min(
                        box.left, document.documentElement.clientWidth - tooltip.offsetWidth - 8
                    )) + 'px';
                };
                button.addEventListener('pointerenter', event => {
                    if (event.pointerType === 'touch') return;
                    touchInteraction = false;
                    dismissed = false;
                    show();
                });
                button.addEventListener('pointerleave', hide);
                button.addEventListener('focus', show);
                button.addEventListener('blur', () => { hide(); dismissed = false; });
                button.addEventListener('pointerdown', () => { hide(); dismissed = true; });
                button.addEventListener('click', () => { hide(); dismissed = true; });
                button.addEventListener('keydown', event => {
                    if (['Escape', 'Enter', ' '].includes(event.key)) {
                        hide();
                        dismissed = true;
                    }
                });
                document.addEventListener('keydown', event => {
                    if (event.key === 'Escape' && !tooltip.hidden) {
                        hide();
                        dismissed = true;
                    }
                });
                window.addEventListener('resize', hide);
                window.addEventListener('scroll', hide, {passive: true});
            });
            if (!sidebar) scope.classList.add('report-reader-sidebar-hidden');
            measure();
            new ResizeObserver(measure).observe(bar);
            const widthButton = scope.querySelector('.report-width-toggle');
            const widthModes = ['standard', 'wide'];
            let widthIndex = 0;
            const setWidth = () => {
                const mode = widthModes[widthIndex];
                const next = widthModes[(widthIndex + 1) % widthModes.length];
                const title = value => value[0].toUpperCase() + value.slice(1);
                scope.dataset.readerWidth = mode;
                labelControl(widthButton, `Content width: ${title(mode)}. Switch to ${title(next)}.`);
                widthButton.querySelectorAll('[data-reader-icon]').forEach(icon => {
                    icon.toggleAttribute('hidden', icon.dataset.readerIcon !== 'width-' + mode);
                });
            };
            setWidth();
            widthButton.addEventListener('click', () => {
                const position = pendingPosition || capturePosition();
                reflowing = true;
                widthIndex = (widthIndex + 1) % widthModes.length;
                setWidth();
                restorePosition(position);
            });
            const systemTheme = matchMedia('(prefers-color-scheme: dark)');
            let manualTheme = false;
            const themeButton = scope.querySelector('.report-theme-toggle');
            const setTheme = mode => {
                scope.dataset.readerTheme = mode;
                report.dataset.readerTheme = mode;
                document.body.dataset.readerTheme = mode;
                labelControl(themeButton, 'Switch to ' + (mode === 'dark' ? 'light' : 'dark') + ' mode');
                themeButton.querySelector('[data-reader-icon="sun"]').toggleAttribute('hidden', mode !== 'dark');
                themeButton.querySelector('[data-reader-icon="moon"]').toggleAttribute('hidden', mode === 'dark');
            };
            const preferredTheme = () => scope.dataset.readerMode === 'auto'
                ? (systemTheme.matches ? 'dark' : 'light') : scope.dataset.readerMode;
            setTheme(preferredTheme());
            systemTheme.addEventListener('change', () => {
                if (!manualTheme && scope.dataset.readerMode === 'auto') setTheme(preferredTheme());
            });
            themeButton.addEventListener('click', () => {
                manualTheme = true;
                setTheme(scope.dataset.readerTheme === 'dark' ? 'light' : 'dark');
            });
            if (sidebar) {
                syncSidebar();
                toggle.addEventListener('click', () => {
                    if (desktop.matches) {
                        // Keep the article block at the reading line anchored across reflow.
                        const position = pendingPosition || capturePosition();
                        reflowing = true;
                        desktopOpen = !desktopOpen;
                        syncSidebar();
                        restorePosition(position);
                    } else if (drawerOpen) closeDrawer();
                    else {
                        returnFocus = document.activeElement;
                        savedOverflow = document.body.style.overflow;
                        drawerOpen = true;
                        document.body.style.overflow = 'hidden';
                        report.inert = true;
                        bar.inert = true;
                        syncSidebar();
                        sidebar.querySelector('.report-reader-close').focus();
                    }
                });
                sidebar.querySelector('.report-reader-close').addEventListener('click', () => closeDrawer());
                scope.querySelector('.report-reader-backdrop').addEventListener('click', () => closeDrawer());
                scope.addEventListener('keydown', event => {
                    if (!drawerOpen) return;
                    if (event.key === 'Escape') {
                        event.preventDefault();
                        closeDrawer();
                    } else if (event.key === 'Tab') {
                        const focusable = [...sidebar.querySelectorAll('button,a[href]')]
                            .filter(element => element.getClientRects().length && !element.hidden);
                        const first = focusable[0], last = focusable[focusable.length - 1];
                        if (event.shiftKey && document.activeElement === first) {
                            event.preventDefault(); last.focus();
                        } else if (!event.shiftKey && document.activeElement === last) {
                            event.preventDefault(); first.focus();
                        }
                    }
                });
                desktop.addEventListener('change', () => {
                    closeDrawer();
                    syncSidebar();
                    if (sidebar.inert && sidebar.contains(document.activeElement)) toggle.focus();
                    measure();
                });
            }
        }
        let automaticExpansion = true;
        const collapseAll = reader ? scope.querySelector('.report-reader-collapse') : null;
        if (collapseAll) collapseAll.addEventListener('click', () => {
            automaticExpansion = false;
            buttons.forEach(button => setExpanded(button, false));
        });
        let structural = null;
        let active = null;
        const reveal = link => {
            let entry = link.parentElement;
            while (entry && nav.contains(entry)) {
                const button = entry.querySelector(':scope > .report-toc-toggle');
                if (button) setExpanded(button, true);
                entry = entry.parentElement.closest('li');
            }
        };
        const keepVisible = link => {
            if (!link.getClientRects().length) return;
            if (!nav.closest('.report-sidebar') || nav.scrollHeight <= nav.clientHeight) return;
            const box = nav.getBoundingClientRect();
            const target = link.getBoundingClientRect();
            const header = reader ? nav.querySelector('.report-reader-toc-header') : null;
            const visibleTop = box.top + (header ? header.getBoundingClientRect().height : 0);
            if (target.top < visibleTop) nav.scrollTop += target.top - visibleTop;
            else if (target.bottom > box.bottom) nav.scrollTop += target.bottom - box.bottom;
        };
        const activate = (heading, explicit = false) => {
            if (reader && heading && structural !== heading) {
                structural = heading;
                breadcrumbs.replaceChildren();
                (paths.get(heading) || []).forEach((ancestor, index, path) => {
                    const crumb = document.createElement('a');
                    crumb.href = '#' + ancestor.id;
                    const label = document.createElement('span');
                    label.className = 'report-breadcrumb-label';
                    label.textContent = ancestor.textContent;
                    crumb.title = ancestor.textContent;
                    crumb.append(label);
                    if (index === path.length - 1) crumb.setAttribute('aria-current', 'location');
                    breadcrumbs.append(crumb);
                });
            }
            const link = included.get(heading);
            if (!link) return;
            const changed = active !== link;
            if (changed) {
                if (active) active.removeAttribute('aria-current');
                active = link;
                active.setAttribute('aria-current', 'location');
                if (reader) {
                    nav.querySelectorAll('[data-reader-ancestor]').forEach(entry => entry.removeAttribute('data-reader-ancestor'));
                    let entry = link.parentElement.parentElement.closest('li');
                    while (entry && nav.contains(entry)) {
                        entry.querySelector(':scope > a').setAttribute('data-reader-ancestor', '');
                        entry = entry.parentElement.closest('li');
                    }
                }
            }
            if (changed || explicit) {
                if (!reader || automaticExpansion) reveal(link);
                keepVisible(link);
            }
        };
        const fromHash = () => resolveHash(location.hash);
        const update = () => {
            if (matchMedia('print').matches || reflowing) return;
            let selected = headings[0];
            headings.forEach(heading => {
                if (heading.getBoundingClientRect().top <= readingLine() + (reader ? 1 : 0)) selected = heading;
            });
            activate(selected);
            if (reader) readingPosition = capturePosition();
        };
        let frame = null;
        const schedule = () => {
            if (frame !== null) return;
            frame = requestAnimationFrame(() => {
                frame = null;
                update();
            });
        };
        scope.addEventListener('click', event => {
            const link = event.target.closest('a');
            if (!link || !scope.contains(link) || event.button !== 0 || event.ctrlKey ||
                event.metaKey || event.shiftKey || event.altKey) return;
            if (link.origin !== location.origin || link.pathname !== location.pathname ||
                link.search !== location.search) return;
            const heading = resolveHash(link.hash);
            if (!heading) return;
            event.preventDefault();
            // Native global ID lookup cannot distinguish repeated fragment anchors.
            if (reader) cancelRestoration();
            history.pushState(null, '', link.hash);
            if (reader && nav.contains(link)) automaticExpansion = true;
            activate(heading, true);
            closeDrawer(false);
            heading.scrollIntoView();
            if (reader) {
                heading.tabIndex = -1;
                heading.focus({preventScroll: true});
            }
        });
        window.addEventListener('hashchange', () => {
            const heading = fromHash();
            if (heading) {
                if (reader) cancelRestoration();
                activate(heading, true);
                if (reader) {
                    closeDrawer(false);
                    heading.scrollIntoView();
                    heading.tabIndex = -1;
                    heading.focus({preventScroll: true});
                }
            }
            else schedule();
        });
        window.addEventListener('scroll', schedule, {passive: true});
        window.addEventListener('resize', () => {
            if (reader && window.innerWidth !== viewportWidth && !matchMedia('print').matches) {
                viewportWidth = window.innerWidth;
                measure();
                restorePosition(readingPosition);
            } else schedule();
        });
        window.addEventListener('load', schedule);
        report.addEventListener('load', schedule, true);
        if (document.fonts) document.fonts.ready.then(schedule);
        if (typeof ResizeObserver !== 'undefined') new ResizeObserver(schedule).observe(report);
        const initial = fromHash();
        if (initial) {
            activate(initial, true);
            if (reader) requestAnimationFrame(() => initial.scrollIntoView());
        }
        else update();
    });
})();
