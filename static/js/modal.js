function showModal(
  title,
  message,
  options = { allowDismiss: true, buttons: [] },
) {
  const modal = document.getElementById("modal");
  const modalMessage = document.getElementById("modal-message");
  const modalTitle = document.getElementById("modal-title");
  const modalSeperator = document.getElementById("modal-seperator");
  const modalActions = document.getElementById("modal-actions");

  showElement(modal, "block");
  modalTitle.textContent = title;
  modalMessage.textContent = message;

  if (options.buttons && options.buttons.length > 0) {
    showElement(modalSeperator, "flex");
    showElement(modalActions, "flex");
    modalActions.innerHTML = "";
    for (var button of options.buttons) {
      const buttonElement = document.createElement("button");
      if (button.secondary) {
        buttonElement.className = "btn-secondary";
      } else {
        buttonElement.className = "btn";
      }
      buttonElement.textContent = button.text;
      buttonElement.addEventListener("click", button.onClick);
      modalActions.appendChild(buttonElement);
    }
  } else {
    hideElement(modalSeperator);
    hideElement(modalActions);
  }

  if (options.allowDismiss) {
    window.onclick = function (event) {
      if (event.target === modal) {
        hideModal();
      }
    };

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideModal();
      }
    });
  }
}

function hideModal() {
  hideElement(document.getElementById("modal"));
}

function showElement(element, style) {
  element.style.display = style;
}

function hideElement(element) {
  element.style.display = "none";
}
