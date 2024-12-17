function discard_input(event, el, suppressed) {
    console.log(el.value, el.value.replace(RegExp(suppressed), ''), RegExp(suppressed));
    el.value = el.value.replace(RegExp(suppressed), '');
    event.stopPropagation();
    event.preventDefault();
}

function check_radio_if_none_selected() {
    const divs = document.getElementsByClassName('radio_input_div');
    for (let div of divs) {
        const radios = Array.from(div.children)
            .filter(el => el.tagName === 'INPUT')
            .filter(el => el.type === 'radio');
        let selected_or_first_radio = radios[0]
        for (let radio of radios) {
            if (radio.checked === true) {
                selected_or_first_radio = radio;
                break;
            }
        }
        selected_or_first_radio.checked = true;
        if (selected_or_first_radio.onclick != null) selected_or_first_radio.click()
    }
}

function disable_inputs(el) {
    console.log("Disabled Inputs", el);
}

function hide_inputs(dependency_type, dependency) {
    const dependent_inputs = Array.from(document.getElementsByTagName('INPUT'))
        .filter(el => !!el.getAttribute(dependency_type));

    for (let input of dependent_inputs) {
        if (input.getAttribute(dependency_type).includes(dependency)) {
            for (let label of input.labels) {
                label.removeAttribute("style")
            }
            input.removeAttribute("style")
        } else {
            for (let label of input.labels) {
                label.style.display = 'none';
            }
            input.style.display = 'none';
        }
    }
}