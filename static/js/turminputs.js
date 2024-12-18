function discard_input(event, el, suppressed) {
    console.log(el.value, el.value.replace(RegExp(suppressed), ''), RegExp(suppressed));
    el.value = el.value.replace(RegExp(suppressed), '');
    event.stopPropagation();
    event.preventDefault();
}
