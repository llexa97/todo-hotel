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
    const weekSections = document.querySelectorAll('.week-section');
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
