/**
 * event hook that prevents the specified characters from being typed into a textfield
 * @param event html event that was triggered
 * @param el the HTML element that triggered the event
 * @param suppressed RegExp of what should be suppressed
 */

function discardInput(event, el, suppressed) {
  el.value = el.value.replace(RegExp(suppressed), "");
  event.stopPropagation();
  event.preventDefault();
}

/**
 * Checks the first radio button of a group of radio buttons, if none are selected
 * Is supposed to be called on page load
 */
function checkRadioIfNoneSelected() {
  const divs = document.getElementsByClassName("radio-input-div");
  for (let div of divs) {
    const radios = Array.from(div.children)
      .filter((el) => el.tagName === "INPUT")
      .filter((el) => el.type === "radio");
    let selected_or_first_radio = radios[0];
    for (let radio of radios) {
      if (radio.checked === true) {
        selected_or_first_radio = radio;
        break;
      }
    }
    selected_or_first_radio.checked = true;
    if (selected_or_first_radio.onclick != null)
      selected_or_first_radio.click();
  }
}

/**
 * disables all inputs that are part of the dependency_type, but not of the given dependency
 * enables all inputs that are part of the dependency_type and of the given dependency
 * @param dependency_type
 * @param dependency
 */
function disableInputs(dependency_type, dependency) {
  const dependent_inputs = Array.from(
    document.getElementsByTagName("INPUT"),
  ).filter((el) => !!el.getAttribute(dependency_type));

  for (let input of dependent_inputs) {
    if (
      Array.from(input.getAttribute(dependency_type).split(" ")).some(
        (el) => el === dependency,
      )
    ) {
      input.disabled = false;
    } else {
      input.disabled = true;
      input.checked = false;
    }
  }
}

/**
 * hides all inputs and corresponding labels that are part of the dependency_type, but not of the given dependency
 * un-hides all inputs and corresponding labels that are part of the dependency_type and of the given dependency
 * @param dependencyType
 * @param dependency
 */
function hideInputs(dependencyType, dependency) {
  const dependent_inputs = Array.from(
    document.getElementsByTagName("INPUT"),
  ).filter((el) => !!el.getAttribute(dependencyType));

  const toCallLater = [];

  for (let input of dependent_inputs) {
    const hideEl = !Array.from(
      input.getAttribute(dependencyType).split(" "),
    ).some((el) => el === dependency);
    let parent = input.parentElement;
    if (parent.classList.contains("radio-input-div")) {
      parent = input.parentElement.parentElement;
    }
    if (hideEl) {
      parent.style.display = "none";
      input.disabled = true;
    } else {
      parent.removeAttribute("style");
      input.disabled = false;
      if (input.type === "radio" && input.checked && input.onclick != null)
        toCallLater.push(input);
    }
  }
  toCallLater.forEach((callable) => callable.click());
}

function updateDateDependency(el) {
  const end = document.getElementById(el.id.replace(RegExp("start"), "end"));
  if (end === null) return;
  end.min = el.value;
  if (Date.parse(end.min) > Date.parse(end.value)) {
    end.value = end.min;
  }
}

/**
 * submits form to specified address. In case of failure it marks the errors in html. In case of success user gets redirected.
 * @param event the form submission event
 * @param form the form element that is to be submitted
 * @param postAddress web address to submit to
 * @param redirectAddress address where a successful submit redirects to
 */
function submitForm(event, form, postAddress, redirectAddress) {
  event.preventDefault();
  event.stopPropagation();

  let data = new FormData(form);

  for (let [name, value] of gatherDefaultValues()) {
    data.set(name, value);
  }

  fetch(postAddress, {
    method: "POST",
    body: data,
    credentials: "include",
    headers: {
      Accept: "application/json",
    },
  })
    .then((response) => {
      if (response.ok) location.href = redirectAddress;
      else
        response
          .json()
          .then((jsonResponse) => {
            clearErrorMessages();
            for (let key in jsonResponse) {
              if (key !== "target") {
                let name = key;
                let escapeGrid = false;
                if (
                  key === "time_range" ||
                  key === "start_time" ||
                  key === "year_range"
                ) {
                  name = "start_observation";
                  escapeGrid = true;
                }
                let element = document.getElementById("id_" + name);
                addErrorMessage(element, jsonResponse[key][0], escapeGrid);
              } else {
                for (let subKey in jsonResponse.target) {
                  let element = document.getElementById("id_" + subKey);
                  addErrorMessage(element, jsonResponse[key][subKey][0]);
                }
              }
            }
          })
          .catch((error) => console.log(error, response));
    })
    .catch((error) => console.error("Error:", error));
}

/**
 * Returns dict of empty inputs that have a placeholder
 */
function gatherDefaultValues() {
  const emptyInputs = Array.from(
    document.getElementsByTagName("INPUT"),
  ).filter((el) => el.value === "");

  const out = new Map();

  for (let input of emptyInputs) {
    const placeholder = input.getAttribute("placeholder");
    if (placeholder && input.id !== "id_catalog_id") {
      out.set(input.getAttribute("name"), placeholder);
    }
  }
  return out;
}

/**
 * Adds an error note under the element with the message text.
 * @param element that the error is for
 * @param message text that should be displayed
 * @param escapeGrid when the element is in a grid-input-div this param specifies if it should be displayed in the same cell or under the whole grid (useful for duration inputs)
 */
function addErrorMessage(element, message, escapeGrid = false) {
  const messageElement = "<span>" + message + "</span>";
  const iconElement = '<i class="bx bx-error-circle"></i>';
  const error = document.createElement("div");
  error.classList.add("error-msg");
  error.innerHTML = iconElement + messageElement;

  // find place to insert error
  let container = element.parentElement;
  if (container.classList.contains("tooltip"))
    container = container.parentElement;
  if (container.classList.contains("checkbox-input-div"))
    container = container.parentElement;
  if (
    escapeGrid &&
    container.parentElement.classList.contains("grid-input-div")
  )
    container = container.parentElement.parentElement;
  else if (container.parentElement.classList.contains("checkbox-input-div"))
    container = container.parentElement.parentElement;
  // write error
  container.appendChild(error);
}

/**
 * clears every element with the "error-msg" class
 */
function clearErrorMessages() {
  for (let el of Array.from(document.getElementsByClassName("error-msg"))) {
    el.remove();
  }
}
