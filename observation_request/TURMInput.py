from django.forms import Widget
from django.utils.safestring import mark_safe


def _render_attrs_static(attr):
    rendered_attrs = []
    for key, value in attr.items():
        if isinstance(value, list):
            attr_values = ' '.join([item for item in value])
            rendered_attrs.append(f'{key}="{attr_values}"')

        else:
            rendered_attrs.append(f'{key}="{value}"')
    return ' '.join(rendered_attrs)

class _TURMInput(Widget):
    """
        Abstract base class for all TURMWidgets

        implements renderer for attributes and dependencies

        requires subclasses to implement the @render function
    """
    def __init__(self, name, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.attrs["name"] = name

    def _render_attrs(self, attr):
        return _render_attrs_static(self.attrs | attr)

    def add_dependencies(self, dependencies:dict):
        for d_type, d in dependencies.items():
            self.attrs[d_type] = d
        return self

    def render(self, name, value, attrs=None, renderer=None):
        raise NotImplementedError("Subclasses must implement this method.")

""" --- TURM Numeric Inputs """
class _TURMNumericInput(_TURMInput):
    """
        Abstract base class for all Numeric style TURMWidgets

        implements optional measurement_unit, minimum, maximum and step attributes

        provides subclasses with a generic render function
    """
    measurement_unit = None
    minimum = None
    maximum = None
    step = None

    def __init__(self, name: str, measurement_unit=None, minimum=None, maximum=None, step=None,
                 *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self.measurement_unit = measurement_unit
        self.attrs["type"] = "text"
        self.attrs["inputmode"] = "numeric"
        if minimum: self.attrs["min"] = str(self.minimum)
        if maximum: self.attrs["max"] = str(self.maximum)
        if step: self.attrs["step"] = str(self.step)

    def render(self, name, value, attrs=None, renderer=None):
        html_render = f'<input {self._render_attrs(attrs)}></input>'
        if self.measurement_unit: html_render += f'<span><span class="measurement_unit">{self.measurement_unit}</span></span>'
        return mark_safe(html_render)

class TURMIntegerInput(_TURMNumericInput):
    """
        provides a numeric input that restricts input to only whole numbers.
    """
    def __init__(self, name, measurement_unit=None, minimum: int= None, maximum: int=None, step: int=None, *args,
                 **kwargs):
        if step:
            step = int(step)
        super().__init__(name=name, measurement_unit=measurement_unit, minimum=minimum, maximum=maximum, step=step,
                         *args, **kwargs)
        self.attrs["oninput"] = "discard_input(event, this, '[^\\\\d*\\\\s*]')"

class TURMFloatInput(_TURMNumericInput):
    """
        provides a numeric input that restricts input to decimal numbers.
    """
    def __init__(self, name, measurement_unit=None, minimum: float = None, maximum: float = None, step: float = None,
                 *args, **kwargs):
        super().__init__(name=name, measurement_unit=measurement_unit, minimum=minimum, maximum=maximum, step=step,
                         *args, **kwargs)
        self.attrs["oninput"] = "discard_input(event, this, '[^\\\\d*\\\\s*\\\\.*]')" #todo restrict multiple dots

""" --- TURM Choice Inputs """

class _TURMDateTimeInput(_TURMInput):
    def __init__(self, name, minimum=None, maximum=None, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        if minimum: self.attrs["min"] = minimum
        if maximum: self.attrs["max"] = maximum

    def render(self, name, value, attrs=None, renderer=None):
        return mark_safe(f'<input {self._render_attrs(attrs)}></input>')

class TURMDateTimeInput(_TURMDateTimeInput):
    def __init__(self, name, minimum=None, maximum=None, *args, **kwargs):
        super().__init__(name, minimum, maximum, *args, **kwargs)
        if minimum: self.attrs["type"] = "datetime"

class TURMDateInput(_TURMDateTimeInput):
    def __init__(self, name, minimum=None, maximum=None, *args, **kwargs):
        super().__init__(name, minimum, maximum*args, **kwargs)
        if minimum: self.attrs["type"] = "date"



""" --- TURM Choice Inputs """
class _TURMChoiceInput(_TURMInput):
    """
        Abstract base class for all choice style TURMWidgets

        implements choices and optional dependency_generator attributes

        provides subclasses with a generic render function
    """
    choices = []
    dependency_generator = None
    on_click = None

    def __init__(self, name, choices, *args, **kwargs):
        super().__init__(name=name, *args, **kwargs)
        self.choices = choices

    def render(self, name, value, attrs=None, renderer=None):
        label_attrs = self.attrs | attrs
        name = label_attrs["name"]
        label_attrs.pop("type", None)
        label_attrs.pop("name", None)
        label_attrs.pop("required", None)
        label_attrs.pop("onclick", None)

        html_render = ""
        for i in range(len(self.choices)):
            dependency_attr = _render_attrs_static(self.dependency_generator(self.choices[i])) if self.dependency_generator else ""
            on_click_attr = f'onclick="{self.on_click(self.choices[i])}"' if self.on_click else ""
            html_render += f'<input id="id_{name}_{i}" {self._render_attrs(attrs)}{dependency_attr}{on_click_attr}>'
            html_render += f'<label for="id_{name}_{i}" {_render_attrs_static(label_attrs)}>{self.choices[i]}</label>'
        return mark_safe(html_render)

    def add_dependency_generator(self,  dependency_generator):
        self.dependency_generator = dependency_generator
        return self

    def add_on_click(self, func_call_generator):
        """
            @param: func_call_generator Function from choice to the rendered function call
        """
        self.on_click = func_call_generator
        return self

class TURMRadioInput(_TURMChoiceInput):
    def __init__(self, name, choices, *args, **kwargs):
        super().__init__(name=name, choices=choices, *args, **kwargs)
        self.attrs["type"] = "radio"

    def render(self, name, value, attrs=None, renderer=None):
        html_render = f'<div class="radio_input_div">'
        html_render += super().render(name, value, attrs, renderer)
        html_render += '</div>'
        return mark_safe(html_render)

class TURMCheckboxInput(_TURMChoiceInput):
    def __init__(self, name, choices, *args, **kwargs):
        super().__init__(name=name, choices=choices, *args, **kwargs)
        self.attrs["type"] = "checkbox"

    def render(self, name, value, attrs=None, renderer=None):
        html_render = f'<div class="checkbox_input_div">'
        html_render += super().render(name, value, attrs, renderer)
        html_render += '</div>'
        return mark_safe(html_render)


""" --- TURM Misc Inputs """
class TURMGridInput(_TURMInput):
    widgets = []
    grid_dim = ()

    def __init__(self, widgets: list[tuple[_TURMInput, str]], grid_dim=(1, 1), *args, **kwargs):
        super().__init__(name="", *args, *kwargs)
        self.widgets = widgets
        self.grid_dim = grid_dim

    def render(self, name, value, attrs=None, renderer=None):
        html_render = f'<div class="grid_input_div" style="{self.render_rows_style()}">'
        for widget, w_name in self.widgets:
            html_render += f'<div><label for="id_{widget.attrs["name"]}">{w_name}</label>'
            html_render += widget.render(widget.attrs["name"], value, {"id": f'id_{widget.attrs["name"]}'}, renderer)
            html_render += '</div>'
        html_render += f'</div>'
        return mark_safe(html_render)

    def render_rows_style(self):
        style_render = "grid-template-rows:"
        for x in range(self.grid_dim[1]):
            style_render += ' 1fr'
        style_render += "; grid-template-columns:"
        for y in range(self.grid_dim[0]):
            style_render += ' 1fr'
        style_render += ";"
        return style_render

    def add_dependencies(self, dependencies):
        for widget, _ in self.widgets:
            widget.add_dependencies(dependencies)
        return self

    def add_dependency_generator(self, dependency_generator):
        for widget, _ in self.widgets:
            if isinstance(widget, _TURMChoiceInput):
                widget.add_dependency_generator(dependency_generator)
        return self

    def add_on_click(self, func_call_generator):
        """
            @param: func_call Function from choice to the rendered function call
        """
        for widget in self.widgets:
            if isinstance(widget, _TURMChoiceInput):
                widget.add_on_click(func_call_generator)
        return self