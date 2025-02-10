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
function disable_inputs(dependency_type, dependency) {
    const dependent_inputs = Array.from(
        document.getElementsByTagName("INPUT"),
    ).filter((el) => !!el.getAttribute(dependency_type));

    for (let input of dependent_inputs) {
        if (
            input.getAttribute(dependency_type).split(" ").includes(dependency)
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
 * @param dependency_type
 * @param dependency
 */
function hide_inputs(dependency_type, dependency) {
    const dependent_inputs = Array.from(
        document.getElementsByTagName("INPUT"),
    ).filter((el) => !!el.getAttribute(dependency_type));

    for (let input of dependent_inputs) {
        const hide_el = !input
            .getAttribute(dependency_type)
            .includes(dependency);
        let parent = input.parentElement;
        const local_inputs = Array.from(parent.children).filter(
            (el) => el.tagName === "INPUT",
        );
        if (parent.classList.contains("checkbox-input-div")) {
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

/**
 * submits form to specified address. In case of failure it marks the errors in html. In case of success user gets redirected.
 * @param event the form submission event
 * @param form the form element that is to be submitted
 * @param post_address web address to submit to
 * @param redirect_address address where a successful submit redirects to
 */
function submitForm(event, form, post_address, redirect_address) {
    event.preventDefault();
    event.stopPropagation();
    fetch(post_address, {
        method: "POST",
        body: new FormData(form),
        credentials: "include",
        headers: {
            Accept: "application/json",
        },
    })
        .then((response) => {
            if (response.ok) location.href = redirect_address;
            else
                response
                    .json()
                    .then((json_response) => {
                        clear_error_messages();
                        for (let key in json_response) {
                            if (key !== "target") {
                                let name = key;
                                let escape_grid = false;
                                if (
                                    key === "time_range" ||
                                    key === "start_time" ||
                                    key === "year_range"
                                ) {
                                    name = "start_observation";
                                    escape_grid = true;
                                }
                                let element = document.getElementById(
                                    "id_" + name,
                                );
                                add_error_message(
                                    element,
                                    json_response[key][0],
                                    escape_grid,
                                );
                            } else {
                                for (let sub_key in json_response.target) {
                                    let element = document.getElementById(
                                        "id_" + sub_key,
                                    );
                                    add_error_message(
                                        element,
                                        json_response[key][sub_key][0],
                                    );
                                }
                            }
                        }
                    })
                    .catch((error) => console.log(error, response));
        })
        .catch((error) => console.error("Error:", error));
}

/**
 * Adds an error note under the element with the message text.
 * @param element that the error is for
 * @param message text that should be displayed
 * @param escape_grid when the element is in a grid-input-div this param specifies if it should be displayed in the same cell or under the whole grid (useful for duration inputs)
 */
function add_error_message(element, message, escape_grid = false) {
    const message_element = "<span>" + message + "</span>";
    const icon_element = '<i class="bx bx-error-circle"></i>';
    const error = document.createElement("div");
    error.classList.add("error-msg");
    error.innerHTML = icon_element + message_element;

    // find place to insert error
    let container = element.parentElement;
    if (container.classList.contains("tooltip"))
        container = container.parentElement;
    if (container.classList.contains("checkbox-input-div"))
        container = container.parentElement;
    if (
        escape_grid &&
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
function clear_error_messages() {
    for (let el of Array.from(document.getElementsByClassName("error-msg"))) {
        el.remove();
    }
}
