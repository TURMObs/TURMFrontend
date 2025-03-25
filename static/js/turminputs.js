/**
 * Returns the string without all parts that are not matched by regex.
 * Regex mustn't generate overlapping sections of selection
 * @param value string that is to be sanitized
 * @param regex regex that is to be kept
 * @returns string
 */
function sanitize(value, regex) {
  const matched = value.match(regex);
  return !!matched ? matched.join("") : "";
}

/* --- RA DEC --- */
/**
 * oninput handler for RA and DEC Field
 */
function raDecInputHandler() {
  const target = event.target;
  const rawInput = event.data;
  let val = target.value;
  if (val === "") return;
  if (!rawInput) {
    val =
      val.endsWith(".") || val.endsWith(" ")
        ? val.slice(0, val.length - 1)
        : val;
  }
  let sign;
  let newValue;
  [newValue, sign] = enforceRaDecRules(
    val,
    !rawInput ? "" : rawInput.match(/[+\-]/),
  );
  const cursorPos = target.selectionStart;
  const offset = !rawInput
    ? 0
    : getRaDecOffset(target.value.length, newValue.length, sign);
  target.value = newValue;
  target.setSelectionRange(cursorPos + offset, cursorPos + offset);
}

function getRaDecOffset(before, after, sign) {
  const firstSpaceIndex = sign ? 4 : 3;
  const secondSpaceIndex = sign ? 7 : 6;
  const decimalPointIndex = sign ? 10 : 9;
  let out = 0;
  if (before > decimalPointIndex) return 0;
  if (before <= firstSpaceIndex && after > firstSpaceIndex) out++;
  if (before <= secondSpaceIndex && after > secondSpaceIndex) out++;
  if (after > decimalPointIndex) out++;
  return out;
}

/**
 * Returns correctly formatted RA/DEC string
 * @param val value of the input
 * @param overwriteSign for when a + or - is typed later on
 * @returns
 */
function enforceRaDecRules(val, overwriteSign) {
  let sign = "";
  if (!overwriteSign) {
    if (val.length < 1) return val;
    if (val[0] === "+" || val[0] === "-") {
      sign = val[0];
      val = val.slice(1, val.length);
    }
  } else sign = overwriteSign;
  const lastChar = val.slice(val.length - 1, val.length);
  val = sanitize(val, /\d/g);
  val = raDecSpacing(val, lastChar);
  return [sign + val.slice(0, 14), sign !== ""];
}
/**
 * Returns input with correct spacing and decimal point for RA/DEC fields
 * @param val value of the input (without sign)
 * @param lastChar
 */
function raDecSpacing(val, lastChar) {
  const firstSpaceIndex = 2;
  const secondSpaceIndex = 5;
  const decimalPointIndex = 8;
  if (val.length === firstSpaceIndex && lastChar === " ") return val + " ";
  if (val.length <= firstSpaceIndex) return val;
  if (val[firstSpaceIndex] !== " ")
    val = val.slice(0, firstSpaceIndex) + " " + val.slice(firstSpaceIndex); // first space
  if (val.length === secondSpaceIndex && lastChar === " ") return val + " ";
  if (val.length <= secondSpaceIndex) return val;
  if (val[secondSpaceIndex] !== " ")
    val = val.slice(0, secondSpaceIndex) + " " + val.slice(secondSpaceIndex); // second space
  if (val.length === decimalPointIndex && lastChar === ".") return val + ".";
  if (val.length <= decimalPointIndex) return val;
  if (!(val[decimalPointIndex] === "."))
    val = val.slice(0, decimalPointIndex) + "." + val.slice(decimalPointIndex); // decimal point
  return val;
}

/* --- date time --- */
/**
 * oninput handler for DateTime fields
 */
function dateTimeInputHandler() {
  abstractDateTimeInputHandler("YYYY-MM-DD hh:mm");
}
/**
 * oninput handler for Date fields
 */
function dateInputHandler() {
  abstractDateTimeInputHandler("YYYY-MM-DD");
}
/**
 * oninput handler for Time fields
 */
function timeInputHandler() {
  abstractDateTimeInputHandler("hh:dd");
}

/**
 * Abstract handler for date time related inputs
 * @param format string of the given format. e.g. "yyyy-mm-dd"
 */
function abstractDateTimeInputHandler(format) {
  const target = event.target;
  const cursorPosBefore = target.selectionStart;
  const formattingIndices = getFormattingIndices(format);
  const isDeletion = event.data === null;

  event.target.addEventListener(
    "input",
    (_) => {
      // format existing input
      let lastChar = "";
      if (!isDeletion && target.value !== undefined)
        lastChar = target.value.charAt(cursorPosBefore);
      let val = enforceDateTimeRules(target.value, lastChar, format);

      // compute new cursor position
      const cursorPosAfter = target.selectionStart;
      let cursorPos = getNewCursorPos(
        formattingIndices,
        cursorPosBefore,
        cursorPosAfter,
      );
      cursorPos = Math.min(cursorPos, val.length);
      if (isDeletion && cursorPos > 0 && !val[cursorPos - 1].match(/\d/))
        cursorPos--;

      // add formatting string to end
      val =
        val.slice(0, format.length) + format.slice(val.length, format.length);

      //set values
      target.value = val;
      target.setSelectionRange(cursorPos, cursorPos);
    },
    { once: true },
  );
}

/** Returns indices of non-alphabetical characters
 * @param format string representing format
 */
function getFormattingIndices(format) {
  let matchedIndices = [];
  let re = /[^A-z]/g;
  let match;
  while ((match = re.exec(format)) != null) matchedIndices.push(match.index);
  return matchedIndices;
}

/**
 * Returns new cursor position
 * @param format formatting string that is used
 * @param oldPos cursor position before input
 * @param newPos cursor position after input
 * @returns {*}
 */
function getNewCursorPos(format, oldPos, newPos) {
  let createdOffset = 0;
  for (let separatorIndex of format) {
    if (oldPos <= separatorIndex && newPos > separatorIndex) createdOffset++;
  }
  return newPos + createdOffset;
}

/**
 * Returns correctly formatted string according to format
 * @param val value of the input
 * @param lastChar last character in input
 * @param format format given as nested Array. See abstractDateTimeInputHandler for example
 * @returns string
 */
function enforceDateTimeRules(val, lastChar, format) {
  const indices = getFormattingIndices(format);
  val = sanitize(val, /\d/g);
  for (let separatorIndex of indices) {
    if (val.length < separatorIndex) return val;
    if (val.length === separatorIndex && lastChar === format[separatorIndex]) {
      return val + format[separatorIndex];
    }
    val =
      val.slice(0, separatorIndex) +
      format[separatorIndex] +
      val.slice(separatorIndex);
  }
  return val;
}

/* --- Numbers --- */
/**
 * oninput handler for Integer fields
 */
function integerInputHandler() {
  const target = event.target;
  target.value = sanitize(target.value, /\d/g);
}

/**
 * oninput handler for Decimal fields
 */
function decimalInputHandler() {
  const target = event.target;
  let val = target.value;
  const decimalIndexPoint = val.indexOf(".");
  const decimalIndexComma = val.indexOf(",");

  if (decimalIndexPoint === -1 && decimalIndexComma === -1) {
    target.value = sanitize(val, /\d/g);
    return;
  }

  let minDecimalIndex;
  if (decimalIndexPoint === -1) {
    minDecimalIndex = decimalIndexComma;
  } else if (decimalIndexComma === -1) minDecimalIndex = decimalIndexPoint;
  else minDecimalIndex = Math.min(decimalIndexPoint, decimalIndexComma);
  const decimalCharacter = val[minDecimalIndex];
  val = sanitize(val, /\d/g);
  target.value =
    val.slice(0, minDecimalIndex) +
    decimalCharacter +
    val.slice(minDecimalIndex, val.length);
}

/* --- Text --- */
/**
 * oninput handler for Target Name field
 */
function targetNameInputHandler() {
  const target = event.target;
  target.value = sanitize(target.value, /[\w!-\/:-@[-`{-~]/g).slice(0, 64);
}

/**
 * oninput handler for Catalogue field
 */
function catalogIdInputHandler() {
  const target = event.target;
  target.value = sanitize(target.value, /[\w!-\/:-@[-`{-~]/g).slice(0, 32);
}

/* --- on page load --- */

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

/* --- dynamic display of form elements --- */

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

/* --- Form Submission and Error handling --- */

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
            handleErrors(jsonResponse);
          })
          .catch((error) => console.log(error, response));
    })
    .catch((error) => console.error("Error:", error));
}

/**
 * Returns dict of empty inputs that have a placeholder
 */
function gatherDefaultValues() {
  const emptyInputs = Array.from(document.getElementsByTagName("INPUT"))
    .filter((el) => !el.disabled)
    .filter((el) => el.value === "");

  const out = new Map();

  for (let input of emptyInputs) {
    const placeholder = input.getAttribute("placeholder");
    if (placeholder && input.id !== "id_catalog_id") {
      out.set(input.getAttribute("name"), placeholder);
    }
  }
  return out;
}

function handleErrors(dict) {
  clearErrorMessages();
  let element;
  for (let key in dict) {
    if (key !== "target") {
      let name = key;
      let escapeGrid = false;
      let message = dict[key][0];
      if (
        key === "time_range" ||
        key === "start_time" ||
        key === "year_range" ||
        key === "overlapping_observations"
      ) {
        name = "start_observation";
        escapeGrid = true;
        if (key === "overlapping_observations")
          message =
            "overlapping with observation: " +
            dict[key][0].start_observation +
            " - " +
            dict[key][0].end_observation;
      }
      const field = addErrorMessage(name, message, escapeGrid);
      if (!element) element = field;
      else if (
        field.getBoundingClientRect().top < element.getBoundingClientRect().top
      ) {
        element = field;
      }
    } else {
      for (let subKey in dict.target) {
        const message = dict[key][subKey][0];
        const field = addErrorMessage(subKey, message);
        if (!element) element = field;
        else if (
          field.getBoundingClientRect().top <
          element.getBoundingClientRect().top
        ) {
          element = field;
        }
      }
    }
  }
  if (!!element) element.scrollIntoView();
}
/**
 * Adds an error note under the element with the message text.
 * @param name of the field that the error is for
 * @param message text that should be displayed
 * @param escapeGrid when the element is in a grid-input-div this param specifies if it should be displayed in the same cell or under the whole grid (useful for duration inputs)
 */
function addErrorMessage(name, message, escapeGrid = false) {
  const messageElement = "<span>" + message + "</span>";
  const iconElement = '<i class="bx bx-error-circle"></i>';
  const error = document.createElement("div");
  error.classList.add("error-msg");
  error.innerHTML = iconElement + messageElement;

  // default case
  let element = document.getElementById("id_" + name);
  // expert_case
  if (element === null || element.disabled)
    element = document.getElementById("id_exp_" + name);
  // select or radio
  if (element === null) element = document.getElementById("id_" + name + "_0");
  // other unknown
  if (element === null) element = document.getElementById("form");
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
  return findLabelForControl(element);
}

/**
 * clears every element with the "error-msg" class
 */
function clearErrorMessages() {
  for (let el of Array.from(document.getElementsByClassName("error-msg"))) {
    el.remove();
  }
}

function findLabelForControl(element) {
  const labels = Array.from(document.getElementsByTagName("label")).filter(
    (el) => el.htmlFor === element.id,
  );
  return labels[0];
}
