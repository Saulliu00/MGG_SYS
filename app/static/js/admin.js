// Show/Hide Add User Modal
function showAddUserModal() {
    document.getElementById('addUserModal').classList.add('active');
}

function hideAddUserModal() {
    document.getElementById('addUserModal').classList.remove('active');
    document.getElementById('addUserForm').reset();
}

// Show/Hide Reset Password Modal
function showResetPasswordModal(userId, username) {
    document.getElementById('resetUserId').value = userId;
    document.getElementById('resetUsername').textContent = username;
    document.getElementById('resetPasswordModal').classList.add('active');
}

function hideResetPasswordModal() {
    document.getElementById('resetPasswordModal').classList.remove('active');
    document.getElementById('resetPasswordForm').reset();
}

// Add User
async function addUser() {
    const form = document.getElementById('addUserForm');
    const formData = new FormData(form);

    try {
        const response = await fetch('/admin/user/add', {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            hideAddUserModal();
            location.reload();
        } else {
            alert('错误: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('操作失败');
    }
}

// Toggle User Status
async function toggleUser(userId) {
    if (!confirm('确定要切换该用户的状态吗？')) {
        return;
    }

    try {
        const response = await fetch(`/admin/user/${userId}/toggle`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            location.reload();
        } else {
            alert('错误: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('操作失败');
    }
}

// Delete User
async function deleteUser(userId, username) {
    if (!confirm(`确定要删除用户 "${username}" 吗？此操作不可恢复！`)) {
        return;
    }

    try {
        const response = await fetch(`/admin/user/${userId}/delete`, {
            method: 'POST'
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            location.reload();
        } else {
            alert('错误: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('操作失败');
    }
}

// Reset Password
async function resetPassword() {
    const form = document.getElementById('resetPasswordForm');
    const userId = document.getElementById('resetUserId').value;
    const formData = new FormData(form);

    try {
        const response = await fetch(`/admin/user/${userId}/reset-password`, {
            method: 'POST',
            body: formData
        });

        const result = await response.json();

        if (result.success) {
            alert(result.message);
            hideResetPasswordModal();
        } else {
            alert('错误: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('操作失败');
    }
}

// Close modal when clicking outside
window.onclick = function(event) {
    const addModal = document.getElementById('addUserModal');
    const resetModal = document.getElementById('resetPasswordModal');

    if (event.target === addModal) {
        hideAddUserModal();
    }
    if (event.target === resetModal) {
        hideResetPasswordModal();
    }
}
