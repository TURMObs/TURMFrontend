async function showConfirmModal(
  title,
  message,
  confirmText = "Confirm",
  cancelText = "Cancel",
) {
  const result = await showModal(title, createModalText(message), {
    allowDismiss: false,
    buttons: [
      {
        id: "cancel",
        text: cancelText,
        secondary: true,
      },
      {
        id: "confirm",
        text: confirmText,
      },
    ],
  });
  return result === "confirm";
}

async function showAlertModal(title, message) {
  await showModal(title, createModalText(message), {
    allowDismiss: true,
    buttons: [],
  });
}

function createModalText(message) {
  const modalMessage = document.createElement("p");
  modalMessage.className = "text";
  modalMessage.textContent = message;
  return modalMessage;
}

async function showModal(
  title,
  content,
  options = { allowDismiss: true, buttons: [] },
) {
  return new Promise((resolve) => {
    const modal = document.getElementById("modal");
    const modalContent = document.getElementById("modal-content");
    const modalTitle = document.getElementById("modal-title");
    const modalSeparator = document.getElementById("modal-separator");
    const modalActions = document.getElementById("modal-actions");

    showElement(modal, "flex");
    modalTitle.textContent = title;

    modalContent.innerHTML = "";
    modalContent.appendChild(content);

    if (options.buttons && options.buttons.length > 0) {
      showElement(modalSeparator, "flex");
      showElement(modalActions, "flex");
      modalActions.innerHTML = "";
      for (var button of options.buttons) {
        const buttonElement = document.createElement("button");
        const buttonId = button.id;
        if (button.secondary) {
          buttonElement.className = "btn-secondary";
        } else {
          buttonElement.className = "btn";
        }
        buttonElement.textContent = button.text;
        buttonElement.addEventListener("click", () => {
          button.onClick?.();
          hideModal();
          resolve(buttonId);
        });
        modalActions.appendChild(buttonElement);
      }
    } else {
      hideElement(modalSeparator);
      hideElement(modalActions);
    }

    const windowClickHandler = function (event) {
      if (event.target === modal) {
        dismissHandler();
      }
    };

    const keydownHandler = function (event) {
      if (event.key === "Escape") {
        dismissHandler();
      }
    };

    const dismissHandler = () => {
      window.removeEventListener("click", windowClickHandler);
      document.removeEventListener("keydown", keydownHandler);
      hideModal();
      resolve(null);
    };

    if (options.allowDismiss) {
      window.addEventListener("click", windowClickHandler);
      document.addEventListener("keydown", keydownHandler);
    }
  });
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
