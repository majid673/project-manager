// Manage modal and focus
const modal = document.getElementById("editModal");
let currentTaskId = null;
let calendar;
let currentProjectId;
let currentUserRole = null;

// Function to fetch user's role and store it globally
function fetchUserRole() {
    return fetch('/api/user/role')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            currentUserRole = data.role;
            return currentUserRole;
        })
        .catch(error => console.error('Error fetching user role:', error));
}

// Function to fetch and update task list (only for project pages)
function fetchTaskList(projectId) {
    if (!window.location.pathname.startsWith('/project/')) return; // Only run for project pages
    currentProjectId = projectId;
    fetch(`/project/${projectId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.text();
        })
        .then(html => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(html, 'text/html');
            const newTasksList = doc.getElementById('tasksList').innerHTML;
            document.getElementById('tasksList').innerHTML = newTasksList;
            updateCalendar(projectId); // Update calendar with tasks for this project
            setupEventListeners(); // Re-attach event listeners after updating
            return fetchUserRole(); // Fetch user's role after updating the list
        })
        .then(role => updateButtonsBasedOnRole(role)) // Update buttons based on the role
        .catch(error => console.error('Error fetching task list:', error));
}

function openEditModal(taskId) {
    console.log("Edit button clicked for task ID:", taskId);
    fetch(`/api/tasks/${taskId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(task => {
            document.getElementById("editTitle").value = task.title;
            document.getElementById("editDeadline").value = task.deadline.split('T')[0]; // Take only the date part
            document.getElementById("editPriority").value = task.priority;
            document.getElementById("editStatus").value = task.status;
            currentTaskId = taskId;
            modal.style.display = "block";
            setupModalFocus();
        })
        .catch(error => console.error('Error fetching task:', error));
}

function saveEdit() {
    const title = document.getElementById("editTitle").value;
    const deadline = document.getElementById("editDeadline").value;
    const priority = document.getElementById("editPriority").value;
    const status = document.getElementById("editStatus").value;

    fetch(`/task/edit/${currentTaskId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title: title,
            deadline: deadline,
            priority: priority,
            status: status
        })
    })
    .then(response => {
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        return response.json();
    })
    .then(data => {
        if (data.status === "success") {
            console.log("Edit successful:", data.task);
            const projectId = window.location.pathname.split('/').pop();
            updateTaskList(data.tasks);
            updateCalendar(projectId); // Update calendar after editing
            closeModal();
        } else {
            console.error("Edit failed:", data.message);
            alert("Error: " + data.message);
        }
    })
    .catch(error => console.error('Fetch error:', error));
}

function closeModal() {
    modal.style.display = "none";
}

window.addEventListener("click", function(event) {
    if (event.target == modal) {
        closeModal();
    }
});

// Smart focus in modal
const editTitle = document.getElementById("editTitle");
const editDeadline = document.getElementById("editDeadline");
const editPriority = document.getElementById("editPriority");
const editStatus = document.getElementById("editStatus");

function setupModalFocus() {
    console.log("Setting up modal focus...");
    editTitle.addEventListener("keypress", function(e) {
        console.log("Title keypress:", e.key);
        if (e.key === "Enter") {
            e.preventDefault();
            editDeadline.focus();
        }
    });

    editDeadline.addEventListener("change", function(e) {
        console.log("Deadline changed:", e.target.value);
        editPriority.focus();
    });

    editPriority.addEventListener("change", function(e) {
        console.log("Priority changed:", e.target.value);
        editStatus.focus();
    });

    editStatus.addEventListener("change", function(e) {
        console.log("Status changed:", e.target.value);
        document.querySelector('.modal button[onclick="saveEdit()"]').focus();
    });
}

// Update task list after editing or deleting
function updateTaskList(tasks) {
    const tasksList = document.getElementById("tasksList");
    tasksList.innerHTML = "";
    tasks.forEach(task => {
        const li = document.createElement("li");
        li.className = "task-item";
        if (currentUserRole) { // Use the globally stored role
            li.innerHTML = `
                <div class="task-details">
                    ${task.title} - Deadline: ${task.deadline} - Priority: ${task.priority} - Status: ${task.status}
                </div>
                <div class="task-actions">
                    ${currentUserRole === 'Manager' || currentUserRole === 'Editor' ? '<button onclick="openEditModal(' + task.id + ')">Edit</button>' : ''}
                    ${currentUserRole === 'Manager' ? '<form method="POST" action="/task/delete/' + task.id + '" class="delete-form"><button type="submit" name="delete" value="' + task.id + '">Delete</button></form>' : ''}
                </div>
            `;
            tasksList.appendChild(li);
        } else {
            fetchUserRole().then(role => {
                currentUserRole = role;
                updateTaskList(tasks); // Recursively update with the role
            });
        }
    });
    setupEventListeners(); // Re-attach event listeners after updating
}

// Update buttons based on role after fetching
function updateButtonsBasedOnRole(role) {
    currentUserRole = role;
    const tasksList = document.getElementById("tasksList");
    const taskItems = tasksList.querySelectorAll('.task-item');
    taskItems.forEach(item => {
        const taskId = item.querySelector('button[onclick^="openEditModal"]')?.getAttribute('onclick')?.match(/\d+/)?.[0];
        if (taskId) {
            item.innerHTML = `
                <div class="task-details">
                    ${item.querySelector('.task-details').textContent}
                </div>
                <div class="task-actions">
                    ${role === 'Manager' || role === 'Editor' ? '<button onclick="openEditModal(' + taskId + ')">Edit</button>' : ''}
                    ${role === 'Manager' ? '<form method="POST" action="/task/delete/' + taskId + '" class="delete-form"><button type="submit" name="delete" value="' + taskId + '">Delete</button></form>' : ''}
                </div>
            `;
        }
    });
    setupEventListeners(); // Re-attach event listeners after updating buttons
}

// Setup event listeners for delete forms
function setupEventListeners() {
    document.querySelectorAll('.delete-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            const taskId = this.querySelector('button[name="delete"]').value;
            if (confirm("Are you sure you want to delete this task?")) {
                fetch(`/task/delete/${taskId}`, {
                    method: 'POST'
                })
                .then(response => {
                    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                    return response.json();
                })
                .then(data => {
                    if (data.status === "success") {
                        const projectId = window.location.pathname.split('/').pop();
                        updateTaskList(data.tasks);
                        updateCalendar(projectId); // Update calendar after deleting
                    } else {
                        alert("Error deleting task: " + data.message);
                    }
                })
                .catch(error => console.error('Error deleting task:', error));
            }
        });
    });
}

// Initial setup when page loads
document.addEventListener('DOMContentLoaded', function() {
    const projectId = window.location.pathname.split('/').pop();
    if (window.location.pathname.startsWith('/project/') && projectId) {
        fetchTaskList(projectId);
    }
    var calendarEl = document.getElementById('calendar');
    if (calendarEl) { // Only initialize calendar if element exists
        calendar = new FullCalendar.Calendar(calendarEl, {
            initialView: 'dayGridMonth',
            events: function(info, successCallback, failureCallback) {
                fetch(`/api/tasks?project_id=${currentProjectId || window.location.pathname.split('/').pop()}`)
                    .then(response => {
                        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
                        return response.json();
                    })
                    .then(tasks => {
                        const events = tasks.map(task => ({
                            title: `${task.title} (Priority: ${task.priority})`,
                            start: task.deadline,
                            color: task.priority === "High" ? "red" : task.priority === "Medium" ? "blue" : "green"
                        }));
                        successCallback(events);
                    })
                    .catch(error => {
                        console.error('Error fetching tasks for calendar:', error);
                        failureCallback(error);
                    });
            }
        });
        calendar.render();
    }
});

// Update calendar with new tasks for the current project
function updateCalendar(projectId) {
    fetch(`/api/tasks?project_id=${projectId}`)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(tasks => {
            const events = tasks.map(task => ({
                title: `${task.title} (Priority: ${task.priority})`,
                start: task.deadline,
                color: task.priority === "High" ? "red" : task.priority === "Medium" ? "blue" : "green"
            }));
            calendar.removeAllEvents();
            calendar.addEventSource(events);
            calendar.render();
        })
        .catch(error => console.error('Error updating calendar:', error));
}