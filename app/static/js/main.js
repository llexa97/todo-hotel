// Main JavaScript for Hotel Le Trèfle Task Management

document.addEventListener('DOMContentLoaded', function() {
    // Set default date to today for the form
    const dateInput = document.getElementById('due_date');
    if (dateInput && !dateInput.value) {
        const today = new Date().toISOString().split('T')[0];
        dateInput.value = today;
    }

    // Auto-hide flash messages after 5 seconds
    setTimeout(function() {
        const flashMessages = document.querySelector('.flash-messages');
        if (flashMessages) {
            flashMessages.style.transition = 'opacity 0.5s';
            flashMessages.style.opacity = '0';
            setTimeout(() => flashMessages.remove(), 500);
        }
    }, 5000);

    // Enable collapsible weeks on the "Toutes les tâches" view
    const weekSections = document.querySelectorAll('[data-week-key]');
    if (weekSections.length > 0) {
        const storageKeyPrefix = 'todo-hotel-week-collapsed:';
        const canPersistState = (() => {
            try {
                const testKey = `${storageKeyPrefix}__test__`;
                localStorage.setItem(testKey, '1');
                localStorage.removeItem(testKey);
                return true;
            } catch (error) {
                return false;
            }
        })();

        weekSections.forEach((section) => {
            const toggle = section.querySelector('[data-week-toggle]');
            const content = section.querySelector('[data-week-content]');
            if (!toggle || !content) {
                return;
            }

            const storageKey = `${storageKeyPrefix}${section.dataset.weekKey || ''}`;
            const shouldCollapse = canPersistState && localStorage.getItem(storageKey) === '1';

            if (shouldCollapse) {
                section.classList.add('is-collapsed');
                content.setAttribute('hidden', 'hidden');
                toggle.setAttribute('aria-expanded', 'false');
            }

            toggle.addEventListener('click', () => {
                const collapsed = section.classList.toggle('is-collapsed');

                if (collapsed) {
                    content.setAttribute('hidden', 'hidden');
                    toggle.setAttribute('aria-expanded', 'false');
                } else {
                    content.removeAttribute('hidden');
                    toggle.setAttribute('aria-expanded', 'true');
                }

                if (canPersistState) {
                    try {
                        if (collapsed) {
                            localStorage.setItem(storageKey, '1');
                        } else {
                            localStorage.removeItem(storageKey);
                        }
                    } catch (error) {
                        // Ignore storage issues silently
                    }
                }
            });
        });
    }

    // Enable collapsible days on the "Terminées" view
    const completedDaySections = document.querySelectorAll('[data-completed-day]');
    console.log('🔍 Completed day sections found:', completedDaySections.length);

    if (completedDaySections.length > 0) {
        const storageKeyPrefix = 'todo-hotel-completed-collapsed:';
        const canPersistState = (() => {
            try {
                const testKey = `${storageKeyPrefix}__test__`;
                localStorage.setItem(testKey, '1');
                localStorage.removeItem(testKey);
                console.log('✅ LocalStorage is available');
                return true;
            } catch (error) {
                console.log('❌ LocalStorage NOT available:', error);
                return false;
            }
        })();

        completedDaySections.forEach((section, index) => {
            console.log(`📅 Processing completed section ${index + 1}:`, section.dataset.completedDay);

            const toggle = section.querySelector('[data-completed-toggle]');
            const content = section.querySelector('[data-completed-content]');

            console.log('  Toggle found:', !!toggle);
            console.log('  Content found:', !!content);

            if (!toggle || !content) {
                console.log('  ⚠️ Skipping section - toggle or content missing');
                return;
            }

            const storageKey = `${storageKeyPrefix}${section.dataset.completedDay || ''}`;
            const shouldCollapse = canPersistState && localStorage.getItem(storageKey) === '1';
            console.log('  Storage key:', storageKey);
            console.log('  Should collapse on load:', shouldCollapse);

            if (shouldCollapse) {
                section.classList.add('is-collapsed');
                content.setAttribute('hidden', 'hidden');
                toggle.setAttribute('aria-expanded', 'false');
                console.log('  ✓ Section collapsed on load');
            }

            toggle.addEventListener('click', () => {
                console.log('🖱️ Toggle clicked for:', section.dataset.completedDay);
                const collapsed = section.classList.toggle('is-collapsed');
                console.log('  New state - collapsed:', collapsed);

                if (collapsed) {
                    content.setAttribute('hidden', 'hidden');
                    toggle.setAttribute('aria-expanded', 'false');
                } else {
                    content.removeAttribute('hidden');
                    toggle.setAttribute('aria-expanded', 'true');
                }

                if (canPersistState) {
                    try {
                        if (collapsed) {
                            localStorage.setItem(storageKey, '1');
                            console.log('  💾 Saved collapsed state to localStorage');
                        } else {
                            localStorage.removeItem(storageKey);
                            console.log('  💾 Removed collapsed state from localStorage');
                        }
                    } catch (error) {
                        console.log('  ❌ Error saving to localStorage:', error);
                    }
                }
            });

            console.log('  ✓ Event listener attached');
        });
    } else {
        console.log('ℹ️ No completed day sections found on this page');
    }

    // Maintain consistent task ordering after HTMX updates
    const sortTaskList = (list) => {
        if (!list) return;
        const items = Array.from(list.querySelectorAll('.task-item'));
        items.sort((a, b) => {
            const doneA = a.dataset.isDone === 'true';
            const doneB = b.dataset.isDone === 'true';
            if (doneA !== doneB) {
                return doneA - doneB;
            }

            const orderA = Number.parseInt(a.dataset.displayOrder || '0', 10);
            const orderB = Number.parseInt(b.dataset.displayOrder || '0', 10);
            if (orderA !== orderB) {
                return orderA - orderB;
            }

            const createdA = Date.parse(a.dataset.createdAt || '0') || 0;
            const createdB = Date.parse(b.dataset.createdAt || '0') || 0;
            return createdB - createdA;
        });

        items.forEach((item) => list.appendChild(item));
    };

    document.body.addEventListener('htmx:afterSwap', (event) => {
        if (!event.detail || !event.detail.target) {
            return;
        }

        const swapped = event.detail.target;
        if (!swapped.classList || !swapped.classList.contains('task-item')) {
            return;
        }

        const currentItem = swapped.id ? document.getElementById(swapped.id) : swapped;
        if (!currentItem) {
            return;
        }

        const list = currentItem.closest('.task-list');
        if (list) {
            sortTaskList(list);
        }
    });
});

// Toggle edit form
function toggleEdit(taskId) {
    const editForm = document.getElementById('edit-form-' + taskId);
    const taskItem = editForm.parentElement;
    const taskContent = taskItem.querySelector('.task-content');
    const taskActions = taskItem.querySelector('.task-actions');
    
    if (editForm.classList.contains('active')) {
        // Cancel edit
        editForm.classList.remove('active');
        taskContent.style.display = 'flex';
        if (taskActions) taskActions.style.display = 'flex';
    } else {
        // Start edit
        editForm.classList.add('active');
        taskContent.style.display = 'none';
        if (taskActions) taskActions.style.display = 'none';
        editForm.querySelector('input[name="title"]').focus();
    }
}
