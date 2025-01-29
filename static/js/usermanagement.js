function toggleInput(fieldId) {
    const field = document.getElementById(fieldId);
    field.style.display = field.style.display === 'none' ? 'block' : 'none';
}


function copyLink() {
    var linkText = document.getElementById("invitationLink").textContent;
    navigator.clipboard.writeText(linkText).then(() => {
        alert("Link copied to clipboard!");
    });
}

async function createInvitation() {
    const form = document.getElementById('invitationForm');
    const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
    const email = form.querySelector('input[name="email"]').value;

    if (document.getElementById('quotaField').style.display === 'none') {
        document.getElementById('id_quota')?.remove();
    }
    if (document.getElementById('lifetimeField').style.display === 'none') {
        document.getElementById('id_lifetime')?.remove();
    }

    const formData = new FormData(form);

    try {
        const response = await fetch("{%  url 'has-invitation' %}", {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                email: email,
            }),
        });
        let data = await response.json();
        if (data['has_invitation'] === true) {
            if (!confirm("An invitation already exists for this email. Do you want to override the invitation?")) {
                return;
            }
        }
        const generateResponse = await fetch("{% url 'generate-user-invitation' %}", {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
            },
            body: formData,
        });
        let linkData = await generateResponse.json();
        if (generateResponse.ok) {
            document.getElementById('modal-link').textContent = linkData['link'];
            document.getElementById('modal').style.display = 'flex'; // Show the modal
        } else {
            if (linkData['error']) {
                alert("Failed to create invitation: " + linkData['error']);
            } else {
                alert("Failed to create invitation. Please try again.");
            }
        }
    } catch (error) {
        alert("Failed to create invitation. Please try again.");
    }
}


function copyToClipboard() {
    const link = document.getElementById('modal-link').textContent;
    const copyButton = document.getElementById('copyButton');  // Get the button element

    navigator.clipboard.writeText(link).then(() => {
        // Save the original button styles
        const originalBackgroundColor = copyButton.style.backgroundColor;
        const originalText = copyButton.textContent;

        // Provide feedback by changing the button color and text
        copyButton.style.backgroundColor = '#45a049';  // Slightly darker green
        copyButton.textContent = 'Link copied!';

        // Reset button color and text after a short delay
        setTimeout(() => {
            copyButton.style.backgroundColor = originalBackgroundColor;  // Restore original color
            copyButton.textContent = originalText;   // Restore original text
        }, 1500); // Feedback stays for 1.5 seconds
    });
}

function copyLinkToClipboard(link) {
    navigator.clipboard.writeText(link).then(() => {
        alert("Link copied to clipboard!");
    });
}


function closeModal() {
    document.getElementById('modal').style.display = 'none';

    // Clear form inputs
    const form = document.getElementById('invitationForm');
    form.reset();
    location.reload();
}

async function deleteUser(userId) {
    if (!confirm("Are you sure you want to mark this user for deletion?")) {
        return;  // If the user cancels, do nothing
    }

    const form = document.getElementById(`delete-user-${userId}`);
    const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;

    try {
        const response = await fetch("{% url 'delete-user' 0 %}".replace("0", userId), {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message || "User marked for deletion!");
            form.closest('tr').remove(); // Remove the row from the table
        } else {
            alert(data.error || "An error occurred while marking the user for deletion.");
        }
    } catch (error) {
        alert("Failed to delete the user. Please try again.");
    }
}


async function deleteInvitation(invitationId) {
    const form = document.getElementById(`delete-invitation-${invitationId}`);
    const csrfToken = form.querySelector('input[name="csrfmiddlewaretoken"]').value;
    console.log("Invitation ID: ", invitationId);
    try {
        const response = await fetch("{% url 'delete-invitation' 0 %}".replace("0", invitationId), {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/json',
            },
        });

        const data = await response.json();

        if (response.ok) {
            alert(data.message || "Invitation deleted successfully!");
            location.reload();
        } else {
            alert(data.error || "An error occurred while deleting the invitation.");
        }
    } catch (error) {
        alert("Failed to delete the invitation. Please try again.");
    }
}