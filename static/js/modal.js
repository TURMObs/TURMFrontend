async function showConfirmModal(title, message, confirmText = "Confirm") {
  const result = await showModal(title, message, {
    buttons: [
      {
        id: "cancel",
        text: "Cancel",
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

async function showModal(
  title,
  message,
  options = { allowDismiss: true, buttons: [] },
) {
  return new Promise((resolve) => {
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
      hideElement(modalSeperator);
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
