/**
 * event hook that prevents the specified characters from being typed into a textfield
 * @param event html event that was triggered
 * @param el the HTML element that triggered the event
 * @param suppressed RegExp of what should be suppressed
 */

function discard_input(event, el, suppressed) {
  el.value = el.value.replace(RegExp(suppressed), "");
  event.stopPropagation();
  event.preventDefault();
}

/**
 * Checks the first radio button of a group of radio buttons, if none are selected
 * Is supposed to be called on page load
 */
function check_radio_if_none_selected() {
  const divs = document.getElementsByClassName("radio_input_div");
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
function disable_inputs(dependency_type, dependency) {
  const dependent_inputs = Array.from(
    document.getElementsByTagName("INPUT"),
  ).filter((el) => !!el.getAttribute(dependency_type));

  for (let input of dependent_inputs) {
    if (input.getAttribute(dependency_type).split(" ").includes(dependency)) {
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
 * @param dependency_type
 * @param dependency
 */
function hide_inputs(dependency_type, dependency) {
  const dependent_inputs = Array.from(
    document.getElementsByTagName("INPUT"),
  ).filter((el) => !!el.getAttribute(dependency_type));

  for (let input of dependent_inputs) {
    const hide_el = !input.getAttribute(dependency_type).includes(dependency);
    let parent = input.parentElement;
    const local_inputs = Array.from(parent.children).filter(
      (el) => el.tagName === "INPUT",
    );
    if (parent.classList.contains("radio_input_div")) {
      parent = input.parentElement.parentElement;
    }
    if (hide_el) {
      parent.style.display = "none";
      for (let l_input of local_inputs) {
        l_input.disabled = true;
      }
    } else {
      parent.removeAttribute("style");
      for (let l_input of local_inputs) {
        l_input.disabled = false;
      }
    }
  }
}

function update_date_dependency(el) {
  const end = document.getElementById(el.id.replace(RegExp("start"), "end"));
  if (end === null) return;
  end.min = el.value;
  if (Date.parse(end.min) > Date.parse(end.value)) {
    end.value = end.min;
  }
}
